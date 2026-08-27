# -*- coding: utf-8 -*-
"""Offline Day-5 product smoke harness for the three frozen demo cases.

Because the sandbox may not have AgentScope/LLM credentials, this harness starts
from the natural-language case fixture plus its frozen structured RFQ extraction,
then executes the real SupplierSearchUseCase, quotation parser, deterministic hard
gates, and ranking. It never substitutes for the separate Agent E2E; it gives a
reproducible equivalent downstream acceptance path when model infrastructure is absent.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.quotation_parser import parse_quotation_text
from app.application.usecases.quotation_compare import QuotationCompareUseCase, SupplierQuoteInput
from app.application.usecases.supplier_search import SupplierSearchUseCase
from app.domain.procurement.rfq import RFQ
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository

CASES = [
    {
        "case": "vacuum_flask",
        "raw_query": "找 5000 个 750ml 304 不锈钢保温杯，要做激光 Logo，需要 LFGB，FOB 单价最好不超过 4 美元，30 天内出货。",
        "rfq": RFQ(
            request_id="RFQ-DEMO-VF", product="vacuum flask", quantity=5000,
            target_price=4.0, currency="USD", material=["304 stainless steel"],
            specifications={"capacity_ml": 750}, customization=["laser logo"],
            required_certifications=["LFGB"], max_lead_time_days=30,
            destination="US", preferred_incoterm="FOB",
        ),
        "query": "750ml 304 stainless steel vacuum flask laser logo LFGB FOB",
        "category": "vacuum flask",
        "quotes": {
            "SUP-VF-001": "Unit price USD 3.65/pc; FOB; laser logo USD 0.12/pc; custom box USD 0.18/pc; fixed fee USD 80; lead time 25 days; LFGB available",
            "SUP-VF-011": "Price USD 3.72/pc; FOB; logo fee USD 0.08/pc; packaging fee USD 0.12/pc; fixed fee USD 50; lead time 22-26 days; LFGB available",
            "SUP-VF-021": "Unit price USD 3.58/pc; FOB; logo fee USD 0.10/pc; packaging fee USD 0.16/pc; fixed fee USD 60; lead time 20-24 days; LFGB available",
        },
    },
    {
        "case": "nylon_backpack",
        "raw_query": "找 2000 个尼龙旅行背包，要 custom logo 和 luggage strap，REACH，目标价 7 美元以内，35 天内交货。",
        "rfq": RFQ(
            request_id="RFQ-DEMO-BP", product="nylon backpack", quantity=2000,
            target_price=7.0, currency="USD", material=["nylon"],
            specifications={"feature": "luggage strap"}, customization=["custom logo", "luggage strap"],
            required_certifications=["REACH"], max_lead_time_days=35,
            destination="US", preferred_incoterm="FOB",
        ),
        "query": "nylon backpack travel luggage strap custom logo REACH FOB",
        "category": "nylon backpack",
        "quotes": {
            "SUP-BP-001": "Unit price USD 6.55/pc; FOB; logo fee USD 0.10/pc; packaging fee USD 0.08/pc; fixed fee USD 60; lead time 28 days; REACH available",
            "SUP-BP-011": "Unit price USD 6.62/pc; FOB; logo fee USD 0.08/pc; packaging fee USD 0.10/pc; fixed fee USD 45; lead time 25-30 days; REACH available",
            "SUP-BP-021": "Unit price USD 6.48/pc; FOB; logo fee USD 0.12/pc; packaging fee USD 0.09/pc; fixed fee USD 50; lead time 27 days; REACH available",
        },
    },
    {
        "case": "electronics",
        "raw_query": "找 3000 个支持 USB-C PD 3.0 / QC 4.0 的 LED 电子配件，需要 CE、RoHS 和 custom firmware，单价 3.3 美元以内，30 天内。",
        "rfq": RFQ(
            request_id="RFQ-DEMO-EL", product="electronic accessories", quantity=3000,
            target_price=3.3, currency="USD", material=[],
            specifications={"protocols": "USB-C PD 3.0 QC 4.0", "voltage": "12V 24V"},
            customization=["custom firmware"], required_certifications=["CE", "RoHS"],
            max_lead_time_days=30, destination="US", preferred_incoterm="FOB",
        ),
        "query": "LED electronic accessories USB-C PD 3.0 QC 4.0 12V 24V CE RoHS custom firmware",
        "category": "electronic accessories",
        "quotes": {
            "SUP-EL-001": "Unit price USD 2.82/pc; FOB; packaging fee USD 0.05/pc; fixed fee USD 40; lead time 23 days; CE RoHS available",
            "SUP-EL-011": "Unit price USD 2.90/pc; FOB; packaging fee USD 0.04/pc; fixed fee USD 35; lead time 20-24 days; CE RoHS available",
            "SUP-EL-021": "Unit price USD 2.78/pc; FOB; packaging fee USD 0.06/pc; fixed fee USD 50; lead time 21 days; CE RoHS available",
        },
    },
]


async def run_case(repo, case):
    rfq = case["rfq"]
    search = SupplierSearchUseCase(repo)
    search_result = await search.execute(
        SupplierSearchSpec(
            normalized_query=case["query"], category=case["category"], quantity=rfq.quantity,
            price_max_major=rfq.target_price, required_certifications=rfq.required_certifications,
            max_lead_time_days=rfq.max_lead_time_days, required_customization=rfq.customization,
            top_k=6, currency=rfq.currency,
        )
    )
    hit_ids = {row["supplier_id"] for row in search_result["hits"]}
    quote_ids = list(case["quotes"])
    if not set(quote_ids).issubset(hit_ids):
        raise AssertionError(f"{case['case']}: quote suppliers must be qualified search hits")

    suppliers = {s.supplier_id: s for s in await repo.find_by_ids(quote_ids)}
    items = []
    for index, supplier_id in enumerate(quote_ids, start=1):
        extraction = parse_quotation_text(
            case["quotes"][supplier_id], quote_id=f"Q-{case['case']}-{index}",
            supplier_id=supplier_id, quantity=rfq.quantity,
        )
        items.append(SupplierQuoteInput(suppliers[supplier_id], extraction.quotation))
    decision = QuotationCompareUseCase().execute(rfq, items, top_k=3)
    if len(decision["shortlist"]) != 3:
        raise AssertionError(f"{case['case']}: expected Top-3")
    if not all(row["hard_constraints_passed"] for row in decision["shortlist"]):
        raise AssertionError(f"{case['case']}: shortlist contains failed supplier")
    return {
        "case": case["case"],
        "raw_query": case["raw_query"],
        "qualified_supplier_count": search_result["qualified_supplier_count"],
        "filtered_out_count": search_result["filtered_out_count"],
        "shortlist": [
            {
                "rank": row["rank"], "supplier_id": row["supplier_id"],
                "score": row["final_score"], "effective_unit_cost": row["effective_unit_cost"],
                "needs_human_approval": row["needs_human_approval"],
            }
            for row in decision["shortlist"]
        ],
    }


async def main():
    repo = InMemorySupplierRepository()
    results = [await run_case(repo, case) for case in CASES]
    print(json.dumps({"status": "passed", "cases": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
