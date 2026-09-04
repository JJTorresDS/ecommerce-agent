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

## Config

See `.env`. Useful flags:

- `LOCAL_MODEL=true` — Ollama (`OLLAMA_MODEL`, default `qwen2.5:7b`)
- `AGENT_TRACING=true` — OpenAI Agents SDK traces
- `EMBEDDING_PROVIDER=hf` or `gemini`

## Layout

Runtime Python lives in `ecommerce_agent/`. As-built diagram: `architecture.md`. Proposal that this tree follows: `architecture_proposal.md`.
