# Application architecture

As-built. Runtime Python is the `ecommerce_agent` package. Root shims (`app.py`, `agent.py`, `tools.py`, `vector_store.py`, `google_doc_reader.py`, `embeddings/`, `init/`) are gone.

```bash
uv run uvicorn ecommerce_agent.api.app:app --reload
```

## Layout

```text
ecommerce-agent/
├── ecommerce_agent/
│   ├── config.py                 # env: DB, LLM, embeddings, Google, tracing
│   ├── db.py                     # one SQLAlchemy engine
│   ├── api/
│   │   ├── app.py                # FastAPI factory
│   │   ├── schemas.py
│   │   └── routes/               # ask, products, documents, health
│   ├── agent/                    # llm, instructions.md, hooks, factory
│   ├── tools/                    # catalog.py, knowledge.py
│   ├── retrieval/                # read-only products + documents
│   ├── ingest/                   # chunking, product/document writes, schema
│   ├── embeddings/               # lazy HF | Gemini
│   ├── integrations/google_docs.py
│   └── jobs/sync_google_docs.py
├── static/                       # chat + catalog HTML
├── db/                           # init_vector_db.sql, seed, download_model
├── notebooks/
├── tests/
├── AGENTS.md                     # TDD + keep README and architecture.md current
└── secrets/                      # gitignored service account
```

## System overview

```mermaid
flowchart TB
    subgraph Clients
        ChatUI["Chat UI<br/>GET /"]
        CatalogUI["Catalog UI<br/>GET /ecommerce"]
        OpenAPI["OpenAPI / curl<br/>GET /docs"]
    end

    subgraph API["ecommerce_agent.api"]
        Ask["POST /ask"]
        Upload["POST /products/upload"]
        GDocEP["POST /documents/google-doc"]
        Health["GET /health"]
    end

    subgraph AgentPkg["ecommerce_agent.agent"]
        Factory["factory.agent"]
        LLM["llm: Ollama | OpenRouter"]
        Trace["AGENT_TRACING"]
    end

    subgraph ToolsPkg["ecommerce_agent.tools"]
        TList["list_knowledgebase_documents"]
        TFaq["search_faq_knowledgebase"]
        TSearch["search_products"]
        TSku["get_item_details"]
    end

    subgraph Retrieval["retrieval — read only"]
        RProd["products.search / get_by_sku"]
        RDocs["documents.list / search"]
    end

    subgraph IngestPkg["ingest — write only"]
        ParseCSV["parse_products_csv"]
        IProd["products.upsert"]
        IDocs["documents.upsert"]
        Chunk["chunking"]
    end

    subgraph Integrations["integrations.google_docs"]
        Fetch["title + text"]
        Drive["Drive modifiedTime"]
    end

    Job["jobs.sync_google_docs"]
    Config["config.settings"]
    Engine["db.engine"]
    Embed["embeddings.get_provider<br/>lazy HF | Gemini"]
    PG["PostgreSQL + pgvector"]

    ChatUI --> Ask
    CatalogUI --> Upload
    OpenAPI --> Ask & Upload & GDocEP & Health

    Ask --> Factory
    Factory --> LLM
    Factory --> Trace
    Factory --> TList & TFaq & TSearch & TSku

    TList --> RDocs
    TFaq --> RDocs
    TSearch --> RProd
    TSku --> RProd

    Upload --> ParseCSV --> IProd
    GDocEP --> Fetch --> IDocs
    IDocs --> Chunk
    Job --> Drive
    Job --> Fetch
    Job --> IDocs

    RProd & RDocs & IProd & IDocs --> Embed
    RProd & RDocs & IProd & IDocs --> Engine --> PG
    Factory & Fetch & Embed --> Config
```

## Layer rules

- **api** calls the agent factory or ingest. It does not run SQL or embedding math.
- **tools** call retrieval only. Tools never ingest.
- **retrieval** is SELECT + cosine search.
- **ingest** is the only writer of embeddings.
- **jobs** reuse ingest + integrations. Not a second write path.
- **config.py** is the only module that reads environment variables.

## Ask flow

For FAQ / support, the agent lists document summaries first, then searches with that `document_id`. It must not invent contact details or policies. `search_faq_knowledgebase` requires `document_id` unless exactly one document exists.

```mermaid
sequenceDiagram
    actor User
    participant UI as Chat UI
    participant Ask as POST /ask
    participant Agent as agent.factory
    participant LLM as Ollama or OpenRouter
    participant Tools as tools
    participant Retrieval as retrieval
    participant DB as pgvector

    User->>UI: question
    UI->>Ask: JSON
    Ask->>Agent: Runner.run

    loop until final answer
        Agent->>LLM: messages + tool schemas
        alt knowledge base
            LLM->>Tools: list_knowledgebase_documents
            Tools->>Retrieval: list_documents
            Retrieval->>DB: id, filename, summary
            LLM->>Tools: search_faq_knowledgebase query + document_id
            Tools->>Retrieval: search_documents
            Retrieval->>DB: embedding <=> query
        else catalog
            LLM->>Tools: search_products / get_item_details
            Tools->>Retrieval: search / get_by_sku
            Retrieval->>DB: product_embeddings
        else done
            LLM-->>Agent: final_output
        end
    end

    Agent-->>Ask: answer
    Ask-->>User: JSON / chat bubble
```

## Ingest and sync

Google Doc **id** is `documents.id`. The Doc **title** is `filename`. Optional `summary` is what the LLM reads before searching. Optional `chunk_chars`: omit for OpenAI File Search default (3200 chars, 50% overlap); FAQ pages 1200–1400; contracts ~3200.

```mermaid
flowchart LR
    subgraph Catalog["Product catalog"]
        CSV["CSV sku, description"]
        Seed["db/seed_products.py"]
        UP["POST /products/upload"]
        Batch["ingest.products"]
        PE["product_embeddings"]
    end

    subgraph KB["Knowledge base"]
        URL["Google Doc URL"]
        GD["POST /documents/google-doc"]
        GDocs["Docs API + Drive"]
        UD["ingest.documents"]
        DT["documents"]
        DE["document_embeddings"]
        Cron["python -m ecommerce_agent.jobs.sync_google_docs"]
    end

    CSV --> UP --> Batch
    Seed --> Batch
    Batch --> PE

    URL --> GD --> GDocs --> UD
    Cron -->|"re-embed if Drive newer than updated_at / embedded_at"| GDocs
    UD --> DT
    UD --> DE
```

The sync job skips ids that start with `file_`. It does not `ALTER` tables.

## Data model and indexes

New databases (`db/init_vector_db.sql` and `ingest.schema.init_db`) use **HNSW**. Existing databases that still have IVFFlat `lists = 100` keep working because retrieval sets `ivfflat.probes = 100` per query. No live `ALTER`.

`embedding VECTOR(...)` width is fixed at `CREATE`. Python `init_db()` uses `provider.embedding_dim` (`hf` / bge-m3: 1024; `gemini`: 768). `db/init_vector_db.sql` is hardcoded `VECTOR(1024)` for HF. Gemini's API returns 3072-d vectors; `GeminiEmbeddingProvider` requests `dimensions=768` and, if the API still returns 3072, truncates and L2-normalizes (Matryoshka). Switching providers after tables exist requires dropping `product_embeddings`, `document_embeddings`, and `documents`.

```mermaid
erDiagram
    product_embeddings {
        serial id PK
        text sku UK
        text name
        text price
        text description
        text content
        vector embedding
        text embedding_model
    }

    documents {
        text id PK
        text filename UK
        text content
        text summary
        boolean has_embedding
        timestamptz updated_at
        timestamptz embedded_at
    }

    document_embeddings {
        serial id PK
        text document_id FK
        int chunk_index
        text content
        vector embedding
        text embedding_model
    }

    documents ||--o{ document_embeddings : chunks
```

## Config

`ecommerce_agent.config.settings` (from `.env`):

| Variable | Role |
|---|---|
| `POSTGRES_*` | Database URL |
| `LOCAL_MODEL` | `true` → Ollama, else OpenRouter |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | Local model |
| `OPEN_ROUTER_API_KEY` / `OPENROUTER_MODEL` | Hosted model |
| `EMBEDDING_PROVIDER` | `hf` (default, 1024-d) or `gemini` (`GEMINI_API_KEY`, stored as 768-d) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Defaults to `secrets/google_service_account.json` |
| `AGENT_TRACING` | `true` enables Agents SDK traces |

The Hugging Face model loads on first `get_provider()` call, not at process import. `/health` does not embed.
