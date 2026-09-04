"""Read-only knowledge-base queries."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine
from ecommerce_agent.embeddings import get_provider


def list_documents() -> list[dict]:
    """Return document ids, filenames, and summaries (no chunk text)."""
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT id, filename, summary, has_embedding
                FROM documents
                ORDER BY filename
            """)
        ).all()

    return [
        {
            "document_id": row.id,
            "filename": row.filename,
            "summary": row.summary,
            "has_embedding": row.has_embedding,
        }
        for row in rows
    ]


def list_google_documents() -> list[dict]:
    """Return ingested Google Docs (ids that were not generated as file_*)."""
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT id, filename, summary, updated_at, embedded_at, has_embedding
                FROM documents
                WHERE id NOT LIKE 'file_%'
                ORDER BY filename
            """)
        ).all()

    return [
        {
            "document_id": row.id,
            "filename": row.filename,
            "summary": row.summary,
            "updated_at": row.updated_at,
            "embedded_at": row.embedded_at,
            "has_embedding": row.has_embedding,
        }
        for row in rows
    ]


def search_documents(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    """Return the top_k most similar chunks from documents that have embeddings."""
    query_vector = get_provider().embed([query])[0]
    document_id = (document_id or "").strip() or None

    sql = """
        SELECT
            d.filename,
            d.id AS document_id,
            de.chunk_index,
            de.content
        FROM document_embeddings de
        JOIN documents d ON d.id = de.document_id
        WHERE d.has_embedding = TRUE
    """
    params: dict = {
        "query_vector": str(query_vector.tolist()),
        "top_k": top_k,
    }
    if document_id is not None:
        sql += " AND d.id = :document_id"
        params["document_id"] = document_id
    sql += """
        ORDER BY de.embedding <=> CAST(:query_vector AS vector)
        LIMIT :top_k
    """

    with Session(engine) as session:
        session.execute(text("SET LOCAL ivfflat.probes = 100"))
        rows = session.execute(text(sql), params).all()

    return [
        {
            "filename": row.filename,
            "document_id": row.document_id,
            "chunk_index": row.chunk_index,
            "content": row.content,
        }
        for row in rows
    ]
