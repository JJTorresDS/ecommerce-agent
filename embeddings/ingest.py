"""
Ingestion pipeline for product embeddings.

Everything here is write-path only: creating the table, embedding and
storing product content, and recomputing embeddings later (e.g. after
a model change). None of this runs during a live request -- it's meant
to be called from seed scripts (see seed_products.py) or one-off jobs.

Requirements:
    uv add sqlalchemy psycopg[binary] pgvector python-dotenv

Connection is configured via environment variables (see .env.example).

IMPORTANT: run init/init_vector_db.sql once against the database before
using this module (enables the vector extension). init_db() below will
create the product_embeddings table itself if it doesn't exist yet.

Usage from a notebook or script:
    from embeddings.ingest import init_db, upsert_products_batch

    init_db()
    upsert_products_batch([
        {"product_id": "SKU123", "content": "Zapatillas de running con amortiguación"}
    ])
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


def init_db() -> None:
    """Create the product_embeddings table if it doesn't exist yet.

    The `vector` extension itself must already be enabled (via
    init/init_vector_db.sql) before this will work.

    Uses provider.embedding_dim, so the column width automatically
    matches whichever provider (HF or Gemini) is active when this
    runs -- switching EMBEDDING_PROVIDER later means you'll want a
    fresh table (or a migration), not just re-running this function,
    since VECTOR(n) is fixed at creation time.

    NOTE: this includes embedding_model, which an earlier version of
    this file omitted from the CREATE TABLE despite upsert_products_batch
    and update_embedding both writing to it -- that mismatch would have
    caused inserts to fail against a freshly created table.
    """
    with Session(engine) as session:
        session.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS product_embeddings (
                    id SERIAL PRIMARY KEY,
                    product_id TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({provider.embedding_dim}) NOT NULL,
                    embedding_model TEXT NOT NULL
                )
            """)
        )
        session.commit()


def upsert_products_batch(products: list[dict]) -> None:
    """Insert or update a batch of products and their embeddings.

    products: list of dicts like {"product_id": "SKU123", "content": "..."}
    """
    contents = [p["content"] for p in products]
    vectors = provider.embed(contents)

    with Session(engine) as session:
        session.execute(
            text("""
                INSERT INTO product_embeddings (product_id, content, embedding, embedding_model)
                VALUES (:product_id, :content, CAST(:embedding AS vector), :embedding_model)
                ON CONFLICT (product_id)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model
            """),
            [
                {
                    "product_id": p["product_id"],
                    "content": p["content"],
                    "embedding": str(v.tolist()),
                    "embedding_model": provider.model_name,
                }
                for p, v in zip(products, vectors)
            ],
        )
        session.commit()


def update_embedding(product_id: str) -> None:
    """Recompute the embedding for a product using its existing content."""
    with Session(engine) as session:
        content = session.execute(
            text("SELECT content FROM product_embeddings WHERE product_id = :product_id"),
            {"product_id": product_id},
        ).scalar_one()

        vector = provider.embed([content])[0]

        session.execute(
            text("""
                UPDATE product_embeddings
                SET embedding = CAST(:embedding AS vector), embedding_model = :embedding_model
                WHERE product_id = :product_id
            """),
            {
                "product_id": product_id,
                "embedding": str(vector.tolist()),
                "embedding_model": provider.model_name,
            },
        )
        session.commit()