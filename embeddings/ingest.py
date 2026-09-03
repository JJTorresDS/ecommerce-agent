"""
Ingestion pipeline for product embeddings and a local document vector store.

Write-path only: table creation, embedding, and storing content. None of this
runs during a live request -- it's meant to be called from seed scripts or
one-off jobs.

The document store is two tables: `documents` holds file metadata
(including whether chunks have been embedded), and `document_embeddings`
holds the chunk vectors. Hosted `FileSearchTool` cannot point at this
database; search is a `@function_tool` (same pattern as search_products).

Requirements:
    uv add sqlalchemy psycopg[binary] pgvector python-dotenv

Connection is configured via environment variables (see .env.example).

IMPORTANT: run init/init_vector_db.sql once against the database before
using this module (enables the vector extension).

Usage:
    from embeddings.ingest import init_db, upsert_products_batch, upsert_document

    init_db()
    upsert_products_batch([{"sku": "G-001", "name": "...", "price": "$34.950",
                            "description": "..."}])
    upsert_document(filename="faq.txt", content="Shipping takes 3-5 days...",
                    summary="Shipping times and return policy")
"""

import os
import uuid

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

# OpenAI File Search defaults are 800 / 400 tokens. ~4 chars per token.
_CHUNK_CHARS = 3200
_CHUNK_OVERLAP_CHARS = 1600


def _description(product: dict) -> str:
    """Embedding text. Prefers `description`; falls back to `content`."""
    return product.get("description") or product["content"]


def _chunk_text(
    text_value: str,
    max_chars: int = _CHUNK_CHARS,
    overlap: int = _CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """Split a document into overlapping chunks (File Search-style)."""
    text_value = text_value.strip()
    if not text_value:
        return []
    if len(text_value) <= max_chars:
        return [text_value]

    chunks: list[str] = []
    start = 0
    while start < len(text_value):
        end = min(start + max_chars, len(text_value))
        chunk = text_value[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text_value):
            break
        start = end - overlap
    return chunks


def init_db() -> None:
    """Create product and document tables if they do not exist.

    If any of those tables already exist, raises RuntimeError and leaves
    the database unchanged. Drop them manually to recreate the schema.
    Does not ALTER existing tables. The `vector` extension must already
    be enabled (via init/init_vector_db.sql).
    """
    with Session(engine) as session:
        existing = session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN
                      ('product_embeddings', 'documents', 'document_embeddings')
                ORDER BY table_name
            """)
        ).scalars().all()
        if existing:
            raise RuntimeError(
                "Refusing to initialize: these tables already exist: "
                f"{', '.join(existing)}. Drop them manually if you want to "
                "recreate the schema, then retry."
            )

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

        session.execute(
            text("""
                CREATE TABLE documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    has_embedding BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now(),
                    embedded_at TIMESTAMPTZ
                )
            """)
        )
        session.execute(
            text(f"""
                CREATE TABLE document_embeddings (
                    id SERIAL PRIMARY KEY,
                    document_id TEXT NOT NULL
                        REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({provider.embedding_dim}) NOT NULL,
                    embedding_model TEXT NOT NULL,
                    UNIQUE (document_id, chunk_index)
                )
            """)
        )
        session.execute(
            text("""
                CREATE INDEX document_embeddings_embedding_idx
                ON document_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
        )
        session.commit()


def upsert_document(
    filename: str,
    content: str,
    document_id: str | None = None,
    summary: str | None = None,
) -> dict:
    """Insert or replace a document and embed its chunks.

    Re-uploading the same `filename` (or the same `document_id`, if
    given) replaces the previous file and its chunks. `has_embedding`
    stays false until chunks are written, then `embedded_at` is set.
    Pass `document_id` to use a stable identifier such as a Google Doc ID.
    `summary` is optional catalog text for the LLM to choose a document
    before running embedding search. On update, omit it to keep the
    stored summary.
    """
    chunks = _chunk_text(content)
    if not chunks:
        raise ValueError(f"Document '{filename}' has no text to embed")

    vectors = provider.embed(chunks)

    with Session(engine) as session:
        existing_id = None
        if document_id is not None:
            existing_id = session.execute(
                text("SELECT id FROM documents WHERE id = :id"),
                {"id": document_id},
            ).scalar_one_or_none()
        else:
            existing_id = session.execute(
                text("SELECT id FROM documents WHERE filename = :filename"),
                {"filename": filename},
            ).scalar_one_or_none()

        if existing_id is None:
            document_id = document_id or f"file_{uuid.uuid4().hex}"
            session.execute(
                text("""
                    INSERT INTO documents (
                        id, filename, content, summary, has_embedding, updated_at
                    )
                    VALUES (
                        :id, :filename, :content, :summary, FALSE, now()
                    )
                """),
                {
                    "id": document_id,
                    "filename": filename,
                    "content": content,
                    "summary": summary,
                },
            )
        else:
            document_id = existing_id
            session.execute(
                text("""
                    UPDATE documents
                    SET filename = :filename,
                        content = :content,
                        summary = COALESCE(:summary, documents.summary),
                        has_embedding = FALSE,
                        updated_at = now(),
                        embedded_at = NULL
                    WHERE id = :id
                """),
                {
                    "id": document_id,
                    "filename": filename,
                    "content": content,
                    "summary": summary,
                },
            )
            session.execute(
                text("DELETE FROM document_embeddings WHERE document_id = :id"),
                {"id": document_id},
            )

        session.execute(
            text("""
                INSERT INTO document_embeddings (
                    document_id, chunk_index, content, embedding, embedding_model
                )
                VALUES (
                    :document_id, :chunk_index, :content,
                    CAST(:embedding AS vector), :embedding_model
                )
            """),
            [
                {
                    "document_id": document_id,
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": str(vector.tolist()),
                    "embedding_model": provider.model_name,
                }
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ],
        )
        session.execute(
            text("""
                UPDATE documents
                SET has_embedding = TRUE, embedded_at = now()
                WHERE id = :id
            """),
            {"id": document_id},
        )
        stored_summary = session.execute(
            text("SELECT summary FROM documents WHERE id = :id"),
            {"id": document_id},
        ).scalar_one()
        session.commit()

    return {
        "document_id": document_id,
        "filename": filename,
        "summary": stored_summary,
        "chunks": len(chunks),
        "has_embedding": True,
    }


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
