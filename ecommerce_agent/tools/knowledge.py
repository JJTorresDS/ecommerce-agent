from agents import function_tool

from ecommerce_agent.retrieval.documents import list_documents as _list_documents
from ecommerce_agent.retrieval.documents import search_documents as _search_documents


@function_tool
def list_knowledgebase_documents() -> dict:
    """List knowledge-base documents and their summaries.

    Call this first for FAQ, shipping, returns, or support questions.
    Read the summaries and pick the document that matches the user's
    question. Then search that document with search_faq_knowledgebase,
    passing its document_id.

    Returns:
        A list of documents with document_id, filename, and summary.
    """
    print("[tool] list_knowledgebase_documents", flush=True)
    documents = _list_documents()
    print(
        f"[tool] list_knowledgebase_documents -> {len(documents)} document(s)",
        flush=True,
    )
    return {"status": "success", "documents": documents}


@function_tool
def search_faq_knowledgebase(
    query: str,
    document_id: str | None = None,
    top_k: int = 5,
) -> dict:
    """Search a knowledge-base document for passages matching `query`.

    Call list_knowledgebase_documents first and pass the matching
    document_id. document_id may be omitted only when exactly one
    document exists.

    Args:
        query: The question or topic to look up.
        document_id: Knowledge-base document id from the catalog.
        top_k: Maximum number of matching passages to return.
    """
    print(
        f"[tool] search_faq_knowledgebase query={query!r} "
        f"document_id={document_id!r} top_k={top_k}",
        flush=True,
    )
    document_id = (document_id or "").strip() or None
    catalog = _list_documents()
    if document_id is None:
        if len(catalog) == 0:
            return {
                "status": "empty",
                "results": [],
                "message": "No knowledge-base documents have been ingested.",
            }
        if len(catalog) == 1:
            document_id = catalog[0]["document_id"]
        else:
            return {
                "status": "need_document_id",
                "message": (
                    "Call list_knowledgebase_documents first and pass "
                    "document_id for the matching file."
                ),
                "documents": catalog,
            }

    results = _search_documents(query, top_k=top_k, document_id=document_id)
    print(
        f"[tool] search_faq_knowledgebase -> {len(results)} result(s)",
        flush=True,
    )
    return {"status": "success", "results": results}
