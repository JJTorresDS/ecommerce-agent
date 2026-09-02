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

_ADD_COLUMN_SQL = [
    "ALTER TABLE product_embeddings ADD COLUMN IF NOT EXISTS name TEXT",
    "ALTER TABLE product_embeddings ADD COLUMN IF NOT EXISTS price TEXT",
    "ALTER TABLE product_embeddings ADD COLUMN IF NOT EXISTS description TEXT",
    "ALTER TABLE product_embeddings ADD COLUMN IF NOT EXISTS embedding_model TEXT",
]


def _sku(product: dict) -> str:
    return product.get("sku") or product["product_id"]


def _description(product: dict) -> str:
    """Embedding text. Seed/catalog rows use `description`; CSV upload
    still sends `content`, which is treated as the same field.
    """
    return product.get("description") or product["content"]


def init_db() -> None:
    """Create the product_embeddings table if it doesn't exist yet.

    The `vector` extension itself must already be enabled (via
    init/init_vector_db.sql) before this will work.

    Uses provider.embedding_dim, so the column width automatically
    matches whichever provider (HF or Gemini) is active when this
    runs -- switching EMBEDDING_PROVIDER later means you'll want a
    fresh table (or a migration), not just re-running this function,
    since VECTOR(n) is fixed at creation time.

    Also ALTERs in name/price/description so an existing table created
    before those columns existed still matches the current schema.
    """
    with Session(engine) as session:
        session.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS product_embeddings (
                    id SERIAL PRIMARY KEY,
                    product_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    price TEXT,
                    description TEXT,
                    content TEXT NOT NULL,
                    embedding VECTOR({provider.embedding_dim}) NOT NULL,
                    embedding_model TEXT NOT NULL
                )
            """)
        )
        for stmt in _ADD_COLUMN_SQL:
            session.execute(text(stmt))
        session.commit()


def delete_all_products() -> None:
    """Remove every product row. Used by the seed script so dummy data
    matches the current storefront instead of mixing in leftover SKUs.
    """
    with Session(engine) as session:
        session.execute(text("DELETE FROM product_embeddings"))
        session.commit()


def upsert_products_batch(products: list[dict]) -> None:
    """Insert or update a batch of products and their embeddings.

    Each dict needs a unique id (`sku` or `product_id`) and text to
    embed (`description` or `content`). Optional catalog fields: name,
    price.
    """
    rows = []
    texts = []
    for product in products:
        description = _description(product)
        rows.append(
            {
                "product_id": _sku(product),
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
                    product_id, name, price, description, content,
                    embedding, embedding_model
                )
                VALUES (
                    :product_id, :name, :price, :description, :content,
                    CAST(:embedding AS vector), :embedding_model
                )
                ON CONFLICT (product_id)
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


def update_embedding(product_id: str) -> None:
    """Recompute the embedding for a product using its stored description."""
    with Session(engine) as session:
        description = session.execute(
            text("""
                SELECT COALESCE(description, content)
                FROM product_embeddings
                WHERE product_id = :product_id
            """),
            {"product_id": product_id},
        ).scalar_one()

        vector = provider.embed([description])[0]

        session.execute(
            text("""
                UPDATE product_embeddings
                SET embedding = CAST(:embedding AS vector),
                    embedding_model = :embedding_model,
                    content = :description,
                    description = :description
                WHERE product_id = :product_id
            """),
            {
                "product_id": product_id,
                "description": description,
                "embedding": str(vector.tolist()),
                "embedding_model": provider.model_name,
            },
        )
        session.commit()
