"""Backward-compatible re-export of ingest helpers."""

from ecommerce_agent.ingest import (
    init_db,
    update_embedding,
    upsert_document,
    upsert_products_batch,
)

__all__ = [
    "init_db",
    "update_embedding",
    "upsert_document",
    "upsert_products_batch",
]
