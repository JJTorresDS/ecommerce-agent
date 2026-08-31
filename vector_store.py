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
    from vector_store import search_products

    results = search_products("zapatillas para correr", top_k=5)
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
        rows = session.execute(
            text("""
                SELECT product_id, content
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
        {"product_id": row.product_id, "content": row.content}
        for row in rows
    ]