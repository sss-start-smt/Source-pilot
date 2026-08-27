# -*- coding: utf-8 -*-
"""Supplier aggregate used for B2B sourcing decisions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Supplier:
    supplier_id: str
    company_name: str
    business_type: str
    categories: list[str]
    product_text: str
    moq: Optional[int]
    unit_price: Optional[float]
    currency: str = "USD"
    incoterms: list[str] = field(default_factory=list)
    lead_time_days: Optional[int] = None
    certifications: Optional[list[str]] = field(default_factory=list)
    customization: Optional[list[str]] = field(default_factory=list)
    years_in_business: Optional[int] = None
    export_markets: list[str] = field(default_factory=list)
    reliability_score: Optional[float] = None
    source: str = ""

    def __post_init__(self) -> None:
        if not self.supplier_id or not self.supplier_id.strip():
            raise ValueError("Supplier.supplier_id required")
        if not self.company_name or not self.company_name.strip():
            raise ValueError("Supplier.company_name required")
        if not self.business_type or not self.business_type.strip():
            raise ValueError("Supplier.business_type required")
        if not self.categories:
            raise ValueError("Supplier.categories 至少需要一个品类")
        if not self.product_text or not self.product_text.strip():
            raise ValueError("Supplier.product_text required")
        if self.moq is not None and self.moq <= 0:
            raise ValueError("Supplier.moq 存在时必须为正整数")
        if self.unit_price is not None and self.unit_price <= 0:
            raise ValueError("Supplier.unit_price 存在时必须为正数")
        if self.lead_time_days is not None and self.lead_time_days <= 0:
            raise ValueError("Supplier.lead_time_days 存在时必须为正整数")
        if self.years_in_business is not None and self.years_in_business < 0:
            raise ValueError("Supplier.years_in_business 不能为负数")
        if self.reliability_score is not None and not 0.0 <= self.reliability_score <= 1.0:
            raise ValueError("Supplier.reliability_score 必须位于 [0, 1]")
        if not self.source or not self.source.strip():
            raise ValueError("Supplier.source required")

        self.supplier_id = self.supplier_id.strip()
        self.company_name = self.company_name.strip()
        self.business_type = self.business_type.strip().lower()
        self.currency = self.currency.upper().strip()
        self.categories = _dedupe(self.categories)
        self.incoterms = _dedupe(self.incoterms)
        self.export_markets = _dedupe(self.export_markets)
        if self.certifications is not None:
            self.certifications = _dedupe(self.certifications)
        if self.customization is not None:
            self.customization = _dedupe(self.customization)

    def searchable_text(self) -> str:
        """Text embedded for supplier retrieval.

        Price/MOQ/lead time are intentionally not relied upon for semantic
        matching; they belong to deterministic filters. The text focuses on
        identity, product capabilities, certifications, customization and
        export-market signals.
        """
        parts = [
            self.company_name,
            " ".join(self.categories),
            self.product_text,
            " ".join(self.certifications or []),
            " ".join(self.customization or []),
            " ".join(self.export_markets),
        ]
        return " ".join(part for part in parts if part).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
