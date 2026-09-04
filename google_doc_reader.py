"""Backward-compatible re-export of Google Docs helpers."""

from ecommerce_agent.integrations.google_docs import (
    get_doc,
    get_doc_text,
    get_doc_text_from_json_string,
    google_doc_id_from_url,
    main,
)

__all__ = [
    "get_doc",
    "get_doc_text",
    "get_doc_text_from_json_string",
    "google_doc_id_from_url",
    "main",
]
