# -*- coding: utf-8 -*-
"""RFQ aggregate for B2B sourcing.

The RFQ is a validated business object. LLM extraction happens outside the
Domain layer; this model only enforces deterministic invariants once the
required fields are present.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RFQ:
    request_id: str
    product: str
    quantity: int
    target_price: Optional[float] = None
    currency: str = "USD"
    material: list[str] = field(default_factory=list)
    specifications: dict[str, Any] = field(default_factory=dict)
    customization: list[str] = field(default_factory=list)
    required_certifications: list[str] = field(default_factory=list)
    max_lead_time_days: Optional[int] = None
    destination: Optional[str] = None
    preferred_incoterm: Optional[str] = None
    missing_required_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.request_id or not self.request_id.strip():
            raise ValueError("RFQ.request_id required")
        if not self.product or not self.product.strip():
            raise ValueError("RFQ.product required")
        if self.quantity <= 0:
            raise ValueError("RFQ.quantity 必须为正整数")
        if self.target_price is not None and self.target_price <= 0:
            raise ValueError("RFQ.target_price 存在时必须为正数")
        if self.max_lead_time_days is not None and self.max_lead_time_days <= 0:
            raise ValueError("RFQ.max_lead_time_days 存在时必须为正整数")
        if not self.currency or not self.currency.strip():
            raise ValueError("RFQ.currency required")
        self.currency = self.currency.upper().strip()
        self.product = self.product.strip()
        self.required_certifications = _dedupe(self.required_certifications)
        self.customization = _dedupe(self.customization)
        self.material = _dedupe(self.material)
        self.missing_required_fields = _dedupe(self.missing_required_fields)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
