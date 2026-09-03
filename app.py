"""
Simple FastAPI endpoint that lets you ask questions to the local Ollama agent
defined in agent.py.

Requirements:
    pip install fastapi uvicorn
    (plus openai-agents, openai already used by agent.py)

Run with:
    uv run uvicorn app:app --reload

Then test with:
    curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
         -d '{"question": "What is the weather in Buenos Aires?"}'

Or open the interactive docs at http://localhost:8000/docs
"""

"""
Simple FastAPI endpoint + minimal HTML UI for the local Ollama agent
defined in agent.py.

Requirements:
    pip install fastapi uvicorn
    (plus openai-agents, openai already used by agent.py)

Run with:
    uv run uvicorn app:app --reload

Then open http://localhost:8000/ in your browser for the UI,
or POST directly to /ask, e.g.:
    curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
         -d '{"question": "What is the weather in Buenos Aires?"}'

Interactive API docs at http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from agents import Runner, set_tracing_disabled

import csv
import io
import os
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from googleapiclient.errors import HttpError

from embeddings.ingest import upsert_document, upsert_products_batch
from google_doc_reader import get_doc

from agent import agent

set_tracing_disabled(True)  # no OPENAI_API_KEY needed since we're local-only

app = FastAPI(title="Local Agent API")


class Question(BaseModel):
    question: str


class Answer(BaseModel):
    answer: str


class GoogleDocIngest(BaseModel):
    document_url: str = Field(
        ...,
        description=(
            "Paste the Google Doc URL from your browser. "
            "You do not need the document ID — the full link is enough. "
            "Example: https://docs.google.com/document/d/<id>/edit"
        ),
        examples=[
            "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        ],
    )
    summary: str | None = Field(
        default=None,
        description="Optional short summary so the agent can decide when to search this document.",
    )
    chunk_chars: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Max characters per chunk. Omit to use OpenAI File Search's default "
            "(800 tokens ≈ 3200 characters, with 50% overlap). "
            "FAQ / short Q&A pages: 1200–1400, so each page stays in one chunk. "
            "Contracts, statutes, or other long-form docs: 3200 is usually fine."
        ),
        examples=[1300, 3200],
    )


@app.post("/ask", response_model=Answer)
async def ask(payload: Question) -> Answer:
    print(f"[agent] called with question: {payload.question!r}", flush=True)
    result = await Runner.run(agent, payload.question)
    print(f"[agent] finished, answer: {result.final_output!r}", flush=True)
    return Answer(answer=result.final_output)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def ui():
    return FileResponse("static/index.html")


@app.get("/ecommerce")
def ecommerce_catalog():
    return FileResponse("static/ecommerce.html")


@app.post("/products/upload")
async def upload_products(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM if Excel added one
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty")

    required = {"sku", "description"}
    missing = required - {h.strip() for h in reader.fieldnames}
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have columns: sku, description. Missing: {sorted(missing)}",
        )

    products = []
    for i, row in enumerate(reader, start=2):  # row 1 is the header
        sku = (row.get("sku") or "").strip()
        description = (row.get("description") or "").strip()
        if not sku or not description:
            raise HTTPException(
                status_code=400,
                detail=f"Row {i}: sku and description are required",
            )
        products.append({"sku": sku, "description": description})

    if not products:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    upsert_products_batch(products)
    return {"upserted": len(products)}


_GDOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")
_GOOGLE_CREDS_PATH = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "secrets/google_service_account.json"
)


def _google_doc_id_from_url(url: str) -> str | None:
    match = _GDOC_ID_RE.search(url.strip())
    if match:
        return match.group(1)
    return None


@app.post(
    "/documents/google-doc",
    summary="Ingest a Google Doc by URL",
    description=(
        "Paste the Google Doc URL from your browser. "
        "You do not need to copy the document ID — the full link is enough. "
        "Share the document with the service account as a Viewer first. "
        "chunk_chars is optional: omit it for OpenAI's 3200-character default, "
        "use 1200–1400 for FAQs, or ~3200 for contracts and legal text."
    ),
)
async def ingest_google_doc(payload: GoogleDocIngest):
    document_id = _google_doc_id_from_url(payload.document_url)
    if not document_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paste the Google Doc URL from your browser, "
                "e.g. https://docs.google.com/document/d/<id>/edit"
            ),
        )

    try:
        title, content = get_doc(document_id, _GOOGLE_CREDS_PATH)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Google service account credentials not found. "
                f"Expected file at '{_GOOGLE_CREDS_PATH}' "
                "(or set GOOGLE_SERVICE_ACCOUNT_FILE)."
            ),
        )
    except HttpError as exc:
        status = int(exc.resp.status)
        if status == 404:
            raise HTTPException(status_code=404, detail="Google Doc not found")
        if status in (401, 403):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Cannot access this Google Doc. Share it with the "
                    "service account as a Viewer."
                ),
            )
        raise HTTPException(
            status_code=502, detail=f"Google Docs API error: {exc}"
        ) from exc

    if not content.strip():
        raise HTTPException(
            status_code=400, detail="Google Doc has no text to embed"
        )

    try:
        result = upsert_document(
            filename=title or document_id,
            content=content,
            document_id=document_id,
            summary=(payload.summary or "").strip() or None,
            chunk_chars=payload.chunk_chars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result