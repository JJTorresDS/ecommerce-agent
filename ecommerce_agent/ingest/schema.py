"""Create product and document tables if they do not exist. Never ALTER."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine
from ecommerce_agent.embeddings import get_provider


def init_db() -> None:
    """Create product and document tables if they do not exist.

    If any of those tables already exist, raises RuntimeError and leaves
    the database unchanged. Drop them manually to recreate the schema.
    """
    provider = get_provider()
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
                USING hnsw (embedding vector_cosine_ops)
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
                USING hnsw (embedding vector_cosine_ops)
            """)
        )
        session.commit()
