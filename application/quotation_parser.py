# -*- coding: utf-8 -*-
"""Quotation extraction helpers.

Primary production path: QuoteAgent performs structured extraction and this
module validates/coerces the extracted slots. A conservative regex parser is
also provided for offline demo/evaluation when an LLM gateway is unavailable.
It intentionally recognizes only explicit commercial labels and returns None
for fields it cannot establish.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.domain.quotation.quotation import Quotation

_CURRENCY_SYMBOLS = {"$": "USD", "¥": "CNY", "￥": "CNY", "€": "EUR", "£": "GBP"}
_CURRENCY_CODES = ("USD", "CNY", "RMB", "EUR", "GBP", "JPY")


@dataclass(frozen=True)
class QuotationExtraction:
    quotation: Quotation
    parser_strategy: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = self.quotation.to_dict()
        result["parser_strategy"] = self.parser_strategy
        result["warnings"] = list(self.warnings)
        return result


def coerce_optional_float(value: Any, field_name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} 必须是数字")
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        text = str(value).strip()
        # Currency/unit wrappers are safe to remove. We never alter decimal
        # magnitude, so "3.65" can never silently become "365".
        text = re.sub(r"^(USD|CNY|RMB|EUR|GBP|JPY)\s*", "", text, flags=re.I)
        text = re.sub(r"^[\$¥￥€£]\s*", "", text)
        text = re.sub(r"\s*(/\s*(pc|pcs|piece|pieces|unit|units|个|件)|each)$", "", text, flags=re.I)
        if not re.fullmatch(r"\d+(?:\.\d+)?", text):
            raise ValueError(f"{field_name} 无法解析为十进制数字: {value!r}")
        result = float(text)
    if result < 0:
        raise ValueError(f"{field_name} 不能为负数")
    return result


def coerce_optional_int(value: Any, field_name: str) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} 必须是整数")
    if isinstance(value, int):
        result = value
    elif isinstance(value, float) and value.is_integer():
        result = int(value)
    else:
        text = str(value).strip()
        if not re.fullmatch(r"\d+", text):
            raise ValueError(f"{field_name} 无法解析为整数: {value!r}")
        result = int(text)
    if result <= 0:
        raise ValueError(f"{field_name} 必须为正整数")
    return result


def normalize_structured_quotation(
    *,
    quote_id: str,
    supplier_id: str,
    quantity: int | str,
    unit_price: Any = None,
    currency: Optional[str] = None,
    incoterm: Optional[str] = None,
    logo_fee_per_unit: Any = None,
    packaging_fee_per_unit: Any = None,
    fixed_fee: Any = None,
    fixed_fee_description: Optional[str] = None,
    lead_time_days: Any = None,
    lead_time_min_days: Any = None,
    lead_time_max_days: Any = None,
    payment_terms: Optional[str] = None,
    certifications_confirmed: Optional[list[str]] = None,
    assume_missing_fees_zero: bool = False,
) -> QuotationExtraction:
    """Validate structured slots extracted by an LLM or UI."""
    quantity_i = coerce_optional_int(quantity, "quantity")
    assert quantity_i is not None
    unit_price_f = coerce_optional_float(unit_price, "unit_price")
    logo_f = coerce_optional_float(logo_fee_per_unit, "logo_fee_per_unit")
    packaging_f = coerce_optional_float(packaging_fee_per_unit, "packaging_fee_per_unit")
    fixed_f = coerce_optional_float(fixed_fee, "fixed_fee")
    lead_i = coerce_optional_int(lead_time_days, "lead_time_days")
    lead_min_i = coerce_optional_int(lead_time_min_days, "lead_time_min_days")
    lead_max_i = coerce_optional_int(lead_time_max_days, "lead_time_max_days")

    normalized_currency = _normalize_currency(currency)
    quote = Quotation(
        quote_id=quote_id,
        supplier_id=supplier_id,
        quantity=quantity_i,
        unit_price=unit_price_f,
        currency=normalized_currency,
        incoterm=incoterm,
        logo_fee_per_unit=logo_f,
        packaging_fee_per_unit=packaging_f,
        fixed_fee=fixed_f,
        fixed_fee_description=fixed_fee_description,
        lead_time_days=lead_i,
        lead_time_min_days=lead_min_i,
        lead_time_max_days=lead_max_i,
        payment_terms=payment_terms,
        certifications_confirmed=certifications_confirmed,
        is_estimated=True,
    )
    quote.update_effective_unit_cost(assume_missing_fees_zero=assume_missing_fees_zero)

    warnings: list[str] = []
    if quote.missing_required_fields():
        warnings.append("missing_required_fields")
    if quote.missing_cost_fields():
        warnings.append("partial_cost_only")
    if quote.incoterm in {"EXW", "FOB", "CIF"}:
        warnings.append("not_landed_cost")
    return QuotationExtraction(quotation=quote, parser_strategy="structured_extraction", warnings=warnings)


def parse_quotation_text(
    text: str,
    *,
    quote_id: str,
    supplier_id: str,
    quantity: int,
) -> QuotationExtraction:
    """Conservative offline parser for demo/evaluation.

    This is not intended to replace the LLM structured extractor. It supports
    common English/Chinese labelled quotation text and deliberately leaves
    ambiguous fields unresolved instead of guessing.
    """
    if not text or not text.strip():
        raise ValueError("quotation text required")
    normalized = " ".join(text.replace("\r", "\n").split())

    currency = _extract_currency(normalized)
    unit_price = _find_money_after_labels(
        normalized,
        [r"unit\s*price", r"price", r"单价"],
    )
    logo_fee = _find_money_after_labels(
        normalized,
        [r"laser\s*logo(?:\s*fee)?", r"logo\s*fee", r"激光\s*logo\s*费?", r"logo\s*费"],
    )
    packaging_fee = _find_money_after_labels(
        normalized,
        [r"custom\s*box", r"packaging\s*fee", r"package\s*fee", r"包装(?:费)?", r"彩盒(?:费)?"],
    )
    fixed_fee, fixed_desc = _find_fixed_fee(normalized)
    lead_min, lead_max = _find_lead_time(normalized)
    incoterm = _find_incoterm(normalized)
    payment_terms = _find_payment_terms(normalized)
    certifications = _find_certifications(normalized)

    extraction = normalize_structured_quotation(
        quote_id=quote_id,
        supplier_id=supplier_id,
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
        incoterm=incoterm,
        logo_fee_per_unit=logo_fee,
        packaging_fee_per_unit=packaging_fee,
        fixed_fee=fixed_fee,
        fixed_fee_description=fixed_desc,
        lead_time_min_days=lead_min,
        lead_time_max_days=lead_max,
        payment_terms=payment_terms,
        certifications_confirmed=certifications,
        assume_missing_fees_zero=False,
    )
    warnings = list(extraction.warnings)
    warnings.append("offline_regex_parser_limited")
    return QuotationExtraction(
        quotation=extraction.quotation,
        parser_strategy="regex_fallback",
        warnings=warnings,
    )


def _normalize_currency(currency: Optional[str]) -> Optional[str]:
    if currency is None:
        return None
    value = currency.strip().upper()
    if value == "RMB":
        value = "CNY"
    if value not in _CURRENCY_CODES:
        raise ValueError(f"unsupported currency: {currency}")
    return value


def _extract_currency(text: str) -> Optional[str]:
    upper = text.upper()
    for code in _CURRENCY_CODES:
        if re.search(rf"\b{code}\b", upper):
            return "CNY" if code == "RMB" else code
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code
    if "美元" in text:
        return "USD"
    if "人民币" in text or "元" in text:
        return "CNY"
    return None


def _find_money_after_labels(text: str, labels: list[str]) -> Optional[float]:
    money = r"(?:(?:USD|CNY|RMB|EUR|GBP|JPY)\s*|[\$¥￥€£]\s*)?(\d+(?:\.\d+)?)"
    suffix = r"(?:\s*(?:USD|CNY|RMB|EUR|GBP|JPY|美元|元))?(?:\s*/\s*(?:pc|pcs|piece|pieces|unit|units|个|件))?"
    for label in labels:
        # Keep label and value close to avoid picking unrelated MOQ/quantity.
        match = re.search(rf"(?:{label})\s*[:：]?\s*{money}{suffix}", text, flags=re.I)
        if match:
            return float(match.group(1))
    return None


def _find_fixed_fee(text: str) -> tuple[Optional[float], Optional[str]]:
    labels = [
        (r"sample\s*fee", "sample_fee"),
        (r"setup\s*fee", "setup_fee"),
        (r"mold\s*fee", "mold_fee"),
        (r"版费", "setup_fee"),
        (r"打样费", "sample_fee"),
        (r"模具费", "mold_fee"),
        (r"fixed\s*fee", "fixed_fee"),
    ]
    for label, description in labels:
        value = _find_money_after_labels(text, [label])
        if value is not None:
            return value, description
    return None, None


def _find_lead_time(text: str) -> tuple[Optional[int], Optional[int]]:
    labels = r"(?:lead\s*time|交期|生产周期)"
    ranged = re.search(rf"{labels}\s*[:：]?\s*(\d+)\s*[-–~至到]\s*(\d+)\s*(?:days?|天)", text, flags=re.I)
    if ranged:
        low, high = int(ranged.group(1)), int(ranged.group(2))
        return min(low, high), max(low, high)
    single = re.search(rf"{labels}\s*[:：]?\s*(\d+)\s*(?:days?|天)", text, flags=re.I)
    if single:
        value = int(single.group(1))
        return value, value
    return None, None


def _find_incoterm(text: str) -> Optional[str]:
    match = re.search(r"\b(EXW|FOB|CIF|CFR|DDP|DAP)\b", text, flags=re.I)
    return match.group(1).upper() if match else None


def _find_payment_terms(text: str) -> Optional[str]:
    patterns = [
        r"(?:payment(?:\s*terms?)?|payment)\s*[:：]?\s*([^.;]+)",
        r"付款(?:方式|条件)?\s*[:：]?\s*([^。；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = match.group(1).strip()
            # Avoid swallowing the remainder of a single-line quotation.
            value = re.split(r"\s+(?=(?:LFGB|FDA|CE|ROHS|REACH|lead\s*time|交期)\b)", value, maxsplit=1, flags=re.I)[0]
            return value[:240]
    return None


def _find_certifications(text: str) -> list[str]:
    known = ["LFGB", "FDA", "CE", "ROHS", "REACH", "FCC", "UL", "BSCI", "SEDEX"]
    upper = text.upper()
    return [cert for cert in known if re.search(rf"\b{re.escape(cert)}\b", upper)]
