# -*- coding: utf-8 -*-
"""Deterministic synthetic supplier dataset for the B2B sourcing MVP.

All records are fictional and carry ``source='mvp_seed'``. The dataset is
purpose-built for retrieval/filter evaluation, not a representation of any
real marketplace. Each demo category contains qualified suppliers plus
intentional MOQ/price/certification/lead-time/customization failures and
partially missing information.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.supplier.supplier import Supplier


@dataclass(frozen=True)
class _CategoryProfile:
    prefix: str
    category: str
    company_stem: str
    product_text: str
    base_moq: int
    base_price: float
    base_lead: int
    required_certification: str
    extra_certification: str
    primary_customization: str
    extra_customization: str


_PROFILES = (
    _CategoryProfile(
        prefix="VF",
        category="vacuum flask",
        company_stem="Northstar Drinkware",
        product_text=(
            "750ml 304 stainless steel vacuum flask insulated bottle double-wall "
            "drinkware OEM ODM 保温杯 不锈钢 750ml"
        ),
        base_moq=1200,
        base_price=3.55,
        base_lead=24,
        required_certification="LFGB",
        extra_certification="FDA",
        primary_customization="laser logo",
        extra_customization="custom box",
    ),
    _CategoryProfile(
        prefix="BP",
        category="nylon backpack",
        company_stem="Harbor Textile",
        product_text=(
            "nylon backpack travel daypack luggage strap water resistant 20L 30L "
            "OEM ODM custom logo 尼龙背包 行李箱拉杆带"
        ),
        base_moq=600,
        base_price=6.40,
        base_lead=27,
        required_certification="REACH",
        extra_certification="BSCI",
        primary_customization="custom logo",
        extra_customization="luggage strap",
    ),
    _CategoryProfile(
        prefix="EL",
        category="electronic accessories",
        company_stem="Vector Lighting",
        product_text=(
            "LED electronic accessories USB-C PD controller strip light module "
            "12V 24V OEM ODM CE RoHS electronics LED 电子配件"
        ),
        base_moq=800,
        base_price=2.75,
        base_lead=22,
        required_certification="CE",
        extra_certification="RoHS",
        primary_customization="custom logo",
        extra_customization="custom firmware",
    ),
)


def _build_supplier(profile: _CategoryProfile, index: int) -> Supplier:
    """Generate one deterministic supplier.

    The final digit intentionally controls the evaluation phenotype:
      0 qualified; 1 MOQ fail; 2 price fail; 3 certification fail;
      4 lead-time fail; 5 customization fail; 6 multi-fail;
      7 missing price; 8 missing lead time; 9 missing capability data.
    """
    phenotype = index % 10
    series = index // 10

    moq: int | None = profile.base_moq + series * 100
    price: float | None = round(profile.base_price + series * 0.06 + (index % 3) * 0.03, 2)
    lead: int | None = profile.base_lead + (series % 3)
    certifications: list[str] | None = [profile.required_certification, profile.extra_certification]
    customization: list[str] | None = [profile.primary_customization, profile.extra_customization]

    if phenotype == 1:
        moq = 8000 + series * 500
    elif phenotype == 2:
        price = round(profile.base_price * 1.55 + series * 0.08, 2)
    elif phenotype == 3:
        certifications = [profile.extra_certification]
    elif phenotype == 4:
        lead = 45 + series
    elif phenotype == 5:
        customization = [profile.extra_customization]
    elif phenotype == 6:
        moq = 9000 + series * 500
        price = round(profile.base_price * 1.65, 2)
        certifications = []
        lead = 50
        customization = []
    elif phenotype == 7:
        price = None
    elif phenotype == 8:
        lead = None
    elif phenotype == 9:
        certifications = None
        customization = None

    # Keep at least several unequivocally strong candidates for each demo case.
    if phenotype == 0:
        moq = max(200, profile.base_moq - series * 50)
        price = round(max(0.5, profile.base_price - series * 0.04), 2)
        lead = max(14, profile.base_lead - series)

    business_type = "manufacturer" if index % 4 else "manufacturer+trading"
    reliability = round(min(0.96, 0.72 + (index % 13) * 0.018), 3)
    years = 3 + (index * 3) % 18
    markets = ["US", "EU"] if index % 3 else ["US", "EU", "JP"]
    incoterms = ["FOB", "CIF"] if index % 2 else ["EXW", "FOB", "CIF"]

    capability_suffix = {
        "VF": " laser engraving powder coating custom packaging 304 steel capacity 500ml 750ml 1L",
        "BP": " embroidery screen print laptop compartment trolley sleeve luggage strap recycled nylon",
        "EL": " USB-C PD 3.0 QC 4.0 LED driver PWM dimming 12V 24V PCB assembly",
    }[profile.prefix]

    return Supplier(
        supplier_id=f"SUP-{profile.prefix}-{index + 1:03d}",
        company_name=f"{profile.company_stem} {index + 1:03d}",
        business_type=business_type,
        categories=[profile.category],
        product_text=f"{profile.product_text}{capability_suffix}",
        moq=moq,
        unit_price=price,
        currency="USD",
        incoterms=incoterms,
        lead_time_days=lead,
        certifications=certifications,
        customization=customization,
        years_in_business=years,
        export_markets=markets,
        reliability_score=reliability,
        source="mvp_seed",
    )


def build_seed_suppliers(per_category: int = 60) -> list[Supplier]:
    """Return 180 suppliers by default (60 across each of three categories)."""
    if per_category < 40:
        raise ValueError("每个演示品类至少需要 40 条 Supplier seed")
    return [
        _build_supplier(profile, index)
        for profile in _PROFILES
        for index in range(per_category)
    ]
