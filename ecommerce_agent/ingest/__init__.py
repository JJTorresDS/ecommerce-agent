"""Write-path: chunking, product upsert, document upsert, schema init."""

from ecommerce_agent.ingest.chunking import DEFAULT_CHUNK_CHARS, chunk_text
from ecommerce_agent.ingest.documents import upsert_document
from ecommerce_agent.ingest.products import (
    parse_products_csv,
    update_embedding,
    upsert_products_batch,
)
from ecommerce_agent.ingest.schema import init_db

__all__ = [
    "DEFAULT_CHUNK_CHARS",
    "chunk_text",
    "init_db",
    "parse_products_csv",
    "update_embedding",
    "upsert_document",
    "upsert_products_batch",
]
