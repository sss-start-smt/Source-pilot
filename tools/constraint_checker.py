# -*- coding: utf-8 -*-
"""SourcePilot constraint_checker facade.

The hard-constraint filter is intentionally a deterministic Python function,
not an LLM judgment. LLM is allowed to explain results later; it is never
allowed to decide whether a supplier passes a hard procurement constraint.

This module re-exports the fixed reason codes and a single
``check_supplier`` entry point that returns the list of failing reason codes
(or an empty list when the supplier is qualified for this RFQ).
"""
from __future__ import annotations

from typing import Optional

from app.domain.procurement.rfq import RFQ
from app.domain.quotation.quotation import Quotation
from app.domain.supplier.supplier import Supplier
from app.application.usecases.supplier_search import (
    REASON_CODES,
    REASON_CUSTOMIZATION_UNSUPPORTED,
    REASON_LEAD_TIME_TOO_LONG,
    REASON_MISSING_CERTIFICATION,
    REASON_MOQ_TOO_HIGH,
    REASON_PRICE_ABOVE_TARGET,
)
from app.application.usecases.quotation_compare import (
    HARD_CURRENCY_MISMATCH,
    HARD_CUSTOMIZATION_UNSUPPORTED,
    HARD_LEAD_TIME_TOO_LONG,
    HARD_MISSING_CERTIFICATION,
    HARD_MOQ_TOO_HIGH,
    HARD_PRICE_ABOVE_TARGET,
    HARD_QUOTE_INCOMPLETE,
    QuotationCompareUseCase,
    SupplierQuoteInput,
)


def check_supplier(
    rfq: RFQ,
    supplier: Supplier,
    quotation: Optional[Quotation] = None,
) -> list[str]:
    """Return the list of hard-constraint reason codes that fail.

    Implementation: run the (supplier, quotation) pair through the
    deterministic QuotationCompareUseCase and collect reason_codes from
    the ``disqualified`` segment of the returned payload. Empty list
    means the supplier (or supplier + quote pair) qualifies.
    """
    if quotation is None:
        # Pure supplier-level gate: synthesize a minimal quotation that
        # carries only the supplier id and let the compare use case decide.
        quotation = Quotation(
            quote_id=f"__probe__{supplier.supplier_id}",
            supplier_id=supplier.supplier_id,
            quantity=rfq.quantity,
            unit_price=supplier.unit_price,
            currency=rfq.currency,
            lead_time_days=supplier.lead_time_days,
            incoterm=rfq.preferred_incoterm,
            certifications_confirmed=list(supplier.certifications or []),
            is_estimated=True,
        )
    result = QuotationCompareUseCase().execute(
        rfq,
        [SupplierQuoteInput(supplier=supplier, quotation=quotation)],
        top_k=1,
    )
    for entry in result.get("disqualified", []):
        if entry.get("supplier_id") == supplier.supplier_id:
            return list(entry.get("reason_codes", []))
    return []


def all_reason_codes(include_quotation: bool = True) -> set[str]:
    codes: set[str] = set(REASON_CODES)
    if include_quotation:
        codes.update({HARD_CURRENCY_MISMATCH, HARD_QUOTE_INCOMPLETE})
    return codes


__all__ = [
    "check_supplier",
    "all_reason_codes",
    "REASON_CODES",
    "REASON_MOQ_TOO_HIGH",
    "REASON_PRICE_ABOVE_TARGET",
    "REASON_MISSING_CERTIFICATION",
    "REASON_LEAD_TIME_TOO_LONG",
    "REASON_CUSTOMIZATION_UNSUPPORTED",
    "HARD_CURRENCY_MISMATCH",
    "HARD_QUOTE_INCOMPLETE",
]
