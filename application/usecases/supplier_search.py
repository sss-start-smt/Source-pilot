# -*- coding: utf-8 -*-
"""Constraint-aware supplier search for the B2B sourcing workflow.

The decision boundary is intentional:
    retrieval/reranking find relevant suppliers;
    deterministic Python applies MOQ / price / certification / lead-time /
    customization hard gates.

LLMs may explain the result later, but they never decide whether a supplier
passes a hard procurement constraint.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.domain.catalog.ports.retrieval_ports import EmbeddingClient, Reranker
from app.domain.supplier.ports.retrieval_ports import SupplierVectorIndex
from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.domain.supplier.supplier import Supplier
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec

logger = logging.getLogger(__name__)

_RECALL_TOP_N = 40
_FILTERED_OUT_LIMIT = 12

REASON_MOQ_TOO_HIGH = "moq_too_high"
REASON_PRICE_ABOVE_TARGET = "price_above_target"
REASON_MISSING_CERTIFICATION = "missing_certification"
REASON_LEAD_TIME_TOO_LONG = "lead_time_too_long"
REASON_CUSTOMIZATION_UNSUPPORTED = "customization_unsupported"

REASON_CODES = {
    REASON_MOQ_TOO_HIGH,
    REASON_PRICE_ABOVE_TARGET,
    REASON_MISSING_CERTIFICATION,
    REASON_LEAD_TIME_TOO_LONG,
    REASON_CUSTOMIZATION_UNSUPPORTED,
}


@dataclass(frozen=True)
class SupplierCandidate:
    supplier: Supplier
    retrieval_score: float
    final_retrieval_score: float

    def to_dict(self) -> dict[str, Any]:
        supplier = self.supplier
        return {
            "supplier_id": supplier.supplier_id,
            "company_name": supplier.company_name,
            "business_type": supplier.business_type,
            "categories": list(supplier.categories),
            "product_text": supplier.product_text,
            "moq": supplier.moq,
            "unit_price": supplier.unit_price,
            "currency": supplier.currency,
            "incoterms": list(supplier.incoterms),
            "lead_time_days": supplier.lead_time_days,
            "certifications": (
                None if supplier.certifications is None else list(supplier.certifications)
            ),
            "customization": (
                None if supplier.customization is None else list(supplier.customization)
            ),
            "years_in_business": supplier.years_in_business,
            "export_markets": list(supplier.export_markets),
            "reliability_score": supplier.reliability_score,
            "source": supplier.source,
            "retrieval_score": round(self.retrieval_score, 6),
            "score": round(self.final_retrieval_score, 6),
            "hard_constraints_passed": True,
        }


class SupplierSearchUseCase:
    def __init__(
        self,
        supplier_repo: SupplierRepository,
        *,
        embedder: Optional[EmbeddingClient] = None,
        vector_index: Optional[SupplierVectorIndex] = None,
        reranker: Optional[Reranker] = None,
    ) -> None:
        self._repo = supplier_repo
        self._embedder = embedder
        self._vector_index = vector_index
        self._reranker = reranker

    async def execute(self, spec: SupplierSearchSpec) -> dict[str, Any]:
        scored: list[tuple[float, Supplier]] = []
        recall_strategy = "keyword_2gram"
        rerank_applied = False

        if self._embedder is not None and self._vector_index is not None:
            try:
                scored = await self._vector_recall(spec)
                recall_strategy = "embedding_only"
            except Exception as err:  # noqa: BLE001 -- retrieval infra must degrade
                logger.warning("supplier vector recall unavailable, keyword fallback: %s", err)
                scored = []

        if not scored:
            scored = await self._keyword_recall(spec)
            recall_strategy = "keyword_2gram"

        qualified: list[tuple[float, Supplier]] = []
        filtered_out_all: list[dict[str, Any]] = []
        for retrieval_score, supplier in scored:
            reasons = self._reject_reasons(supplier, spec)
            if reasons:
                filtered_out_all.append(
                    self._to_rejected(supplier, retrieval_score, spec, reasons),
                )
            else:
                qualified.append((retrieval_score, supplier))

        # Reranking is intentionally applied only to suppliers that passed all
        # hard gates. A high semantic score can never rescue an invalid MOQ,
        # price, certification, lead time or customization capability.
        ranked = qualified
        if ranked and self._reranker is not None:
            try:
                ranked = await self._rerank(spec, ranked)
                rerank_applied = True
                if recall_strategy == "embedding_only":
                    recall_strategy = "embedding_rerank"
                else:
                    recall_strategy = "keyword_2gram_rerank"
            except Exception as err:  # noqa: BLE001 -- keep deterministic fallback
                logger.warning("supplier rerank unavailable, keep recall order: %s", err)

        hits = [
            SupplierCandidate(
                supplier=supplier,
                retrieval_score=retrieval_score,
                final_retrieval_score=score,
            ).to_dict()
            for score, supplier, retrieval_score in self._with_original_score(ranked, qualified)
        ][: spec.top_k]

        result: dict[str, Any] = {
            "hits": hits,
            "qualified_supplier_count": len(qualified),
            "total_recalled": len(scored),
            "filtered_out_count": len(filtered_out_all),
            "recall_strategy": recall_strategy,
            "rerank_applied": rerank_applied,
        }
        if filtered_out_all:
            result["filtered_out"] = filtered_out_all[:_FILTERED_OUT_LIMIT]
        return result

    async def _vector_recall(self, spec: SupplierSearchSpec) -> list[tuple[float, Supplier]]:
        assert self._embedder is not None
        assert self._vector_index is not None
        embedding = await self._embedder.embed(spec.normalized_query)
        top_n = max(_RECALL_TOP_N, spec.top_k * 5)
        vector_hits = await self._vector_index.search(embedding, top_n=top_n)
        suppliers = await self._repo.find_by_ids([hit.supplier_id for hit in vector_hits])
        by_id = {supplier.supplier_id: supplier for supplier in suppliers}
        return [
            (hit.score, by_id[hit.supplier_id])
            for hit in vector_hits
            if hit.supplier_id in by_id
        ]

    async def _keyword_recall(self, spec: SupplierSearchSpec) -> list[tuple[float, Supplier]]:
        query_terms = _tokenize(spec.normalized_query)
        candidates: list[tuple[float, Supplier]] = []
        for supplier in await self._repo.list_all():
            score = self._keyword_score(query_terms, supplier, spec)
            if score > 0:
                candidates.append((score, supplier))
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        top_n = max(_RECALL_TOP_N, spec.top_k * 5)
        return candidates[:top_n]

    @staticmethod
    def _keyword_score(
        query_terms: set[str], supplier: Supplier, spec: SupplierSearchSpec,
    ) -> float:
        doc_terms = _tokenize(supplier.searchable_text())
        matched = query_terms & doc_terms
        if not matched:
            return 0.0
        score = float(len(matched))
        if spec.category and any(spec.category.lower() in item.lower() for item in supplier.categories):
            score += 4.0
        return score

    async def _rerank(
        self,
        spec: SupplierSearchSpec,
        scored: list[tuple[float, Supplier]],
    ) -> list[tuple[float, Supplier]]:
        assert self._reranker is not None
        documents = [supplier.searchable_text() for _, supplier in scored]
        rerank_scores = await self._reranker.rerank(spec.normalized_query, documents)
        if len(rerank_scores) != len(scored):
            raise RuntimeError("supplier reranker returned unexpected score count")
        reranked = [
            (float(rerank_scores[index]), supplier)
            for index, (_, supplier) in enumerate(scored)
        ]
        reranked.sort(key=lambda pair: pair[0], reverse=True)
        return reranked

    @staticmethod
    def _with_original_score(
        ranked: list[tuple[float, Supplier]],
        qualified: list[tuple[float, Supplier]],
    ) -> list[tuple[float, Supplier, float]]:
        original = {supplier.supplier_id: score for score, supplier in qualified}
        return [
            (final_score, supplier, original.get(supplier.supplier_id, final_score))
            for final_score, supplier in ranked
        ]

    def _reject_reasons(
        self, supplier: Supplier, spec: SupplierSearchSpec,
    ) -> list[dict[str, Any]]:
        reasons: list[dict[str, Any]] = []

        if spec.quantity is not None:
            if supplier.moq is None or supplier.moq > spec.quantity:
                reasons.append(
                    {
                        "code": REASON_MOQ_TOO_HIGH,
                        "required": {"quantity": spec.quantity},
                        "actual": {"moq": supplier.moq},
                        "status": "unknown" if supplier.moq is None else "failed",
                    },
                )

        if spec.price_max_major is not None:
            price_unknown = supplier.unit_price is None
            currency_mismatch = supplier.currency.upper() != spec.currency.upper()
            over_target = (
                not price_unknown
                and not currency_mismatch
                and supplier.unit_price > spec.price_max_major
            )
            if price_unknown or currency_mismatch or over_target:
                status = "unknown" if price_unknown or currency_mismatch else "failed"
                reasons.append(
                    {
                        "code": REASON_PRICE_ABOVE_TARGET,
                        "required": {
                            "price_max_major": spec.price_max_major,
                            "currency": spec.currency.upper(),
                        },
                        "actual": {
                            "unit_price": supplier.unit_price,
                            "currency": supplier.currency,
                        },
                        "status": status,
                    },
                )

        if spec.required_certifications:
            actual = supplier.certifications
            required = {_norm(value) for value in spec.required_certifications}
            available = {_norm(value) for value in (actual or [])}
            missing = sorted(required - available)
            if actual is None or missing:
                reasons.append(
                    {
                        "code": REASON_MISSING_CERTIFICATION,
                        "required": {"certifications": list(spec.required_certifications)},
                        "actual": {"certifications": actual},
                        "missing": missing or list(spec.required_certifications),
                        "status": "unknown" if actual is None else "failed",
                    },
                )

        if spec.max_lead_time_days is not None:
            if supplier.lead_time_days is None or supplier.lead_time_days > spec.max_lead_time_days:
                reasons.append(
                    {
                        "code": REASON_LEAD_TIME_TOO_LONG,
                        "required": {"max_lead_time_days": spec.max_lead_time_days},
                        "actual": {"lead_time_days": supplier.lead_time_days},
                        "status": "unknown" if supplier.lead_time_days is None else "failed",
                    },
                )

        if spec.required_customization:
            actual = supplier.customization
            required = {_norm(value) for value in spec.required_customization}
            available = {_norm(value) for value in (actual or [])}
            missing = sorted(required - available)
            if actual is None or missing:
                reasons.append(
                    {
                        "code": REASON_CUSTOMIZATION_UNSUPPORTED,
                        "required": {"customization": list(spec.required_customization)},
                        "actual": {"customization": actual},
                        "missing": missing or list(spec.required_customization),
                        "status": "unknown" if actual is None else "failed",
                    },
                )

        return reasons

    @staticmethod
    def _to_rejected(
        supplier: Supplier,
        retrieval_score: float,
        spec: SupplierSearchSpec,
        reasons: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "supplier_id": supplier.supplier_id,
            "company_name": supplier.company_name,
            "categories": list(supplier.categories),
            "moq": supplier.moq,
            "unit_price": supplier.unit_price,
            "currency": supplier.currency,
            "lead_time_days": supplier.lead_time_days,
            "certifications": supplier.certifications,
            "customization": supplier.customization,
            "retrieval_score": round(retrieval_score, 6),
            "reason_codes": [reason["code"] for reason in reasons],
            "details": reasons,
            "requested_constraints": {
                "quantity": spec.quantity,
                "price_max_major": spec.price_max_major,
                "currency": spec.currency,
                "required_certifications": list(spec.required_certifications),
                "max_lead_time_days": spec.max_lead_time_days,
                "required_customization": list(spec.required_customization),
            },
        }


def _norm(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _tokenize(text: str) -> set[str]:
    """Whitespace terms plus CJK 2-grams for deterministic fallback recall."""
    terms: set[str] = set()
    for chunk in text.lower().split():
        clean = chunk.strip(" ,.;:/\\|()[]{}<>\"'")
        if not clean:
            continue
        terms.add(clean)
        if any("\u4e00" <= char <= "\u9fff" for char in clean) and len(clean) >= 2:
            terms.update(clean[index : index + 2] for index in range(len(clean) - 1))
    return terms
