"""
Runtime read path for product embeddings.

This module owns the DB connection and the *query* side only --
searching existing embeddings via pgvector's cosine distance operator.

All *write* operations (creating the table, upserting products,
recomputing embeddings) live in embeddings/ingest.py instead, since
those only ever run during setup/seeding, never during a live request.

Requirements:
    uv add sqlalchemy psycopg[binary] pgvector python-dotenv

Connection is configured via environment variables (see .env.example).

IMPORTANT: run init/init_vector_db.sql once against the database before
using this module (enables the vector extension, creates the table).

Usage:
    from vector_store import search_products, search_documents, list_documents

    results = search_products("zapatillas para correr", top_k=5)
    catalog = list_documents()
    docs = search_documents("política de envíos", document_id=catalog[0]["document_id"])
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from embeddings import provider

load_dotenv()

DB_URL = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(DB_URL, echo=False)


def search_products(query: str, top_k: int = 5) -> list[dict]:
    """Return the top_k most similar products using cosine distance.

    Uses pgvector's `<=>` operator, which computes true cosine distance
    directly in SQL (lower = more similar) -- it divides by each
    vector's norm internally, so this works regardless of whether the
    stored vectors happen to be pre-normalized. `provider.similarity()`
    is there for the separate case where you need to compute similarity
    in Python rather than in a SQL query.
    """
    query_vector = provider.embed([query])[0]

    with Session(engine) as session:
        # ivfflat with lists=100 returns 0 rows on tiny tables unless we
        # probe every list (default probes=1).
        session.execute(text("SET LOCAL ivfflat.probes = 100"))
        rows = session.execute(
            text("""
                SELECT sku, name, price, description, content
                FROM product_embeddings
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :top_k
            """),
            {
                "query_vector": str(query_vector.tolist()),
                "top_k": top_k,
            },
        ).all()

    return [
        {
            "sku": row.sku,
            "name": row.name,
            "price": row.price,
            "description": row.description or row.content,
        }
        for row in rows
    ]


def get_product_by_sku(sku: str) -> dict | None:
    """Return the catalog row for `sku`, or None if it does not exist."""
    with Session(engine) as session:
        row = session.execute(
            text("""
                SELECT sku, name, price, description, content
                FROM product_embeddings
                WHERE sku = :sku
            """),
            {"sku": sku},
        ).first()

    if row is None:
        return None

    return {
        "sku": row.sku,
        "name": row.name,
        "price": row.price,
        "description": row.description or row.content,
    }


def list_documents() -> list[dict]:
    """Return document ids, filenames, and summaries (no chunk text).

    Intended as a cheap catalog so a model can pick which document to
    search instead of ranking every embedding.
    """
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


def search_documents(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    """Return the top_k most similar chunks from documents that have embeddings.

    Pass `document_id` to search only that document.
    """
    query_vector = provider.embed([query])[0]
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
        # ivfflat with lists=100 returns 0 rows on tiny tables unless we
        # probe every list (default probes=1).
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