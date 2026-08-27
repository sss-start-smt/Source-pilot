# -*- coding: utf-8 -*-
"""Raw supplier candidate retrieval for the Day 2 B2B data foundation.

This use case deliberately stops before procurement hard-constraint filtering
and reranking. Day 3's SupplierSearchUseCase composes those decision rules on
top of this retrieval primitive.
"""
from __future__ import annotations

from typing import Any

from app.domain.catalog.ports.retrieval_ports import EmbeddingClient
from app.domain.supplier.ports.retrieval_ports import SupplierVectorIndex
from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.domain.supplier.supplier import Supplier


class SupplierRetrievalUseCase:
    def __init__(
        self,
        supplier_repo: SupplierRepository,
        embedder: EmbeddingClient,
        vector_index: SupplierVectorIndex,
    ) -> None:
        self._repo = supplier_repo
        self._embedder = embedder
        self._vector_index = vector_index

    async def execute(self, query: str, *, top_n: int = 20) -> dict[str, Any]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("supplier retrieval query required")
        if top_n <= 0:
            raise ValueError("top_n 必须为正整数")

        try:
            embedding = await self._embedder.embed(normalized)
            vector_hits = await self._vector_index.search(embedding, top_n=top_n)
            suppliers = await self._repo.find_by_ids([hit.supplier_id for hit in vector_hits])
            by_id = {supplier.supplier_id: supplier for supplier in suppliers}
            candidates = [
                _supplier_card(by_id[hit.supplier_id], retrieval_score=hit.score)
                for hit in vector_hits
                if hit.supplier_id in by_id
            ]
            return {"query": normalized, "recall_strategy": "embedding", "candidates": candidates}
        except Exception:  # noqa: BLE001 -- Day 3 will expose richer diagnostics
            suppliers = await self._repo.list_all()
            ranked = sorted(
                (
                    (_keyword_2gram_score(normalized, supplier.searchable_text()), supplier)
                    for supplier in suppliers
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            candidates = [
                _supplier_card(supplier, retrieval_score=score)
                for score, supplier in ranked[:top_n]
                if score > 0
            ]
            return {"query": normalized, "recall_strategy": "keyword_2gram", "candidates": candidates}


def _supplier_card(supplier: Supplier, *, retrieval_score: float) -> dict[str, Any]:
    return {
        "supplier_id": supplier.supplier_id,
        "company_name": supplier.company_name,
        "business_type": supplier.business_type,
        "categories": list(supplier.categories),
        "moq": supplier.moq,
        "unit_price": supplier.unit_price,
        "currency": supplier.currency,
        "lead_time_days": supplier.lead_time_days,
        "certifications": None if supplier.certifications is None else list(supplier.certifications),
        "customization": None if supplier.customization is None else list(supplier.customization),
        "reliability_score": supplier.reliability_score,
        "source": supplier.source,
        "retrieval_score": retrieval_score,
    }


def _keyword_2gram_score(query: str, document: str) -> float:
    def grams(text: str) -> set[str]:
        normalized = " ".join(text.lower().split())
        if len(normalized) < 2:
            return {normalized} if normalized else set()
        return {normalized[i : i + 2] for i in range(len(normalized) - 1)}

    q = grams(query)
    d = grams(document)
    if not q or not d:
        return 0.0
    return len(q & d) / len(q)
