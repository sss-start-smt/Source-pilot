# -*- coding: utf-8 -*-
"""Supplier retrieval ports: embedding, vector index and reranking."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.supplier.supplier import Supplier


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


class Reranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        """Return one relevance score per document."""


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
