-- Runs automatically on first container startup (via docker-entrypoint-initdb.d)

CREATE EXTENSION IF NOT EXISTS vector;

-- bge-m3 produces 1024-dimensional embeddings
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,
    product_id TEXT NOT NULL UNIQUE,
    name TEXT,
    price TEXT,
    description TEXT,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Speeds up nearest-neighbor search as the table grows.
-- ivfflat needs at least a few hundred rows before it's useful;
-- fine to leave this in from the start.
CREATE INDEX IF NOT EXISTS product_embeddings_embedding_idx
    ON product_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);