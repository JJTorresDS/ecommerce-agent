# ecommerce-agent

Chat UI and tools over Ollama, OpenRouter, OpenAI, or Mistral, with a pgvector catalog and knowledge base.

## Run

Copy `.env.example` to `.env` and fill in API keys. Then start Postgres (pgvector), the API, MLflow, Prometheus, and Grafana:

```bash
cp .env.example .env
make docker-up
make docker-seed
```

Same as `docker compose up --build -d`, then `docker compose run --rm app uv run --frozen --no-dev python db/seed_products.py`.

Open [http://localhost:8000/](http://localhost:8000/) for the chat UI (thumbs up/down after each reply), [http://localhost:8000/ecommerce](http://localhost:8000/ecommerce) for the catalog, [http://localhost:8000/docs](http://localhost:8000/docs) for the API, [http://localhost:5000](http://localhost:5000) for MLflow evals, [http://localhost:3000](http://localhost:3000) for Grafana production dashboards (login `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`, default `admin` / `admin`), [http://localhost:9090](http://localhost:9090) for Prometheus, and [http://localhost:5050](http://localhost:5050) for pgAdmin.

The first image build installs CPU PyTorch and can take several minutes. Python is pinned to `>=3.12,<3.14` (`pyproject.toml`) because Torch has no 3.14 Windows wheels; Compose runs `uv run --frozen` so app/MLflow do not re-resolve on start.

Stop with `make docker-down`. Logs: `docker compose logs -f app`.

Local Ollama (only if `LLM_PROVIDER` in `config.py` is `ollama`): `docker compose --profile ollama up --build -d` and set `OLLAMA_BASE_URL=http://ollama:11434/v1` in `.env`.

To run the API on the host instead of Compose (`make run_app`), keep `POSTGRES_HOST=localhost` in `.env` and still start Postgres with Compose.

## Database

Compose Postgres is empty until you seed. `init_db()` enables the pgvector extension, then sizes `VECTOR(...)` from the active provider in `config.py` (`hf` → 1024, `gemini` → 768, `openai` → 1536). Gemini's native vectors are 3072-d; the app requests (and truncates + L2-normalizes) down to 768 so they fit. The same call creates conversation tables `agent_sessions` and `agent_messages` and production tables `ask_turns` and `conversation_feedback` if they are missing, including when the product catalog already exists.

The chat UI keeps a `session_id` in `sessionStorage` and sends it on `POST /ask`. The agent loads and stores turns for that id in Postgres so follow-ups keep context. Omit `session_id` for a one-off question. The first stored turn also creates the tables if seed has not run yet. Each reply returns a `turn_id`; use 👍 / 👎 on the bubble to `POST /feedback`. Production latency, word counts, and feedback go to Prometheus + Grafana. Offline evals stay in MLflow. Langfuse still traces tool calls in the cloud.

```bash
make docker-seed
```

Explore tables in pgAdmin at [http://localhost:5050](http://localhost:5050) (login `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` from `.env.example`, default `admin@example.com` / `admin`). Register host `postgres`, port `5432`, database `pyrolabs-local`, user/password from `POSTGRES_*`. The saved server **ecommerce-agent** is preloaded from `db/pgadmin/servers.json`. Paste `db/inspect.sql` in the Query Tool, or print it in the terminal:

```bash
make docker-inspect
```

To add **only pgAdmin** to an already running stack (no image rebuild, does not recreate app/mlflow):

```bash
docker compose up -d pgadmin
```

Same as `make docker-pgadmin`. Compose starts Postgres if it is not up yet, then pulls `dpage/pgadmin4` and starts that service.

Host equivalent (Postgres already running):

```bash
uv run python db/seed_products.py
```

Switching `EMBEDDING_PROVIDER` after tables exist needs a drop and re-seed — pgvector cannot mix widths:

```sql
DROP TABLE IF EXISTS product_embeddings, document_embeddings, documents CASCADE;
```

The SQL file `db/init_vector_db.sql` is the HF/1024-d schema for a manual `psql` load. Prefer `seed_products.py` so width matches `config.py`.

Download the local embedding model once if you use `EMBEDDING_PROVIDER = "hf"` (offline HF after that):

```bash
uv run python db/download_model.py
```



## Google Doc sync

Daily job: if Drive `modifiedTime` is newer than `documents.updated_at` / `embedded_at`, re-embed the doc.

```bash
uv run python -m ecommerce_agent.jobs.sync_google_docs
```

Enable the Google Drive API and share the doc with the service account. Credentials default to `secrets/google_service_account.json` at the project root (`GOOGLE_SERVICE_ACCOUNT_FILE`). Relative credential paths are resolved from the project root, so notebooks in `notebooks/` can use that same path.

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

How the datasets and scripts fit together, plus run commands: `evals/evaluation.md`.

Generate synthetic FAQ questions:

```bash
uv run python evals/generate_eval_data.py
```

Search hit-rate (Postgres with ingested FAQ chunks). `--search-type` is required and is logged to MLflow as `search_type`:

```bash
make evaluate_retrieval SEARCH_TYPE=genai_001_embedding
```

Agent answer correctness (`build_agent()`, one row at a time, 1s pause after each). `--provider` and `--experiment` are required; optional `--n` limits how many rows run. Each MLflow run is named `llm-eval-{provider}-{model}` from the built agent:

```bash
make docker-up
make evaluate_llms PROVIDER=mistral EXPERIMENT=ecommerce-agent-llm_eval
```

Or from inside Compose (same image, `MLFLOW_TRACKING_URI` already points at the MLflow service):

```bash
docker compose run --rm app uv run --frozen --no-dev python evals/evaluate_llm_response.py \
  --provider mistral --experiment ecommerce-agent-llm_eval
```

MLflow UI: [http://127.0.0.1:5000](http://127.0.0.1:5000). Host evals default to that URI; override with `MLFLOW_TRACKING_URI`.

## LLM API smoke tests

Live pings of each chat and embedding API. They are **not** collected by `uv run pytest` (`testpaths` is `tests/` only). A missing key skips that provider.

```bash
make llm_api_tests
```

Same as `uv run pytest llm-api-tests -v`. One provider:

```bash
uv run pytest llm-api-tests/test_mistral.py -v
```

| File | API |
|---|---|
| `test_mistral.py` | Mistral chat (`MISTRAL_API_KEY`) |
| `test_openai.py` | OpenAI chat + embeddings (`OPENAI_API_KEY`) |
| `test_openrouter.py` | OpenRouter chat (`OPEN_ROUTER_API_KEY`) |
| `test_ollama.py` | Local Ollama (skips if the server is down) |
| `test_gemini.py` | Gemini embeddings (`GEMINI_API_KEY`) |

## Config

See `.env` for secrets (`POSTGRES_*`, `OPENAI_API_KEY`, `OPEN_ROUTER_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, optional `LANGFUSE_BASE_URL`). Start from `.env.example`. Chat and embedding backends are set in `ecommerce_agent/config.py` (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`) and are not read from `.env`. Compose overrides `POSTGRES_HOST=postgres` and `MLFLOW_TRACKING_URI=http://mlflow:5000` for the `app` service.

- `LLM_PROVIDER` — `ollama` | `openrouter` | `openai` | `mistral` (currently `mistral`). `LOCAL_MODEL` is derived (`true` only when the provider is `ollama`).
- `MODEL` — optional env override for the chat model. Defaults: Ollama `qwen2.5:7b`, OpenRouter `nvidia/nemotron-3.5-lightning:free`, OpenAI `gpt-4o-mini`, Mistral `mistral-small`. Provider-specific `OLLAMA_MODEL` / `OPENROUTER_MODEL` / `OPENAI_MODEL` / `MISTRAL_MODEL` still work as fallbacks.
- `OPENAI_API_KEY` / `OPEN_ROUTER_API_KEY` / `MISTRAL_API_KEY` — required for those chat backends. Ollama uses a dummy key.
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — Langfuse tracing for `POST /ask` (OpenAI Agents SDK via OpenInference). Enabled when `LANGFUSE_TRACING` is true in `config.py` and both keys are set. Optional `LANGFUSE_BASE_URL` (EU default `https://cloud.langfuse.com`; US is `https://us.cloud.langfuse.com`). Chat turns send `session_id` so conversations group in Langfuse Sessions and so Postgres can replay history. Agents SDK tracing stays on so tool calls and generations nest under the `ask` span.
- `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` — Grafana at http://localhost:3000. Provisioned dashboard **Ecommerce agent production** shows ask latency, word counts, and thumbs feedback. Prometheus scrapes `GET /metrics`.
- `AGENT_TRACING=true` — OpenAI Agents SDK traces (separate from Langfuse; off by default)
- `EMBEDDING_PROVIDER` — `hf`, `gemini`, or `openai` in `config.py` (currently `gemini`). Needs `GEMINI_API_KEY` or `OPENAI_API_KEY` as required. `EMBEDDING_MODEL` defaults live in `DEFAULT_EMBEDDING_MODELS`: HF `BAAI/bge-m3` (1024-d), Gemini `gemini-embedding-001` (768-d), OpenAI `text-embedding-3-small` (1536-d). `OPENAI_EMBEDDING_MODEL` is still a fallback for OpenAI. A provider/model mismatch raises `ValueError` telling you to check `config.py`. Vector width is fixed when tables are created; do not switch providers without dropping those tables.

Base URLs are constants in `ecommerce_agent/config.py` (`OLLAMA_BASE_URL`, `OPENROUTER_BASE_URL`, `OPENAI_BASE_URL`, `MISTRAL_BASE_URL`, `GEMINI_OPENAI_BASE_URL`) with optional env overrides.

## Layout

Runtime Python lives in `ecommerce_agent/`. The stack is `docker compose up` (`Dockerfile` + `docker-compose.yml`). Unit tests live in `tests/` (`uv run pytest`). Live API pings live in `llm-api-tests/` (`make llm_api_tests`). Eval runbook: `evals/evaluation.md`. As-built diagram: `architecture.md`. Agent workflow (TDD, docs): `AGENTS.md`. Proposal that this tree follows: `architecture_proposal.md`.