# -*- coding: utf-8 -*-
"""SourcePilot cost_calculator facade.

P0 Effective Unit Cost formula:

    Effective Unit Cost
    = Unit Price
    + Logo Fee / Unit
    + Packaging Fee / Unit
    + Fixed Fee / Quantity

``null`` and ``0`` are deliberately distinct. When freight / duty / tax
data is not real, EXW / FOB / CIF results are flagged as
"Estimated / Partial Cost" and never claimed as full landed cost.
"""
from __future__ import annotations

from typing import Any, Optional

from app.domain.quotation.quotation import Quotation
from app.application.usecases.quotation_compare import QuotationCompareUseCase


def effective_unit_cost(quotation: Quotation) -> Optional[float]:
    """Return the deterministic effective unit cost, refreshing first."""
    quotation.update_effective_unit_cost(assume_missing_fees_zero=False)
    return quotation.effective_unit_cost


def cost_breakdown(quotation: Quotation) -> dict[str, Any]:
    """Return a JSON-friendly breakdown of the cost components used."""
    quotation.update_effective_unit_cost(assume_missing_fees_zero=False)
    return {
        "quote_id": quotation.quote_id,
        "unit_price": quotation.unit_price,
        "currency": quotation.currency,
        "logo_fee": quotation.logo_fee,
        "packaging_fee": quotation.packaging_fee,
        "fixed_fee": quotation.fixed_fee,
        "quantity": quotation.quantity,
        "effective_unit_cost": quotation.effective_unit_cost,
        "cost_scope": "Estimated / Partial Cost; not landed cost",
    }


# A module-level handle so callers can also access the wider comparison
# use case (which knows about ranking + reason codes) without importing
# the internal use-case path.
compare_use_case = QuotationCompareUseCase()


__all__ = [
    "effective_unit_cost",
    "cost_breakdown",
    "compare_use_case",
    "Quotation",
]
