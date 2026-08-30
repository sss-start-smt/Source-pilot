# -*- coding: utf-8 -*-
"""Pure validation helpers for supplier_search_tool inputs.

Kept free of AgentScope imports so the extraction/validation boundary can be
unit-tested even when the Agent runtime is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ValidatedSupplierSearchInput:
    product: str
    quantity: int
    price_max_major: Optional[float]
    max_lead_time_days: Optional[int]
    top_k: int
    currency: str


def validate_supplier_search_input(
    *,
    product: Any,
    quantity: Any,
    price_max_major: Any,
    max_lead_time_days: Any,
    top_k: Any,
    currency: Any,
) -> ValidatedSupplierSearchInput:
    product_text = str(product or "").strip()
    if not product_text:
        raise ValueError("product required; ask the buyer to clarify the product")

    try:
        quantity_i = int(quantity)
    except (TypeError, ValueError) as err:
        raise ValueError(f"quantity 非法：{quantity}") from err
    if quantity_i <= 0:
        raise ValueError("quantity 必须为正整数")

    try:
        price_f = None if price_max_major is None else float(price_max_major)
    except (TypeError, ValueError) as err:
        raise ValueError(f"price_max_major 非法：{price_max_major}") from err
    if price_f is not None and price_f <= 0:
        raise ValueError("price_max_major 存在时必须为正数")

    try:
        lead_i = None if max_lead_time_days is None else int(max_lead_time_days)
    except (TypeError, ValueError) as err:
        raise ValueError(f"max_lead_time_days 非法：{max_lead_time_days}") from err
    if lead_i is not None and lead_i <= 0:
        raise ValueError("max_lead_time_days 存在时必须为正整数")

    try:
        top_k_i = int(top_k)
    except (TypeError, ValueError) as err:
        raise ValueError(f"top_k 非法：{top_k}") from err
    if top_k_i <= 0:
        raise ValueError("top_k 必须为正整数")

    currency_text = str(currency or "").strip().upper()
    if not currency_text:
        raise ValueError("currency required")

    return ValidatedSupplierSearchInput(
        product=product_text,
        quantity=quantity_i,
        price_max_major=price_f,
        max_lead_time_days=lead_i,
        top_k=top_k_i,
        currency=currency_text,
    )
