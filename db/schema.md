# Database schema

Postgres + pgvector tables used by the app. **Source of truth for CREATE** is Python: `ecommerce_agent/ingest/schema.py` (`init_db()`), `ecommerce_agent/agent/memory.py`, and `ecommerce_agent/monitoring/store.py`. Prefer `make docker-seed` (`db/seed_products.py`) so `VECTOR(...)` width matches `EMBEDDING_PROVIDER` in `config.py`.

`db/init_vector_db.sql` is a manual `psql` snapshot hardcoded to HF / 1024-d. It also adds `product_embeddings.created_at`, which `init_db()` does not. Do not mix embedding widths in one database.

No live `ALTER`. Catalog tables (`product_embeddings`, `documents`, `document_embeddings`) are created once; `init_db()` refuses if they already exist. Memory and monitoring tables use `CREATE TABLE IF NOT EXISTS` so they can appear on an existing catalog. If `conversation_feedback.rating` is still text (`'up'` / `'down'`), the next `/ask` or `/feedback` drops that table and recreates it with integer `1` / `-1`.

Inspect live rows: `make docker-inspect` (`db/inspect.sql`) or pgAdmin.

Column types below are what `init_db()` / ensure helpers emit. `VECTOR(n)` is 1024 (`hf`), 768 (`gemini`), or 1536 (`openai`).

## Catalog

Written only by **ingest**. Read by **retrieval** (`search_products`, `get_item_details`).

### `product_embeddings`

One row per SKU. Dummy seed data is in `db/seed_products.py`.

| Column | Type | Purpose |
|---|---|---|
| `id` | `SERIAL` PK | Surrogate key |
| `sku` | `TEXT` UNIQUE NOT NULL | Catalog id (for example `G-001`) |
| `name` | `TEXT` | Display name |
| `price` | `TEXT` | Price as stored text (not a numeric type) |
| `description` | `TEXT` | Product copy used for embedding |
| `content` | `TEXT` NOT NULL | Text that was embedded |
| `embedding` | `VECTOR(n)` NOT NULL | Dense vector for cosine search |
| `embedding_model` | `TEXT` NOT NULL | Model id that produced the vector |

Index: `product_embeddings_embedding_idx` — HNSW on `embedding` (`vector_cosine_ops`).

## Knowledge base

Written by **ingest** (`upsert_document`, structured Google Doc ingest) and `jobs.sync_google_docs`. Read by **retrieval** (`list_knowledgebase_documents`, `search_faq_knowledgebase`).

### `documents`

One row per Google Doc (or uploaded knowledge file). `id` is the Google Doc id. `filename` is the Doc title.

| Column | Type | Purpose |
|---|---|---|
| `id` | `TEXT` PK | Document id (Google Doc id) |
| `filename` | `TEXT` UNIQUE NOT NULL | Title shown to the agent |
| `content` | `TEXT` NOT NULL | Full markdown / text |
| `summary` | `TEXT` | Short blurb the LLM reads before searching; structured ingest fills this from `summary_tag` unless the caller passes `summary` |
| `has_embedding` | `BOOLEAN` NOT NULL DEFAULT `FALSE` | Whether chunks exist |
| `created_at` | `TIMESTAMPTZ` DEFAULT `now()` | First insert |
| `updated_at` | `TIMESTAMPTZ` DEFAULT `now()` | Last content write |
| `embedded_at` | `TIMESTAMPTZ` | Last successful embed; sync compares Drive `modifiedTime` to `updated_at` / `embedded_at` |

Ids that start with `file_` are skipped by the sync job.

### `document_embeddings`

One row per chunk. Deleted with the parent document (`ON DELETE CASCADE`).

| Column | Type | Purpose |
|---|---|---|
| `id` | `SERIAL` PK | Surrogate key |
| `document_id` | `TEXT` NOT NULL FK → `documents.id` | Parent document |
| `chunk_index` | `INTEGER` NOT NULL | Order within the document |
| `content` | `TEXT` NOT NULL | Chunk text that was embedded |
| `embedding` | `VECTOR(n)` NOT NULL | Dense vector for cosine search |
| `embedding_model` | `TEXT` NOT NULL | Model id that produced the vector |

Constraint: `UNIQUE (document_id, chunk_index)`.

Index: `document_embeddings_embedding_idx` — HNSW on `embedding` (`vector_cosine_ops`).

## Conversation memory

Written by **agent.memory** (`PostgresSession`) when `POST /ask` includes `session_id`. The chat UI stores that id in `sessionStorage`. Omit `session_id` for a one-off question (evals do this).

### `agent_sessions`

| Column | Type | Purpose |
|---|---|---|
| `session_id` | `TEXT` PK | Browser / caller session id |
| `created_at` | `TIMESTAMPTZ` DEFAULT `now()` | First turn |
| `updated_at` | `TIMESTAMPTZ` DEFAULT `now()` | Last write |

### `agent_messages`

Agents SDK items for replay. `message_data` is JSONB (role, content, tool calls).

| Column | Type | Purpose |
|---|---|---|
| `id` | `SERIAL` PK | Insertion order within a session |
| `session_id` | `TEXT` NOT NULL FK → `agent_sessions.session_id` | Parent session (`ON DELETE CASCADE`) |
| `message_data` | `JSONB` NOT NULL | One SDK message item |
| `created_at` | `TIMESTAMPTZ` DEFAULT `now()` | Insert time |

Index: `agent_messages_session_id_idx` on `(session_id, id)`.

## Production monitoring

Written by **monitoring** on `POST /ask` and `POST /feedback`. Grafana reads recent rows; Prometheus scrapes `GET /metrics` for the same latency / word / thumbs series.

### `ask_turns`

One row per `/ask` reply. `id` is the `turn_id` returned to the client (thumbs attach to this).

| Column | Type | Purpose |
|---|---|---|
| `id` | `TEXT` PK | `turn_id` (UUID string) |
| `session_id` | `TEXT` | Chat session if the client sent one |
| `question` | `TEXT` NOT NULL | User question |
| `answer` | `TEXT` NOT NULL | Agent reply |
| `question_words` | `INTEGER` NOT NULL | Whitespace word count |
| `answer_words` | `INTEGER` NOT NULL | Whitespace word count |
| `latency_ms` | `DOUBLE PRECISION` NOT NULL | End-to-end ask latency |
| `created_at` | `TIMESTAMPTZ` DEFAULT `now()` | Insert time |

Index: `ask_turns_created_at_idx` on `created_at DESC`.

### `conversation_feedback`

Thumbs from the chat UI. `rating` is `1` (helpful) or `-1` (not helpful).

| Column | Type | Purpose |
|---|---|---|
| `id` | `SERIAL` PK | Surrogate key |
| `session_id` | `TEXT` NOT NULL | Chat session |
| `turn_id` | `TEXT` | Optional `ask_turns.id` so Grafana can join a thumb to a reply |
| `rating` | `INTEGER` NOT NULL | `CHECK (rating IN (1, -1))` |
| `created_at` | `TIMESTAMPTZ` DEFAULT `now()` | Insert time |

Index: `conversation_feedback_created_at_idx` on `created_at DESC`.

## Relationships

```text
documents 1 ──< document_embeddings
agent_sessions 1 ──< agent_messages
ask_turns.id  (optional join)  conversation_feedback.turn_id
```

Catalog tables are independent of conversation tables. Feedback does not use a SQL foreign key to `ask_turns` so a thumb can still store if the turn row is missing.
