# -*- coding: utf-8 -*-
"""SupplierRepository port."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.supplier.supplier import Supplier


class SupplierRepository(ABC):
    @abstractmethod
    async def find_by_id(self, supplier_id: str) -> Optional[Supplier]:
        ...

    @abstractmethod
    async def find_by_ids(self, supplier_ids: list[str]) -> list[Supplier]:
        ...

    @abstractmethod
    async def list_all(self) -> list[Supplier]:
        ...
