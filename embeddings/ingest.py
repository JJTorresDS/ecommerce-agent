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
using this module (enables the vector extension). init_db() below drops
and recreates the product_embeddings table from the schema in this file.

Usage from a notebook or script:
    from embeddings.ingest import init_db, upsert_products_batch

    init_db()
    upsert_products_batch([
        {
            "sku": "G-001",
            "name": "KID LOVE VEST",
            "price": "$34.950",
            "description": "KID LOVE VEST — Discount, Winter, Girls, 50% off.",
        }
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


def _description(product: dict) -> str:
    """Embedding text. Seed/catalog rows use `description`; CSV upload
    still sends `content`, which is treated as the same field.
    """
    return product.get("description") or product["content"]


def init_db() -> None:
    """Drop and recreate the product_embeddings table.

    The `vector` extension itself must already be enabled (via
    init/init_vector_db.sql) before this will work.

    Uses provider.embedding_dim, so the column width automatically
    matches whichever provider (HF or Gemini) is active when this
    runs -- switching EMBEDDING_PROVIDER later means re-running this
    function (VECTOR(n) is fixed at creation time).
    """
    with Session(engine) as session:
        session.execute(text("DROP TABLE IF EXISTS product_embeddings CASCADE"))
        session.execute(
            text(f"""
                CREATE TABLE product_embeddings (
                    id SERIAL PRIMARY KEY,
                    sku TEXT UNIQUE NOT NULL,
                    name TEXT,
                    price TEXT,
                    description TEXT,
                    content TEXT NOT NULL,
                    embedding VECTOR({provider.embedding_dim}) NOT NULL,
                    embedding_model TEXT NOT NULL
                )
            """)
        )
        session.execute(
            text("""
                CREATE INDEX product_embeddings_embedding_idx
                ON product_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
        )
        session.commit()


def upsert_products_batch(products: list[dict]) -> None:
    """Insert or update a batch of products and their embeddings.

    Each dict needs a unique `sku` and text to embed (`description` or
    `content`). Optional catalog fields: name, price.
    """
    rows = []
    texts = []
    for product in products:
        description = _description(product)
        rows.append(
            {
                "sku": product["sku"],
                "name": product.get("name"),
                "price": product.get("price"),
                "description": description,
                "content": description,
            }
        )
        texts.append(description)

    vectors = provider.embed(texts)

    with Session(engine) as session:
        session.execute(
            text("""
                INSERT INTO product_embeddings (
                    sku, name, price, description, content,
                    embedding, embedding_model
                )
                VALUES (
                    :sku, :name, :price, :description, :content,
                    CAST(:embedding AS vector), :embedding_model
                )
                ON CONFLICT (sku)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    price = EXCLUDED.price,
                    description = EXCLUDED.description,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model
            """),
            [
                {
                    **row,
                    "embedding": str(vector.tolist()),
                    "embedding_model": provider.model_name,
                }
                for row, vector in zip(rows, vectors)
            ],
        )
        session.commit()


def update_embedding(sku: str) -> None:
    """Recompute the embedding for a product using its stored description."""
    with Session(engine) as session:
        description = session.execute(
            text("""
                SELECT COALESCE(description, content)
                FROM product_embeddings
                WHERE sku = :sku
            """),
            {"sku": sku},
        ).scalar_one()

        vector = provider.embed([description])[0]

        session.execute(
            text("""
                UPDATE product_embeddings
                SET embedding = CAST(:embedding AS vector),
                    embedding_model = :embedding_model,
                    content = :description,
                    description = :description
                WHERE sku = :sku
            """),
            {
                "sku": sku,
                "description": description,
                "embedding": str(vector.tolist()),
                "embedding_model": provider.model_name,
            },
        )
        session.commit()
