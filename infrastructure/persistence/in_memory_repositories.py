# -*- coding: utf-8 -*-
"""In-memory repositories for Product, Supplier and Order.

开发态内存仓储实现。ProductRepository 由种子数据初始化；
OrderRepository 提供自增单号（GBX-XXXX 前缀，便于日志排查）。
"""
from __future__ import annotations

import itertools
from typing import Optional

from app.domain.catalog.ports.product_repository import ProductRepository
from app.domain.catalog.product import Product
from app.domain.order.order import Order
from app.domain.order.ports.order_repository import OrderRepository
from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.domain.supplier.supplier import Supplier
from app.infrastructure.persistence.seed_products import build_seed_products
from app.infrastructure.persistence.seed_suppliers import build_seed_suppliers


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: Optional[list[Product]] = None) -> None:
        seed = products if products is not None else build_seed_products()
        self._products: dict[str, Product] = {p.product_id: p for p in seed}

    async def find_by_id(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    async def find_by_ids(self, product_ids: list[str]) -> list[Product]:
        return [self._products[pid] for pid in product_ids if pid in self._products]

    async def list_all(self) -> list[Product]:
        return list(self._products.values())


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


class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._counter = itertools.count(1)

    async def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def next_order_id(self) -> str:
        return f"GBX-{next(self._counter):06d}"
