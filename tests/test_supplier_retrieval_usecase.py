# -*- coding: utf-8 -*-
"""Day 2 raw supplier retrieval use-case tests without external services."""
from app.application.usecases.supplier_retrieval import SupplierRetrievalUseCase
from app.domain.catalog.ports.retrieval_ports import EmbeddingClient
from app.domain.supplier.ports.retrieval_ports import SupplierVectorHit, SupplierVectorIndex
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository


class StubEmbedder(EmbeddingClient):
    async def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class BrokenEmbedder(EmbeddingClient):
    async def embed(self, text: str) -> list[float]:
        raise RuntimeError("offline")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("offline")


class StubSupplierIndex(SupplierVectorIndex):
    async def ensure_ready(self, vector_dim: int) -> None:
        return None

    async def upsert_suppliers(self, suppliers, embeddings) -> None:
        return None

    async def search(self, embedding: list[float], top_n: int) -> list[SupplierVectorHit]:
        return [
            SupplierVectorHit("SUP-VF-001", 0.99),
            SupplierVectorHit("SUP-VF-011", 0.95),
        ][:top_n]


async def test_python_usecase_returns_structured_supplier_candidates():
    usecase = SupplierRetrievalUseCase(
        InMemorySupplierRepository(), StubEmbedder(), StubSupplierIndex(),
    )
    result = await usecase.execute("750ml 304 vacuum flask LFGB", top_n=2)
    assert result["recall_strategy"] == "embedding"
    assert [item["supplier_id"] for item in result["candidates"]] == ["SUP-VF-001", "SUP-VF-011"]
    assert result["candidates"][0]["source"] == "mvp_seed"
    assert result["candidates"][0]["retrieval_score"] == 0.99


async def test_python_usecase_degrades_to_keyword_retrieval():
    usecase = SupplierRetrievalUseCase(
        InMemorySupplierRepository(), BrokenEmbedder(), StubSupplierIndex(),
    )
    result = await usecase.execute("nylon backpack luggage strap", top_n=5)
    assert result["recall_strategy"] == "keyword_2gram"
    assert result["candidates"]
    assert all("nylon backpack" in item["categories"] for item in result["candidates"])
