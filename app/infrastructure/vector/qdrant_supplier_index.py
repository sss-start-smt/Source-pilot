# -*- coding: utf-8 -*-
"""Qdrant supplier vector index.

Uses a collection independent from the optional Product index. For embedded
Qdrant mode it also uses a separate local storage path, avoiding two local
clients competing for the same file lock during the migration period.
"""
from __future__ import annotations

import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.domain.supplier.ports.retrieval_ports import SupplierVectorHit, SupplierVectorIndex
from app.domain.supplier.supplier import Supplier
from app.infrastructure.settings import Settings


def _point_id(supplier_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"sourcepilot/supplier/{supplier_id}"))


class QdrantSupplierIndex(SupplierVectorIndex):
    def __init__(self, settings: Settings) -> None:
        if settings.qdrant_url:
            self._client = AsyncQdrantClient(url=settings.qdrant_url)
        else:
            local_path = settings.data_dir / "qdrant_suppliers"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._client = AsyncQdrantClient(path=str(local_path))
        self._collection = settings.qdrant_supplier_collection

    async def ensure_ready(self, vector_dim: int) -> None:
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )

    async def upsert_suppliers(
        self,
        suppliers: list[Supplier],
        embeddings: list[list[float]],
    ) -> None:
        if len(suppliers) != len(embeddings):
            raise ValueError("suppliers 与 embeddings 数量不一致")
        if not suppliers:
            return
        points = [
            PointStruct(
                id=_point_id(supplier.supplier_id),
                vector=embedding,
                payload={"supplier_id": supplier.supplier_id},
            )
            for supplier, embedding in zip(suppliers, embeddings)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)

    async def search(self, embedding: list[float], top_n: int) -> list[SupplierVectorHit]:
        result = await self._client.query_points(
            collection_name=self._collection,
            query=embedding,
            limit=top_n,
            with_payload=True,
        )
        return [
            SupplierVectorHit(supplier_id=point.payload["supplier_id"], score=point.score)
            for point in result.points
            if point.payload and "supplier_id" in point.payload
        ]

    async def close(self) -> None:
        await self._client.close()
