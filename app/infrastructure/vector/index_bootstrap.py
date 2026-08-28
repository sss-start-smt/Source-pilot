# -*- coding: utf-8 -*-
"""Bootstrap the synthetic supplier vector index without blocking startup."""
from __future__ import annotations

import logging

from app.domain.supplier.ports.retrieval_ports import EmbeddingClient, SupplierVectorIndex
from app.domain.supplier.ports.supplier_repository import SupplierRepository

logger = logging.getLogger(__name__)


async def bootstrap_supplier_index(
    supplier_repo: SupplierRepository,
    embedder: EmbeddingClient,
    vector_index: SupplierVectorIndex,
) -> bool:
    """Bootstrap supplier embeddings without blocking service startup on failure."""
    try:
        suppliers = await supplier_repo.list_all()
        embeddings = await embedder.embed_batch([s.searchable_text() for s in suppliers])
        if not embeddings:
            logger.warning("供应商库为空，跳过向量建库")
            return False
        await vector_index.ensure_ready(vector_dim=len(embeddings[0]))
        await vector_index.upsert_suppliers(suppliers, embeddings)
        logger.info("供应商向量索引就绪：%d 家（dim=%d）", len(suppliers), len(embeddings[0]))
        return True
    except Exception as err:  # noqa: BLE001 -- sourcing can fall back later
        logger.warning("供应商向量建库失败，后续检索需降级关键词召回：%s", err)
        return False
