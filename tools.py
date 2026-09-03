from agents import function_tool
from vector_store import get_product_by_sku as _get_product_by_sku
from vector_store import list_documents as _list_documents
from vector_store import search_documents as _search_documents
from vector_store import search_products as _search_products
# --- Define your tools ------------------------------------------------------
# Decorate plain Python functions with @function_tool. Use type hints and a
# clear docstring — the model relies on both to decide when/how to call it.

@function_tool
def get_item_details(sku: str) -> dict:
    """Look up a product in the catalog by its SKU.

    Args:
        sku: Product SKU, e.g. G-001 or B-004.
    """
    print(f"[tool] get_item_details sku={sku!r}", flush=True)
    product = _get_product_by_sku(sku)
    if product is None:
        print(f"[tool] get_item_details -> not_found", flush=True)
        return {"status": "not_found", "sku": sku}
    print(f"[tool] get_item_details -> success", flush=True)
    return {"status": "success", **product}


@function_tool
def list_knowledgebase_documents() -> dict:
    """List knowledge-base documents and their summaries.

    Read the summaries first and pick the document that matches the
    user's question. Then search that document with
    search_faq_knowledgebase, passing its document_id. Do not search
    every document unless no summary is a clear match.

    Returns:
        A list of documents with document_id, filename, and summary.
    """
    print("[tool] list_knowledgebase_documents", flush=True)
    documents = _list_documents()
    print(f"[tool] list_knowledgebase_documents -> {len(documents)} document(s)", flush=True)
    return {"status": "success", "documents": documents}


@function_tool
def search_faq_knowledgebase(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> dict:
    """Search uploaded knowledge-base documents (FAQ, shipping, returns).

    Args:
        query: The question or topic to look up.
        top_k: Maximum number of matching passages to return.
        document_id: Optional document id. Omit it to search all documents.
    """
    print(
        f"[tool] search_faq_knowledgebase query={query!r} "
        f"document_id={document_id!r} top_k={top_k}",
        flush=True,
    )
    document_id = (document_id or "").strip() or None
    results = _search_documents(query, top_k=top_k, document_id=document_id)
    print(
        f"[tool] search_faq_knowledgebase -> {len(results)} result(s)",
        flush=True,
    )
    return {"status": "success", "results": results}

@function_tool
def search_products(query: str, top_k: int = 5) -> list[dict]:
    """Search the product catalog for items semantically similar to `query`."""
    print(f"[tool] search_products query={query!r} top_k={top_k}", flush=True)
    results = _search_products(query, top_k=top_k)
    print(f"[tool] search_products -> {len(results)} result(s)", flush=True)
    return results
 