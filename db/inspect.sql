-- Inspect ecommerce-agent tables. Run in pgAdmin (Query Tool) or:
--   make docker-inspect

SELECT current_database() AS database, current_user AS "user";

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT COUNT(*) AS product_rows FROM product_embeddings;
SELECT sku, name, price, embedding_model
FROM product_embeddings
ORDER BY sku;

SELECT COUNT(*) AS document_rows FROM documents;
SELECT id, filename, has_embedding, embedded_at
FROM documents
ORDER BY filename;

SELECT COUNT(*) AS chunk_rows FROM document_embeddings;
SELECT document_id, chunk_index, embedding_model, left(content, 80) AS content_preview
FROM document_embeddings
ORDER BY document_id, chunk_index
LIMIT 50;

SELECT COUNT(*) AS session_rows FROM agent_sessions;
SELECT session_id, created_at, updated_at
FROM agent_sessions
ORDER BY updated_at DESC
LIMIT 20;

SELECT COUNT(*) AS message_rows FROM agent_messages;
SELECT session_id, id, created_at, left(message_data::text, 80) AS message_preview
FROM agent_messages
ORDER BY id DESC
LIMIT 50;

SELECT COUNT(*) AS ask_turn_rows FROM ask_turns;
SELECT created_at, session_id, latency_ms, question_words, answer_words
FROM ask_turns
ORDER BY created_at DESC
LIMIT 20;

SELECT COUNT(*) AS feedback_rows FROM conversation_feedback;
SELECT created_at, session_id, turn_id, rating
FROM conversation_feedback
ORDER BY created_at DESC
LIMIT 20;
