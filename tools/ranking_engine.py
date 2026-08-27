# -*- coding: utf-8 -*-
"""SourcePilot ranking_engine facade.

Deterministic supplier ranking for the B2B sourcing workflow. The weights
are frozen for the MVP and intentionally redistribute the original
"historical preference" 5% into requirement_match (35%):

    Requirement Match   35%
    Effective Cost      25%
    Lead Time           15%
    Reliability         15%
    MOQ Flexibility     10%
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from app.domain.procurement.rfq import RFQ
from app.domain.quotation.quotation import Quotation
from app.domain.supplier.supplier import Supplier
from app.application.usecases.quotation_compare import (
    MVP_WEIGHTS,
    QuotationCompareUseCase,
    SupplierQuoteInput,
)


_engine = QuotationCompareUseCase()


def rank_suppliers(
    rfq: RFQ,
    items: Iterable[tuple[Supplier, Optional[Quotation]]],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    """Run the deterministic ranking and return the shortlist payload."""
    payload: list[SupplierQuoteInput] = []
    for supplier, quotation in items:
        if quotation is None:
            continue
        payload.append(SupplierQuoteInput(supplier=supplier, quotation=quotation))
    return _engine.execute(rfq, payload, top_k=top_k)


def weights() -> dict[str, float]:
    """Return the frozen MVP weight vector."""
    return dict(MVP_WEIGHTS)


__all__ = [
    "rank_suppliers",
    "weights",
    "MVP_WEIGHTS",
    "QuotationCompareUseCase",
    "SupplierQuoteInput",
]
