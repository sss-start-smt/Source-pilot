# -*- coding: utf-8 -*-
"""Offline Day-4 demo: quote text -> normalized quotes -> deterministic Top-3."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.quotation_parser import parse_quotation_text
from app.application.usecases.quotation_compare import QuotationCompareUseCase, SupplierQuoteInput
from app.domain.procurement.rfq import RFQ
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository


async def main() -> None:
    repo = InMemorySupplierRepository()
    supplier_ids = ["SUP-VF-001", "SUP-VF-011", "SUP-VF-021", "SUP-VF-031"]
    suppliers = {supplier.supplier_id: supplier for supplier in await repo.find_by_ids(supplier_ids)}

    raw_quotes = {
        "SUP-VF-001": """
            For 5000 pcs: Unit price USD 3.65/pc; FOB Shenzhen;
            Laser logo USD 0.12/pc; Custom box USD 0.18/pc;
            Sample fee USD 80; Lead time 25 days;
            Payment: 30% deposit, 70% before shipment. LFGB available.
        """,
        "SUP-VF-011": (
            "Price: $3.72 each; logo fee: $0.08/pc; packaging fee: $0.12/pc; "
            "setup fee: $50; lead time: 22-26 days; FOB; LFGB FDA; "
            "Payment: 30% deposit, 70% before shipment."
        ),
        "SUP-VF-021": (
            "单价 USD 3.58/pc，激光Logo费 0.10美元/个，包装费 0.16美元/个，"
            "版费 60美元，交期20-24天，FOB Shenzhen，LFGB可提供"
        ),
        # Intentionally above target to demonstrate hard gate beating rank.
        "SUP-VF-031": (
            "Unit price USD 4.25/pc; laser logo USD 0.05/pc; custom box USD 0.10/pc; "
            "fixed fee USD 30; lead time 18 days; FOB; LFGB available"
        ),
    }

    items = []
    parsed = []
    for idx, (supplier_id, text) in enumerate(raw_quotes.items(), start=1):
        extraction = parse_quotation_text(
            text,
            quote_id=f"Q-DEMO-{idx:03d}",
            supplier_id=supplier_id,
            quantity=5000,
        )
        parsed.append(extraction.to_dict())
        items.append(SupplierQuoteInput(suppliers[supplier_id], extraction.quotation))

    rfq = RFQ(
        request_id="RFQ-DEMO-VF",
        product="vacuum flask",
        quantity=5000,
        target_price=4.0,
        currency="USD",
        material=["304 stainless steel"],
        specifications={"capacity_ml": 750},
        customization=["laser logo"],
        required_certifications=["LFGB"],
        max_lead_time_days=30,
        destination="US",
        preferred_incoterm="FOB",
    )
    result = QuotationCompareUseCase().execute(rfq, items, top_k=3)
    print(json.dumps({"parsed_quotes": parsed, "decision": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
