# -*- coding: utf-8 -*-
"""Canonical long-term procurement preferences stored in PreferenceStore.

The persistence schema intentionally remains unchanged (buyer_id/kind/statement).
For the B2B product surface we encode the preference type in ``statement`` using
``type=value`` so the memory remains inspectable and can be applied deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass

ALLOWED_PROCUREMENT_PREFERENCE_TYPES = (
    "preferred_incoterm",
    "required_certification",
    "supplier_blacklist",
    "preferred_supplier",
    "target_market",
    "material_preference",
)


@dataclass(frozen=True)
class ProcurementPreference:
    preference_type: str
    value: str

    @property
    def statement(self) -> str:
        return f"{self.preference_type}={self.value}"


def parse_procurement_preference(statement: str) -> ProcurementPreference:
    raw = (statement or "").strip()
    if "=" not in raw:
        raise ValueError(
            "B2B 长期偏好必须使用 type=value；允许类型："
            + ", ".join(ALLOWED_PROCUREMENT_PREFERENCE_TYPES)
        )
    preference_type, value = (part.strip() for part in raw.split("=", 1))
    if preference_type not in ALLOWED_PROCUREMENT_PREFERENCE_TYPES:
        raise ValueError(
            f"不支持的采购偏好类型：{preference_type}；允许类型："
            + ", ".join(ALLOWED_PROCUREMENT_PREFERENCE_TYPES)
        )
    if not value:
        raise ValueError(f"采购偏好 {preference_type} 的 value 不能为空")
    return ProcurementPreference(preference_type=preference_type, value=value)


def validate_procurement_preference_statement(statement: str) -> str:
    """Validate and return a normalized canonical statement."""
    return parse_procurement_preference(statement).statement
