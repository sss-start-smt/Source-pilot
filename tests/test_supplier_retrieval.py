# -*- coding: utf-8 -*-
"""Day 2 supplier Qdrant retrieval test.

The current project execution sandbox may not have qdrant-client installed;
in that case this test is collected as skipped rather than hiding a business
failure. In a normal `uv sync` environment it exercises the real local Qdrant
implementation.
"""
import pytest

pytest.importorskip("qdrant_client")

from app.domain.supplier.ports.retrieval_ports import EmbeddingClient
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository
from app.infrastructure.settings import Settings
from app.infrastructure.vector.index_bootstrap import bootstrap_supplier_index
from app.infrastructure.vector.qdrant_supplier_index import QdrantSupplierIndex

_FEATURE_TERMS = ("vacuum flask", "nylon backpack", "LED", "LFGB", "luggage strap", "USB-C")


class AxisEmbeddingClient(EmbeddingClient):
    async def embed(self, text: str) -> list[float]:
        lower = text.lower()
        return [1.0 if term.lower() in lower else 0.0 for term in _FEATURE_TERMS]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


def _settings(tmp_path) -> Settings:
    return Settings(
        llm_base_url="", llm_api_key="", llm_model="", port=8000, log_level="info",
        embedding_base_url="", embedding_api_key="", embedding_model="", embedding_dim=6,
        qdrant_url="", qdrant_collection="test_products",
        reranker_base_url="", reranker_model="", tavily_api_key="",
        otlp_endpoint="", data_dir=tmp_path,
        category_kb_collection="test_category_kb",
        context_size=128000, tool_result_limit=20000, reply_token_budget=0,
        tool_failure_threshold=3, tool_circuit_reset_seconds=60.0,
        cors_origins=["http://localhost:5173"],
        qdrant_supplier_collection="test_suppliers",
    )


@pytest.fixture()
async def indexed(tmp_path):
    repo = InMemorySupplierRepository()
    embedder = AxisEmbeddingClient()
    index = QdrantSupplierIndex(_settings(tmp_path))
    assert await bootstrap_supplier_index(repo, embedder, index)
    yield repo, embedder, index
    await index.close()


async def test_supplier_vector_search_returns_supplier_candidates(indexed):
    repo, embedder, index = indexed
    query = await embedder.embed("750ml vacuum flask LFGB")
    hits = await index.search(query, top_n=10)
    assert hits
    suppliers = await repo.find_by_ids([hit.supplier_id for hit in hits])
    assert suppliers
    assert suppliers[0].categories == ["vacuum flask"]
    assert any("LFGB" in (s.certifications or []) for s in suppliers)


async def test_supplier_collection_is_independent_from_product_collection(tmp_path):
    settings = _settings(tmp_path)
    assert settings.qdrant_supplier_collection != settings.qdrant_collection
