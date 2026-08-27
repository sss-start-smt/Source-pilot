# -*- coding: utf-8 -*-
"""Normalized supplier quotation with deterministic cost calculation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Quotation:
    quote_id: str
    supplier_id: str
    quantity: int
    unit_price: Optional[float]
    currency: Optional[str]
    incoterm: Optional[str] = None
    logo_fee_per_unit: Optional[float] = None
    packaging_fee_per_unit: Optional[float] = None
    fixed_fee: Optional[float] = None
    fixed_fee_description: Optional[str] = None
    lead_time_days: Optional[int] = None
    lead_time_min_days: Optional[int] = None
    lead_time_max_days: Optional[int] = None
    payment_terms: Optional[str] = None
    certifications_confirmed: Optional[list[str]] = field(default_factory=list)
    effective_unit_cost: Optional[float] = None
    is_estimated: bool = True

    def __post_init__(self) -> None:
        if not self.quote_id or not self.quote_id.strip():
            raise ValueError("Quotation.quote_id required")
        if not self.supplier_id or not self.supplier_id.strip():
            raise ValueError("Quotation.supplier_id required")
        if self.quantity <= 0:
            raise ValueError("Quotation.quantity 必须为正整数")
        if self.unit_price is not None and self.unit_price <= 0:
            raise ValueError("Quotation.unit_price 存在时必须为正数")
        if self.currency is not None and not self.currency.strip():
            raise ValueError("Quotation.currency 存在时不能为空字符串")
        for field_name in ("logo_fee_per_unit", "packaging_fee_per_unit", "fixed_fee"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"Quotation.{field_name} 不能为负数")
        for field_name in ("lead_time_days", "lead_time_min_days", "lead_time_max_days"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"Quotation.{field_name} 存在时必须为正整数")
        if (
            self.lead_time_min_days is not None
            and self.lead_time_max_days is not None
            and self.lead_time_min_days > self.lead_time_max_days
        ):
            raise ValueError("Quotation lead time min 不能大于 max")
        if self.effective_unit_cost is not None and self.effective_unit_cost <= 0:
            raise ValueError("Quotation.effective_unit_cost 存在时必须为正数")

        self.quote_id = self.quote_id.strip()
        self.supplier_id = self.supplier_id.strip()
        if self.currency:
            self.currency = self.currency.upper().strip()
        if self.incoterm:
            self.incoterm = self.incoterm.upper().strip()
        if self.fixed_fee_description:
            self.fixed_fee_description = self.fixed_fee_description.strip()
        if self.certifications_confirmed is not None:
            self.certifications_confirmed = _dedupe(self.certifications_confirmed)

        # A range is preserved, while `lead_time_days` is the conservative max
        # used by hard-gate risk checks.
        if self.lead_time_min_days is not None or self.lead_time_max_days is not None:
            if self.lead_time_min_days is None:
                self.lead_time_min_days = self.lead_time_max_days
            if self.lead_time_max_days is None:
                self.lead_time_max_days = self.lead_time_min_days
            self.lead_time_days = self.lead_time_max_days
        elif self.lead_time_days is not None:
            self.lead_time_min_days = self.lead_time_days
            self.lead_time_max_days = self.lead_time_days

    def missing_cost_fields(self) -> list[str]:
        """Return unresolved fields needed by the P0 effective-cost formula.

        `None` means unknown/not extracted. A literal 0 means the quote
        explicitly has no charge for that component.
        """
        names = ("unit_price", "logo_fee_per_unit", "packaging_fee_per_unit", "fixed_fee")
        return [name for name in names if getattr(self, name) is None]

    def calculate_effective_unit_cost(self, *, assume_missing_fees_zero: bool = False) -> Optional[float]:
        """Compute P0 effective unit cost deterministically.

        Formula:
            unit_price + logo_fee_per_unit + packaging_fee_per_unit + fixed_fee / quantity

        Missing `unit_price` is never imputable. Missing fee fields may be
        treated as zero only when the caller explicitly opts into that policy.
        """
        if self.unit_price is None:
            return None
        missing_fees = [
            name
            for name in ("logo_fee_per_unit", "packaging_fee_per_unit", "fixed_fee")
            if getattr(self, name) is None
        ]
        if missing_fees and not assume_missing_fees_zero:
            return None
        logo = self.logo_fee_per_unit or 0.0
        packaging = self.packaging_fee_per_unit or 0.0
        fixed = self.fixed_fee or 0.0
        return self.unit_price + logo + packaging + fixed / self.quantity

    def update_effective_unit_cost(self, *, assume_missing_fees_zero: bool = False) -> Optional[float]:
        value = self.calculate_effective_unit_cost(
            assume_missing_fees_zero=assume_missing_fees_zero,
        )
        self.effective_unit_cost = value
        return value

    def missing_required_fields(self) -> list[str]:
        missing = []
        if self.unit_price is None:
            missing.append("unit_price")
        if self.currency is None:
            missing.append("currency")
        return missing

    def to_dict(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "supplier_id": self.supplier_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "incoterm": self.incoterm,
            "logo_fee_per_unit": self.logo_fee_per_unit,
            "packaging_fee_per_unit": self.packaging_fee_per_unit,
            "fixed_fee": self.fixed_fee,
            "fixed_fee_description": self.fixed_fee_description,
            "lead_time_days": self.lead_time_days,
            "lead_time_min_days": self.lead_time_min_days,
            "lead_time_max_days": self.lead_time_max_days,
            "payment_terms": self.payment_terms,
            "certifications_confirmed": self.certifications_confirmed,
            "effective_unit_cost": self.effective_unit_cost,
            "is_estimated": self.is_estimated,
            "missing_cost_fields": self.missing_cost_fields(),
            "missing_required_fields": self.missing_required_fields(),
        }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
