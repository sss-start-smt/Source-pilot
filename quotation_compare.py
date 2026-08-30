# -*- coding: utf-8 -*-
"""Deterministic quotation comparison and supplier ranking."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.domain.procurement.rfq import RFQ
from app.domain.quotation.quotation import Quotation
from app.domain.supplier.supplier import Supplier
from app.domain.supplier.supplier_score import SupplierScore

# Historical preference is not wired into Day-4 MVP. Per the frozen schema,
# its 5% is redistributed explicitly rather than left as an invisible missing
# component: requirement_match receives 35% instead of 30%.
MVP_WEIGHTS: dict[str, float] = {
    "requirement_match": 0.35,
    "effective_cost": 0.25,
    "lead_time": 0.15,
    "reliability": 0.15,
    "moq_flexibility": 0.10,
}

HARD_MOQ_TOO_HIGH = "moq_too_high"
HARD_PRICE_ABOVE_TARGET = "price_above_target"
HARD_MISSING_CERTIFICATION = "missing_certification"
HARD_LEAD_TIME_TOO_LONG = "lead_time_too_long"
HARD_CUSTOMIZATION_UNSUPPORTED = "customization_unsupported"
HARD_CURRENCY_MISMATCH = "currency_mismatch"
HARD_QUOTE_INCOMPLETE = "quote_incomplete"


@dataclass(frozen=True)
class SupplierQuoteInput:
    supplier: Supplier
    quotation: Quotation


class QuotationCompareUseCase:
    def execute(
        self,
        rfq: RFQ,
        items: Iterable[SupplierQuoteInput],
        *,
        top_k: int = 3,
    ) -> dict[str, Any]:
        if top_k <= 0:
            raise ValueError("top_k 必须为正整数")
        records = list(items)
        if not records:
            return {
                "qualified_supplier_count": 0,
                "shortlist": [],
                "disqualified": [],
                "weights": dict(MVP_WEIGHTS),
                "cost_scope": "Estimated / Partial Cost; not landed cost",
            }

        for item in records:
            if item.supplier.supplier_id != item.quotation.supplier_id:
                raise ValueError(
                    f"quotation supplier mismatch: {item.quotation.quote_id} -> "
                    f"{item.quotation.supplier_id}, expected {item.supplier.supplier_id}",
                )

        # Ensure effective costs are derived from formula, not trusted from LLM.
        for item in records:
            item.quotation.update_effective_unit_cost(assume_missing_fees_zero=False)

        qualified: list[SupplierQuoteInput] = []
        disqualified: list[dict[str, Any]] = []
        for item in records:
            failures = self._hard_failures(rfq, item.supplier, item.quotation)
            if failures:
                disqualified.append(
                    {
                        "supplier_id": item.supplier.supplier_id,
                        "quote_id": item.quotation.quote_id,
                        "hard_constraints_passed": False,
                        "reason_codes": failures,
                        "quotation": item.quotation.to_dict(),
                    },
                )
            else:
                qualified.append(item)

        cohort_costs = [
            self._cost_value(item.quotation)
            for item in qualified
            if self._cost_value(item.quotation) is not None
        ]
        cohort_leads = [
            self._lead_value(item.supplier, item.quotation)
            for item in qualified
            if self._lead_value(item.supplier, item.quotation) is not None
        ]

        scored = [
            self._score(rfq, item.supplier, item.quotation, cohort_costs, cohort_leads)
            for item in qualified
        ]
        scored.sort(key=lambda score: (-score.final_score, score.supplier_id))

        shortlist = []
        by_id = {item.supplier.supplier_id: item for item in qualified}
        for rank, score in enumerate(scored[:top_k], start=1):
            item = by_id[score.supplier_id]
            row = score.to_dict()
            row.update(
                {
                    "rank": rank,
                    "company_name": item.supplier.company_name,
                    "quote_id": item.quotation.quote_id,
                    "unit_price": item.quotation.unit_price,
                    "currency": item.quotation.currency,
                    "effective_unit_cost": (
                        None
                        if item.quotation.effective_unit_cost is None
                        else round(item.quotation.effective_unit_cost, 6)
                    ),
                    "cost_is_partial": item.quotation.effective_unit_cost is None,
                    "incoterm": item.quotation.incoterm,
                    "lead_time_days": self._lead_value(item.supplier, item.quotation),
                    "moq": item.supplier.moq,
                    "source": item.supplier.source,
                },
            )
            shortlist.append(row)

        return {
            "qualified_supplier_count": len(qualified),
            "shortlist": shortlist,
            "disqualified": disqualified,
            "weights": dict(MVP_WEIGHTS),
            "weight_note": "historical_preference 5% redistributed to requirement_match for MVP",
            "cost_scope": "Estimated / Partial Cost; excludes unprovided freight, duty and taxes",
            "needs_human_approval": True,
        }

    def _hard_failures(self, rfq: RFQ, supplier: Supplier, quote: Quotation) -> list[str]:
        failures: list[str] = []
        if supplier.moq is None or supplier.moq > rfq.quantity:
            failures.append(HARD_MOQ_TOO_HIGH)

        # Target price is a quoted unit-price gate. Effective cost is a separate
        # comparison dimension because logo/packaging/fixed fees may be scoped
        # differently from a user's target FOB unit price.
        # Quote comparison requires the commercial quote itself to establish
        # unit price/currency. Supplier-profile values are retrieval facts, not
        # a substitute for missing quote terms.
        if quote.unit_price is None:
            failures.append(HARD_QUOTE_INCOMPLETE)
        elif rfq.target_price is not None and quote.unit_price > rfq.target_price:
            failures.append(HARD_PRICE_ABOVE_TARGET)

        if quote.currency is None:
            failures.append(HARD_QUOTE_INCOMPLETE)
        elif rfq.currency and quote.currency.upper() != rfq.currency.upper():
            failures.append(HARD_CURRENCY_MISMATCH)

        certs = quote.certifications_confirmed
        if certs is None or len(certs) == 0:
            certs = supplier.certifications
        if rfq.required_certifications:
            if certs is None:
                failures.append(HARD_MISSING_CERTIFICATION)
            else:
                known = {value.casefold() for value in certs}
                if any(req.casefold() not in known for req in rfq.required_certifications):
                    failures.append(HARD_MISSING_CERTIFICATION)

        lead = self._lead_value(supplier, quote)
        if rfq.max_lead_time_days is not None:
            if lead is None or lead > rfq.max_lead_time_days:
                failures.append(HARD_LEAD_TIME_TOO_LONG)

        if rfq.customization:
            capabilities = supplier.customization
            if capabilities is None:
                failures.append(HARD_CUSTOMIZATION_UNSUPPORTED)
            else:
                known_caps = {value.casefold() for value in capabilities}
                if any(req.casefold() not in known_caps for req in rfq.customization):
                    failures.append(HARD_CUSTOMIZATION_UNSUPPORTED)

        return _dedupe(failures)

    def _score(
        self,
        rfq: RFQ,
        supplier: Supplier,
        quote: Quotation,
        cohort_costs: list[float],
        cohort_leads: list[int],
    ) -> SupplierScore:
        components = {
            "requirement_match": self._requirement_match(rfq, supplier, quote),
            "effective_cost": self._cost_score(rfq, quote, cohort_costs),
            "lead_time": self._lead_score(rfq, supplier, quote, cohort_leads),
            "reliability": self._reliability_score(supplier),
            "moq_flexibility": self._moq_flexibility(rfq, supplier),
            "historical_preference": None,
        }
        weighted = sum(components[name] * weight for name, weight in MVP_WEIGHTS.items())
        final = round(weighted * 100.0, 2)
        strengths = self._strengths(rfq, supplier, quote, components)
        risks = self._risks(rfq, supplier, quote, components)
        next_action = self._next_action(rfq, quote, risks)
        return SupplierScore(
            supplier_id=supplier.supplier_id,
            hard_constraints_passed=True,
            component_scores=components,
            weights=dict(MVP_WEIGHTS),
            final_score=final,
            strengths=strengths,
            risks=risks,
            next_action=next_action,
            needs_human_approval=True,
        )

    @staticmethod
    def _requirement_match(rfq: RFQ, supplier: Supplier, quote: Quotation) -> float:
        weighted_checks: list[tuple[float, float]] = []
        haystack = supplier.searchable_text().casefold()

        product_tokens = _tokens(rfq.product)
        if product_tokens:
            coverage = sum(1 for token in product_tokens if token in haystack) / len(product_tokens)
            weighted_checks.append((0.35, coverage))

        detail_tokens: set[str] = set()
        for material in rfq.material:
            detail_tokens.update(_tokens(material))
        for key, value in rfq.specifications.items():
            detail_tokens.update(_tokens(str(key)))
            detail_tokens.update(_tokens(str(value)))
        if detail_tokens:
            coverage = sum(1 for token in detail_tokens if token in haystack) / len(detail_tokens)
            weighted_checks.append((0.25, coverage))

        if rfq.preferred_incoterm:
            incoterms = {value.casefold() for value in supplier.incoterms}
            quote_incoterm = (quote.incoterm or "").casefold()
            match = 1.0 if rfq.preferred_incoterm.casefold() in incoterms | {quote_incoterm} else 0.0
            weighted_checks.append((0.15, match))

        if rfq.destination:
            markets = {value.casefold() for value in supplier.export_markets}
            destination = rfq.destination.casefold()
            match = 1.0 if destination in markets or any(destination in market for market in markets) else 0.0
            weighted_checks.append((0.10, match))

        if rfq.required_certifications or rfq.customization:
            certs = {value.casefold() for value in (supplier.certifications or [])}
            caps = {value.casefold() for value in (supplier.customization or [])}
            requirements = [
                *(1.0 if value.casefold() in certs else 0.0 for value in rfq.required_certifications),
                *(1.0 if value.casefold() in caps else 0.0 for value in rfq.customization),
            ]
            if requirements:
                weighted_checks.append((0.15, sum(requirements) / len(requirements)))

        if not weighted_checks:
            return 1.0
        weight_total = sum(weight for weight, _ in weighted_checks)
        return _clamp(sum(weight * value for weight, value in weighted_checks) / weight_total)

    @staticmethod
    def _cost_score(rfq: RFQ, quote: Quotation, cohort_costs: list[float]) -> float:
        value = QuotationCompareUseCase._cost_value(quote)
        if value is None:
            return 0.0
        if rfq.target_price is not None:
            raw = min(1.0, rfq.target_price / value)
        else:
            raw = _inverse_minmax(value, cohort_costs)
        # Partial cost uses quoted unit price only; penalize confidence without
        # pretending missing fees are zero.
        if quote.effective_unit_cost is None:
            raw *= 0.75
        return _clamp(raw)

    @staticmethod
    def _lead_score(
        rfq: RFQ,
        supplier: Supplier,
        quote: Quotation,
        cohort_leads: list[int],
    ) -> float:
        lead = QuotationCompareUseCase._lead_value(supplier, quote)
        if lead is None:
            return 0.0
        if rfq.max_lead_time_days is not None:
            # Faster suppliers score better even after all candidates pass the
            # hard maximum. At the exact limit the score is 0.5.
            return _clamp(1.0 - lead / (2.0 * rfq.max_lead_time_days))
        return _inverse_minmax(float(lead), [float(item) for item in cohort_leads])

    @staticmethod
    def _reliability_score(supplier: Supplier) -> float:
        return _clamp(supplier.reliability_score if supplier.reliability_score is not None else 0.5)

    @staticmethod
    def _moq_flexibility(rfq: RFQ, supplier: Supplier) -> float:
        if supplier.moq is None or supplier.moq > rfq.quantity:
            return 0.0
        return _clamp(1.0 - supplier.moq / rfq.quantity)

    @staticmethod
    def _cost_value(quote: Quotation) -> Optional[float]:
        return quote.effective_unit_cost if quote.effective_unit_cost is not None else quote.unit_price

    @staticmethod
    def _lead_value(supplier: Supplier, quote: Quotation) -> Optional[int]:
        return quote.lead_time_max_days or quote.lead_time_days or supplier.lead_time_days

    @staticmethod
    def _strengths(rfq: RFQ, supplier: Supplier, quote: Quotation, components: dict[str, float | None]) -> list[str]:
        strengths: list[str] = []
        if rfq.required_certifications:
            strengths.append("required certifications satisfied")
        if rfq.customization:
            strengths.append("required customization capability satisfied")
        if components["effective_cost"] is not None and components["effective_cost"] >= 0.85:
            strengths.append("cost position is favorable")
        if components["lead_time"] is not None and components["lead_time"] >= 0.65:
            strengths.append("lead time is comparatively strong")
        if supplier.reliability_score is not None and supplier.reliability_score >= 0.8:
            strengths.append("supplier reliability score is strong")
        return strengths[:4] or ["passes all hard procurement constraints"]

    @staticmethod
    def _risks(rfq: RFQ, supplier: Supplier, quote: Quotation, components: dict[str, float | None]) -> list[str]:
        risks: list[str] = []
        if quote.effective_unit_cost is None:
            risks.append("effective cost is partial because one or more fee fields are unresolved")
        if quote.incoterm in {"EXW", "FOB", "CIF"}:
            risks.append("cost is not a landed-cost estimate; freight/duty/tax may be missing")
        if rfq.target_price is not None and quote.effective_unit_cost is not None:
            if quote.effective_unit_cost > rfq.target_price:
                delta = (quote.effective_unit_cost / rfq.target_price - 1.0) * 100.0
                risks.append(f"effective unit cost is {delta:.1f}% above target unit-price ceiling")
        if supplier.reliability_score is None:
            risks.append("supplier reliability signal is unavailable")
        elif supplier.reliability_score < 0.7:
            risks.append("supplier reliability score is relatively weak")
        return risks[:4]

    @staticmethod
    def _next_action(rfq: RFQ, quote: Quotation, risks: list[str]) -> str:
        if quote.effective_unit_cost is None:
            return "Confirm unresolved fee items before commercial comparison. Needs human approval."
        if rfq.target_price is not None and quote.effective_unit_cost > rfq.target_price:
            return (
                "Ask for 5k/8k/10k tier pricing and confirm whether logo/packaging fees can be included "
                "in unit price. Needs human approval."
            )
        if risks:
            return "Verify the listed commercial risks with the supplier before selection. Needs human approval."
        return "Confirm sample/specification details and commercial terms before selection. Needs human approval."


def _tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", text)
        if len(token) >= 2
    }


def _clamp(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _inverse_minmax(value: float, cohort: list[float]) -> float:
    if not cohort:
        return 0.5
    low, high = min(cohort), max(cohort)
    if abs(high - low) < 1e-12:
        return 1.0
    return _clamp((high - value) / (high - low))


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
