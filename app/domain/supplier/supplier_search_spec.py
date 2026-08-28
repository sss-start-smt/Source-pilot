# -*- coding: utf-8 -*-
"""Structured supplier retrieval specification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SupplierSearchSpec:
    normalized_query: str
    category: Optional[str] = None
    quantity: Optional[int] = None
    price_max_major: Optional[float] = None
    required_certifications: list[str] = field(default_factory=list)
    max_lead_time_days: Optional[int] = None
    required_customization: list[str] = field(default_factory=list)
    top_k: int = 5
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not self.normalized_query or not self.normalized_query.strip():
            raise ValueError("SupplierSearchSpec.normalized_query required")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("SupplierSearchSpec.quantity 存在时必须为正整数")
        if self.price_max_major is not None and self.price_max_major <= 0:
            raise ValueError("SupplierSearchSpec.price_max_major 存在时必须为正数")
        if self.max_lead_time_days is not None and self.max_lead_time_days <= 0:
            raise ValueError("SupplierSearchSpec.max_lead_time_days 存在时必须为正整数")
        if self.top_k <= 0:
            raise ValueError("SupplierSearchSpec.top_k 必须为正整数")
        if not self.currency or not self.currency.strip():
            raise ValueError("SupplierSearchSpec.currency required")
