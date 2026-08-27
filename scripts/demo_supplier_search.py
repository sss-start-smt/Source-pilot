# -*- coding: utf-8 -*-
"""Reproducible Day-3 B2B sourcing acceptance case without external services."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.usecases.supplier_search import SupplierSearchUseCase
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository


async def main() -> None:
    search = SupplierSearchUseCase(InMemorySupplierRepository())
    result = await search.execute(
        SupplierSearchSpec(
            normalized_query="750ml 304 stainless steel vacuum flask laser logo LFGB FOB",
            category="vacuum flask",
            quantity=5000,
            price_max_major=4.0,
            required_certifications=["LFGB"],
            max_lead_time_days=30,
            required_customization=["laser logo"],
            top_k=5,
            currency="USD",
        ),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
