"""Backward-compatible re-export of the read path."""

from ecommerce_agent.retrieval import (
    get_product_by_sku,
    list_documents,
    search_documents,
    search_products,
)

__all__ = [
    "get_product_by_sku",
    "list_documents",
    "search_documents",
    "search_products",
]
