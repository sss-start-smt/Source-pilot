# -*- coding: utf-8 -*-
"""Generate data/sample_suppliers.csv from the in-repo seed dataset.

Usage:
    python scripts/_build_sample_csv.py

Output: data/sample_suppliers.csv (UTF-8, ~30 representative rows)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.seed_suppliers import build_seed_suppliers as build_default_seed  # noqa: E402

OUT = ROOT / "data" / "sample_suppliers.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "supplier_id",
    "company_name",
    "business_type",
    "category",
    "product_text",
    "moq",
    "unit_price",
    "currency",
    "incoterms",
    "lead_time_days",
    "certifications",
    "customization",
    "years_in_business",
    "export_markets",
    "reliability_score",
    "source",
]


def main() -> int:
    suppliers = build_default_seed()
    # Pick 10 suppliers from each of the 3 categories for a balanced sample.
    by_cat: dict[str, list] = {}
    for s in suppliers:
        cat = s.categories[0] if s.categories else "unknown"
        by_cat.setdefault(cat, []).append(s)

    selected = []
    for cat, group in by_cat.items():
        group.sort(key=lambda x: x.supplier_id)
        selected.extend(group[:10])

    with OUT.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDS)
        writer.writeheader()
        for s in selected:
            writer.writerow(
                {
                    "supplier_id": s.supplier_id,
                    "company_name": s.company_name,
                    "business_type": s.business_type,
                    "category": s.categories[0] if s.categories else "",
                    "product_text": s.product_text,
                    "moq": s.moq if s.moq is not None else "",
                    "unit_price": s.unit_price if s.unit_price is not None else "",
                    "currency": s.currency,
                    "incoterms": "|".join(s.incoterms),
                    "lead_time_days": s.lead_time_days if s.lead_time_days is not None else "",
                    "certifications": "|".join(s.certifications) if s.certifications else "",
                    "customization": "|".join(s.customization) if s.customization else "",
                    "years_in_business": s.years_in_business,
                    "export_markets": "|".join(s.export_markets),
                    "reliability_score": s.reliability_score,
                    "source": s.source,
                },
            )
    print(f"wrote {len(selected)} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
