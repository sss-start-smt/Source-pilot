# -*- coding: utf-8 -*-
"""Day 3 deterministic supplier hard-constraint and reranking tests."""
from app.application.usecases.supplier_search import SupplierSearchUseCase
from app.domain.catalog.ports.retrieval_ports import EmbeddingClient, Reranker
from app.domain.supplier.ports.retrieval_ports import SupplierVectorHit, SupplierVectorIndex
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository


class StubEmbedder(EmbeddingClient):
    async def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class StubSupplierIndex(SupplierVectorIndex):
    async def ensure_ready(self, vector_dim: int) -> None:
        return None

    async def upsert_suppliers(self, suppliers, embeddings) -> None:
        return None

    async def search(self, embedding: list[float], top_n: int) -> list[SupplierVectorHit]:
        # First 11 vacuum-flask records intentionally cover all Day-3 phenotypes.
        return [SupplierVectorHit(f"SUP-VF-{index:03d}", 1.0 - index / 100) for index in range(1, 12)]


class StubReranker(Reranker):
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        # Reverse the qualified order so the test can prove reranking happens
        # after hard gates rather than before them.
        return [float(index) for index in range(len(documents))]


def _spec(**overrides) -> SupplierSearchSpec:
    defaults = dict(
        normalized_query="750ml 304 stainless steel vacuum flask laser logo LFGB",
        category="vacuum flask",
        quantity=5000,
        price_max_major=4.0,
        required_certifications=["LFGB"],
        max_lead_time_days=30,
        required_customization=["laser logo"],
        top_k=5,
        currency="USD",
    )
    defaults.update(overrides)
    return SupplierSearchSpec(**defaults)


def _usecase(*, reranker=None) -> SupplierSearchUseCase:
    return SupplierSearchUseCase(
        InMemorySupplierRepository(),
        embedder=StubEmbedder(),
        vector_index=StubSupplierIndex(),
        reranker=reranker,
    )


async def test_normal_search_only_returns_fully_qualified_suppliers():
    result = await _usecase().execute(_spec())
    assert result["hits"]
    assert all(item["hard_constraints_passed"] is True for item in result["hits"])
    for item in result["hits"]:
        assert item["moq"] <= 5000
        assert item["unit_price"] <= 4.0
        assert "LFGB" in item["certifications"]
        assert item["lead_time_days"] <= 30
        assert "laser logo" in item["customization"]


async def test_moq_filter_has_fixed_reason_code():
    result = await _usecase().execute(_spec())
    rejected = {item["supplier_id"]: item for item in result["filtered_out"]}
    assert "moq_too_high" in rejected["SUP-VF-002"]["reason_codes"]


async def test_certification_filter_has_fixed_reason_code():
    result = await _usecase().execute(_spec())
    rejected = {item["supplier_id"]: item for item in result["filtered_out"]}
    assert "missing_certification" in rejected["SUP-VF-004"]["reason_codes"]


async def test_price_filter_has_fixed_reason_code():
    result = await _usecase().execute(_spec())
    rejected = {item["supplier_id"]: item for item in result["filtered_out"]}
    assert "price_above_target" in rejected["SUP-VF-003"]["reason_codes"]


async def test_multiple_constraint_failures_are_preserved():
    result = await _usecase().execute(_spec())
    rejected = {item["supplier_id"]: item for item in result["filtered_out"]}
    codes = set(rejected["SUP-VF-007"]["reason_codes"])
    assert {
        "moq_too_high",
        "price_above_target",
        "missing_certification",
        "lead_time_too_long",
        "customization_unsupported",
    } <= codes


async def test_missing_constraint_data_is_not_silently_treated_as_pass():
    result = await _usecase().execute(_spec())
    rejected = {item["supplier_id"]: item for item in result["filtered_out"]}
    assert "price_above_target" in rejected["SUP-VF-008"]["reason_codes"]
    assert rejected["SUP-VF-008"]["details"][0]["status"] == "unknown"
    assert "lead_time_too_long" in rejected["SUP-VF-009"]["reason_codes"]
    assert "missing_certification" in rejected["SUP-VF-010"]["reason_codes"]
    assert "customization_unsupported" in rejected["SUP-VF-010"]["reason_codes"]


async def test_rerank_is_applied_only_to_qualified_suppliers():
    result = await _usecase(reranker=StubReranker()).execute(_spec())
    assert result["rerank_applied"] is True
    assert result["recall_strategy"] == "embedding_rerank"
    hit_ids = [item["supplier_id"] for item in result["hits"]]
    # Invalid supplier ids 002..010 must never be reintroduced by reranking.
    assert set(hit_ids).isdisjoint({f"SUP-VF-{i:03d}" for i in range(2, 11)})


async def test_keyword_fallback_still_applies_hard_constraints():
    usecase = SupplierSearchUseCase(InMemorySupplierRepository())
    result = await usecase.execute(_spec(top_k=3))
    assert result["recall_strategy"] == "keyword_2gram"
    assert len(result["hits"]) == 3
    assert all(item["unit_price"] <= 4.0 for item in result["hits"])
