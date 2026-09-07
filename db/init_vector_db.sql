-- Safe to re-run against an existing database: if any of these tables already
-- exist, this script stops instead of dropping or altering them. Drop the
-- tables yourself if you want to recreate the schema.

-- Conversation memory is additive and can be created on an existing catalog.
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
    message_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_messages_session_id_idx
    ON agent_messages (session_id, id);

CREATE TABLE IF NOT EXISTS ask_turns (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_words INTEGER NOT NULL,
    answer_words INTEGER NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ask_turns_created_at_idx
    ON ask_turns (created_at DESC);

CREATE TABLE IF NOT EXISTS conversation_feedback (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_id TEXT,
    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversation_feedback_created_at_idx
    ON conversation_feedback (created_at DESC);

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

CREATE INDEX product_embeddings_embedding_idx
    ON product_embeddings
    USING hnsw (embedding vector_cosine_ops);

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
    USING hnsw (embedding vector_cosine_ops);
