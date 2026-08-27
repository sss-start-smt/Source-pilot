# -*- coding: utf-8 -*-
"""Supplier vector-index port.

EmbeddingClient and Reranker remain shared catalog-level infrastructure ports;
this file introduces only the supplier-specific vector index contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.supplier.supplier import Supplier


@dataclass(frozen=True)
class SupplierVectorHit:
    supplier_id: str
    score: float


class SupplierVectorIndex(ABC):
    @abstractmethod
    async def ensure_ready(self, vector_dim: int) -> None:
        ...

    @abstractmethod
    async def upsert_suppliers(
        self,
        suppliers: list[Supplier],
        embeddings: list[list[float]],
    ) -> None:
        ...

    @abstractmethod
    async def search(self, embedding: list[float], top_n: int) -> list[SupplierVectorHit]:
        ...
