"""Read-only product catalog queries."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine
from ecommerce_agent.embeddings import get_provider


def search_products(query: str, top_k: int = 5) -> list[dict]:
    """Return the top_k most similar products using cosine distance."""
    query_vector = get_provider().embed([query])[0]

    with Session(engine) as session:
        # Existing DBs may still use ivfflat lists=100, which returns 0
        # rows on tiny tables unless every list is probed.
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
