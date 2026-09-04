"""Product catalog writes."""

from __future__ import annotations

import csv
import io

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine
from ecommerce_agent.embeddings import get_provider


def _description(product: dict) -> str:
    """Embedding text. Prefers `description`; falls back to `content`."""
    return product.get("description") or product["content"]


def parse_products_csv(text_value: str) -> list[dict]:
    """Parse a UTF-8 CSV with `sku` and `description` columns.

    Raises ValueError with a message suitable for an HTTP 400 body.
    """
    reader = csv.DictReader(io.StringIO(text_value))
    if not reader.fieldnames:
        raise ValueError("CSV is empty")

    required = {"sku", "description"}
    missing = required - {h.strip() for h in reader.fieldnames}
    if missing:
        raise ValueError(
            f"CSV must have columns: sku, description. Missing: {sorted(missing)}"
        )

    products = []
    for i, row in enumerate(reader, start=2):
        sku = (row.get("sku") or "").strip()
        description = (row.get("description") or "").strip()
        if not sku or not description:
            raise ValueError(f"Row {i}: sku and description are required")
        products.append({"sku": sku, "description": description})

    if not products:
        raise ValueError("CSV has no data rows")
    return products


def upsert_products_batch(products: list[dict]) -> None:
    """Insert or update a batch of products and their embeddings."""
    provider = get_provider()
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
    provider = get_provider()
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
