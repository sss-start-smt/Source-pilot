# -*- coding: utf-8 -*-
"""SourcePilot quotation_parser facade.

Quotation extraction + coercion. Two paths are exposed:

    - LLM structured extraction + validation (``normalize_structured_quotation``)
    - regex fallback parser (``parse_quotation_text``)

The module-level ``parse_quotation`` function picks the strategy based on
what the caller hands in: a pre-extracted dict uses the structured path;
a raw string falls back to the regex parser. Both paths share the same
``QuotationExtraction`` result type.
"""
from __future__ import annotations

from typing import Any, Optional

# Import from the source module with an explicit alias to avoid name
# collision with this facade module.
from app.application import quotation_parser as _app_quotation_parser
from app.domain.quotation.quotation import Quotation

QuotationExtraction = _app_quotation_parser.QuotationExtraction
coerce_optional_float = _app_quotation_parser.coerce_optional_float
coerce_optional_int = _app_quotation_parser.coerce_optional_int
normalize_structured_quotation = _app_quotation_parser.normalize_structured_quotation
parse_quotation_text = _app_quotation_parser.parse_quotation_text


def parse_quotation(
    payload: Any,
    *,
    quote_id: Optional[str] = None,
    supplier_id: Optional[str] = None,
    quantity: Optional[int] = None,
) -> QuotationExtraction:
    """Dispatch structured payload vs. raw text to the appropriate parser.

    ``payload`` shape:
        - ``str``  -> ``parse_quotation_text`` (regex fallback)
        - ``dict`` -> ``normalize_structured_quotation`` (LLM extracted slots)

    For the regex fallback, ``quote_id`` / ``supplier_id`` / ``quantity`` are
    required by the underlying parser; sensible synthetic defaults are
    supplied if the caller did not pass them so that demo usage stays terse.
    """
    if isinstance(payload, str):
        return parse_quotation_text(
            payload,
            quote_id=quote_id or "QUOTE-UNKNOWN",
            supplier_id=supplier_id or "SUPPLIER-UNKNOWN",
            quantity=quantity or 1,
        )
    if isinstance(payload, dict):
        return normalize_structured_quotation(**payload)
    raise TypeError(
        f"parse_quotation expects str or dict, got {type(payload).__name__}",
    )


__all__ = [
    "parse_quotation",
    "QuotationExtraction",
    "Quotation",
    "coerce_optional_float",
    "coerce_optional_int",
    "normalize_structured_quotation",
    "parse_quotation_text",
]
