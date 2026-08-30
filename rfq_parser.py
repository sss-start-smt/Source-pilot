# -*- coding: utf-8 -*-
"""Conservative RFQ extraction fallback used by offline evaluation/demo.

Production intent remains LLM structured extraction + schema validation. This
module gives Day-6 evaluation a reproducible, dependency-free baseline. It only
extracts explicit values/patterns and reports missing/conflicting constraints;
it never invents quantity, price, certification, or lead-time values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.domain.procurement.rfq import RFQ


KNOWN_PRODUCTS = {
    "vacuum flask": ["vacuum flask", "insulated bottle", "保温杯", "真空杯"],
    "nylon backpack": ["nylon backpack", "backpack", "尼龙背包", "双肩包"],
    "electronic accessories": ["electronic accessories", "led electronic accessories", "led 配件", "电子配件", "led电子配件"],
    "ceramic mug": ["ceramic mug", "陶瓷杯"],
    "bamboo cutlery": ["bamboo cutlery", "竹餐具"],
    "yoga mat": ["yoga mat", "瑜伽垫"],
    "glass jar": ["glass jar", "玻璃罐"],
    "pet harness": ["pet harness", "宠物胸背"],
}
KNOWN_CERTS = ["LFGB", "FDA", "CE", "ROHS", "REACH", "FCC", "UL", "BSCI", "SEDEX"]
KNOWN_INCOTERMS = ["EXW", "FOB", "CIF", "CFR", "DDP", "DAP"]
KNOWN_CUSTOMIZATION = [
    "laser logo", "custom logo", "custom box", "luggage strap", "custom firmware",
    "激光logo", "激光 logo", "定制logo", "定制 logo", "定制彩盒", "拉杆带", "定制固件",
]


@dataclass(frozen=True)
class RFQExtraction:
    product: Optional[str]
    quantity: Optional[int]
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
    conflict_fields: list[str] = field(default_factory=list)
    parser_strategy: str = "regex_fallback"

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "quantity": self.quantity,
            "target_price": self.target_price,
            "currency": self.currency,
            "material": list(self.material),
            "specifications": dict(self.specifications),
            "customization": list(self.customization),
            "required_certifications": list(self.required_certifications),
            "max_lead_time_days": self.max_lead_time_days,
            "destination": self.destination,
            "preferred_incoterm": self.preferred_incoterm,
            "missing_required_fields": list(self.missing_required_fields),
            "conflict_fields": list(self.conflict_fields),
            "parser_strategy": self.parser_strategy,
        }

    def to_rfq(self, request_id: str) -> RFQ:
        if self.product is None or self.quantity is None:
            raise ValueError("cannot build RFQ while product/quantity is missing")
        return RFQ(
            request_id=request_id,
            product=self.product,
            quantity=self.quantity,
            target_price=self.target_price,
            currency=self.currency,
            material=list(self.material),
            specifications=dict(self.specifications),
            customization=list(self.customization),
            required_certifications=list(self.required_certifications),
            max_lead_time_days=self.max_lead_time_days,
            destination=self.destination,
            preferred_incoterm=self.preferred_incoterm,
            missing_required_fields=list(self.missing_required_fields),
        )


def parse_rfq_text(text: str) -> RFQExtraction:
    if not text or not text.strip():
        raise ValueError("rfq text required")
    normalized = " ".join(text.replace("\r", "\n").split())
    lower = normalized.casefold()

    product = _find_product(lower)
    quantity_values = _find_quantity_values(normalized)
    quantity = quantity_values[0] if quantity_values else None
    price_values = _find_price_values(normalized)
    target_price = price_values[0] if price_values else None
    lead_values = _find_lead_values(normalized)
    max_lead = lead_values[0] if lead_values else None

    conflict_fields: list[str] = []
    if len(set(quantity_values)) > 1:
        conflict_fields.append("quantity")
    if len(set(price_values)) > 1:
        conflict_fields.append("target_price")
    if len(set(lead_values)) > 1:
        conflict_fields.append("max_lead_time_days")

    currency = _find_currency(normalized)
    certs = [cert for cert in KNOWN_CERTS if re.search(rf"\b{re.escape(cert)}\b", normalized, re.I)]
    incoterm = next((value for value in KNOWN_INCOTERMS if re.search(rf"\b{value}\b", normalized, re.I)), None)
    destination = _find_destination(normalized)
    material = _find_material(lower)
    customization = _find_customization(lower)
    specs = _find_specifications(normalized, lower)

    missing = []
    if product is None:
        missing.append("product")
    if quantity is None:
        missing.append("quantity")

    return RFQExtraction(
        product=product,
        quantity=quantity,
        target_price=target_price,
        currency=currency,
        material=material,
        specifications=specs,
        customization=customization,
        required_certifications=certs,
        max_lead_time_days=max_lead,
        destination=destination,
        preferred_incoterm=incoterm,
        missing_required_fields=missing,
        conflict_fields=conflict_fields,
    )


def _find_product(lower: str) -> Optional[str]:
    for canonical, aliases in KNOWN_PRODUCTS.items():
        if any(alias.casefold() in lower for alias in aliases):
            return canonical
    return None


def _find_quantity_values(text: str) -> list[int]:
    patterns = [
        r"(?:找|采购|需要|要|订购|quantity\s*[:：]?|qty\s*[:：]?)\s*(\d{2,7})\s*(?:个|件|pcs?|pieces?|units?)",
        r"\b(\d{2,7})\s*(?:pcs?|pieces?|units?|个|件)\b",
    ]
    return _collect_ints(text, patterns)


def _find_price_values(text: str) -> list[float]:
    patterns = [
        r"(?:目标价|target\s*price|price\s*(?:cap|max)?|单价(?:最好)?(?:不超过|低于|<=|≤)?|不超过|<=|≤)\s*[:：]?\s*(?:USD|US\$|\$)?\s*(\d+(?:\.\d+)?)",
        r"(?:USD|US\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:以内|以下|or\s*less|max)?",
        r"(\d+(?:\.\d+)?)\s*(?:美元|美金)\s*(?:以内|以下|不超过|or\s*less|max)?",
    ]
    return _collect_floats(text, patterns)


def _find_lead_values(text: str) -> list[int]:
    patterns = [
        r"(?:lead\s*time|交期|出货|生产周期|within|不超过|<=|≤)\s*[:：]?\s*(\d{1,3})\s*(?:days?|天)",
        r"(\d{1,3})\s*(?:days?|天)\s*(?:内|以内|or\s*less|max)",
    ]
    return _collect_ints(text, patterns)


def _collect_ints(text: str, patterns: list[str]) -> list[int]:
    values: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            value = int(match.group(1))
            if value not in values:
                values.append(value)
    return values


def _collect_floats(text: str, patterns: list[str]) -> list[float]:
    values: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            value = float(match.group(1))
            if value not in values:
                values.append(value)
    return values


def _find_currency(text: str) -> str:
    upper = text.upper()
    if "CNY" in upper or "RMB" in upper or "人民币" in text or "¥" in text or "￥" in text:
        return "CNY"
    if "EUR" in upper or "€" in text:
        return "EUR"
    if "GBP" in upper or "£" in text:
        return "GBP"
    return "USD"


def _find_destination(text: str) -> Optional[str]:
    patterns = [
        (r"(?:destination|ship\s*to|发往|目的地)\s*[:：]?\s*(US|USA|United States|EU|UK|Germany|Japan|美国|欧洲|英国|德国|日本)", None),
    ]
    for pattern, _ in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = match.group(1).casefold()
            mapping = {
                "us": "US", "usa": "US", "united states": "US", "美国": "US",
                "eu": "EU", "欧洲": "EU", "uk": "UK", "英国": "UK",
                "germany": "DE", "德国": "DE", "japan": "JP", "日本": "JP",
            }
            return mapping.get(value, match.group(1))
    return None


def _find_material(lower: str) -> list[str]:
    aliases = [
        ("304 stainless steel", ["304 stainless steel", "304不锈钢", "304 不锈钢"]),
        ("nylon", ["nylon", "尼龙"]),
    ]
    return [canonical for canonical, values in aliases if any(v.casefold() in lower for v in values)]


def _find_customization(lower: str) -> list[str]:
    found: list[str] = []
    aliases = {
        "laser logo": ["laser logo", "激光logo", "激光 logo"],
        "custom logo": ["custom logo", "定制logo", "定制 logo"],
        "custom box": ["custom box", "定制彩盒"],
        "luggage strap": ["luggage strap", "trolley sleeve", "拉杆带"],
        "custom firmware": ["custom firmware", "定制固件"],
    }
    for canonical, values in aliases.items():
        if any(value.casefold() in lower for value in values):
            found.append(canonical)
    return found


def _find_specifications(text: str, lower: str) -> dict[str, Any]:
    specs: dict[str, Any] = {}
    capacity = re.search(r"\b(\d{3,4})\s*ml\b", text, re.I)
    if capacity:
        specs["capacity_ml"] = int(capacity.group(1))
    if "usb-c pd 3.0" in lower or "pd 3.0" in lower:
        specs["protocol_pd"] = "USB-C PD 3.0"
    if "qc 4.0" in lower:
        specs["protocol_qc"] = "QC 4.0"
    voltages = re.findall(r"\b(12V|24V)\b", text, re.I)
    if voltages:
        specs["voltages"] = sorted({value.upper() for value in voltages})
    if "luggage strap" in lower or "trolley sleeve" in lower or "拉杆带" in lower:
        specs["luggage_strap"] = True
    return specs
