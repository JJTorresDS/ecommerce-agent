# ecommerce-agent

Chat UI and tools over Ollama, OpenRouter, or OpenAI, with a pgvector catalog and knowledge base.

## Run

```bash
uv run uvicorn ecommerce_agent.api.app:app --reload
```

Open http://localhost:8000/ for the chat UI, http://localhost:8000/ecommerce for the catalog, or http://localhost:8000/docs for the API.

If Postgres runs in Docker, start it first. `get_item_details` and vector search read from that database.

## Database

```bash
docker exec -i postgres-pgvector psql -U postgres -d pyrolabs-local < db/init_vector_db.sql
```

Or:

```bash
uv run python db/seed_products.py
```

`init_db()` sizes `VECTOR(...)` from the active provider in `config.py` (`hf` → 1024, `gemini` → 768, `openai` → 1536). Gemini's native vectors are 3072-d; the app requests (and truncates + L2-normalizes) down to 768 so they fit. Switching `EMBEDDING_PROVIDER` after tables exist needs a drop and re-seed — pgvector cannot mix widths:

```sql
DROP TABLE IF EXISTS product_embeddings, document_embeddings, documents CASCADE;
```

Download the local embedding model once (offline HF after that):

```bash
uv run python db/download_model.py
```

## Google Doc sync

Daily job: if Drive `modifiedTime` is newer than `documents.updated_at` / `embedded_at`, re-embed the doc.

```bash
uv run python -m ecommerce_agent.jobs.sync_google_docs
```

Enable the Google Drive API and share the doc with the service account. Credentials default to `secrets/google_service_account.json` (`GOOGLE_SERVICE_ACCOUNT_FILE`).

Two ingest endpoints:

- `POST /documents/google-doc` — character windows (`chunk_chars`). Use for contracts and long-form docs.
- `POST /documents/google-doc/structured` — heading tags. Use for FAQs with Heading 1 / Heading 2 styles.

```bash
curl -X POST http://localhost:8000/documents/google-doc/structured \
  -H 'Content-Type: application/json' \
  -d '{
    "document_url": "https://docs.google.com/document/d/1FlKHKxwltF_2S9ADmkfT3B0ajapSMrVKYWRUXf13mno/edit",
    "summary_tag": "h1",
    "question_tag": "h2"
  }'
```

Text under `h1` becomes `documents.summary` unless you pass `"summary"`. Each `h2` plus the text beneath it is embedded as one chunk.

## Evals

Ground truth lives in `evals/datasets/faq_ground_truth.json`. Generate five shopper-style paraphrases per FAQ (uses `LLM_PROVIDER` from `config.py`):

```bash
uv run python evals/generate_eval_data.py
```

Writes `evals/datasets/faq_eval_synthetic.json`. A tqdm bar advances once per FAQ. Optional `--input` / `--output` paths.

## Config

See `.env` for secrets (`POSTGRES_*`, `OPENAI_API_KEY`, `OPEN_ROUTER_API_KEY`, `GEMINI_API_KEY`). Chat and embedding backends are set in `ecommerce_agent/config.py` (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`) and are not read from `.env`.

- `LLM_PROVIDER` — `ollama` | `openrouter` | `openai` (currently `openai`). `LOCAL_MODEL` is derived (`true` only when the provider is `ollama`).
- `MODEL` — optional env override for the chat model. Defaults: Ollama `qwen2.5:7b`, OpenRouter `nvidia/nemotron-3.5-lightning:free`, OpenAI `gpt-4o-mini`. Provider-specific `OLLAMA_MODEL` / `OPENROUTER_MODEL` / `OPENAI_MODEL` still work as fallbacks.
- `OPENAI_API_KEY` / `OPEN_ROUTER_API_KEY` — required for those chat backends. Ollama uses a dummy key.
- `AGENT_TRACING=true` — OpenAI Agents SDK traces
- `EMBEDDING_PROVIDER` — `hf`, `gemini`, or `openai` in `config.py` (currently `gemini`). Needs `GEMINI_API_KEY` or `OPENAI_API_KEY` as required. `EMBEDDING_MODEL` defaults live in `DEFAULT_EMBEDDING_MODELS`: HF `BAAI/bge-m3` (1024-d), Gemini `gemini-embedding-001` (768-d), OpenAI `text-embedding-3-small` (1536-d). `OPENAI_EMBEDDING_MODEL` is still a fallback for OpenAI. A provider/model mismatch raises `ValueError` telling you to check `config.py`. Vector width is fixed when tables are created; do not switch providers without dropping those tables.

Base URLs are constants in `ecommerce_agent/config.py` (`OLLAMA_BASE_URL`, `OPENROUTER_BASE_URL`, `OPENAI_BASE_URL`, `GEMINI_OPENAI_BASE_URL`) with optional env overrides.

## Layout

Runtime Python lives in `ecommerce_agent/`. Tests live in `tests/` (`uv run pytest`). As-built diagram: `architecture.md`. Agent workflow (TDD, docs): `AGENTS.md`. Proposal that this tree follows: `architecture_proposal.md`.
