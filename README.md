# ecommerce-agent

Chat UI and tools over a local (Ollama) or OpenRouter model, with a pgvector catalog and knowledge base.

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

`init_db()` sizes `VECTOR(...)` from the active provider (`hf` → 1024, `gemini` → 768). Gemini's native vectors are 3072-d; the app requests (and truncates + L2-normalizes) down to 768 so they fit. Switching `EMBEDDING_PROVIDER` after tables exist needs a drop and re-seed — pgvector cannot mix widths:

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

Ground truth lives in `evals/datasets/faq_ground_truth.json`. Generate five shopper-style paraphrases per FAQ (uses Ollama or OpenRouter from `.env`):

```bash
uv run python evals/generate_eval_data.py
```

Writes `evals/datasets/faq_eval_synthetic.json`. A tqdm bar advances once per FAQ. Optional `--input` / `--output` paths.

## Config

See `.env`. Useful flags:

- `LOCAL_MODEL=true` — Ollama (`OLLAMA_MODEL`, default `qwen2.5:7b`)
- `AGENT_TRACING=true` — OpenAI Agents SDK traces
- `EMBEDDING_PROVIDER=hf` or `gemini` (`GEMINI_API_KEY` required for Gemini). Vector width is fixed when tables are created; do not switch providers without dropping those tables.

## Layout

Runtime Python lives in `ecommerce_agent/`. Tests live in `tests/` (`uv run pytest`). As-built diagram: `architecture.md`. Agent workflow (TDD, docs): `AGENTS.md`. Proposal that this tree follows: `architecture_proposal.md`.
