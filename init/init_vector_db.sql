-- Runs automatically on first container startup (via docker-entrypoint-initdb.d)
-- Safe to re-run against an existing database: if any of these tables already
-- exist, this script stops instead of dropping or altering them. Drop the
-- tables yourself if you want to recreate the schema.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN (
              'product_embeddings',
              'documents',
              'document_embeddings'
          )
    ) THEN
        RAISE EXCEPTION
            'Refusing to initialize: product_embeddings, documents, and/or document_embeddings already exist. Drop them manually if you want to recreate the schema, then retry.';
    END IF;
END $$;

CREATE EXTENSION IF NOT EXISTS vector;

-- bge-m3 produces 1024-dimensional embeddings
CREATE TABLE product_embeddings (
    id SERIAL PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
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
CREATE INDEX product_embeddings_embedding_idx
    ON product_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    has_embedding BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    embedded_at TIMESTAMPTZ
);

CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX document_embeddings_embedding_idx
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
