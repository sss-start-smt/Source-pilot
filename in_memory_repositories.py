# -*- coding: utf-8 -*-
"""Synthetic in-memory supplier repository used by the public MVP."""
from __future__ import annotations

from typing import Optional

from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.domain.supplier.supplier import Supplier
from app.infrastructure.persistence.seed_suppliers import build_seed_suppliers


class InMemorySupplierRepository(SupplierRepository):
    def __init__(self, suppliers: Optional[list[Supplier]] = None) -> None:
        seed = suppliers if suppliers is not None else build_seed_suppliers()
        self._suppliers: dict[str, Supplier] = {s.supplier_id: s for s in seed}

    async def find_by_id(self, supplier_id: str) -> Optional[Supplier]:
        return self._suppliers.get(supplier_id)

    async def find_by_ids(self, supplier_ids: list[str]) -> list[Supplier]:
        return [self._suppliers[sid] for sid in supplier_ids if sid in self._suppliers]

    async def list_all(self) -> list[Supplier]:
        return list(self._suppliers.values())
