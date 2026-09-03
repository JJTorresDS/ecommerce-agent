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
from pydantic import BaseModel
from agents import Runner, set_tracing_disabled

import csv
import io

from fastapi import FastAPI, File, HTTPException, UploadFile

from embeddings.ingest import upsert_products_batch

from agent import agent

set_tracing_disabled(True)  # no OPENAI_API_KEY needed since we're local-only

app = FastAPI(title="Local Agent API")


class Question(BaseModel):
    question: str


class Answer(BaseModel):
    answer: str


@app.post("/ask", response_model=Answer)
async def ask(payload: Question) -> Answer:
    result = await Runner.run(agent, payload.question)
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

    required = {"sku", "content"}
    missing = required - {h.strip() for h in reader.fieldnames}
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have columns: sku, content. Missing: {sorted(missing)}",
        )

    products = []
    for i, row in enumerate(reader, start=2):  # row 1 is the header
        sku = (row.get("sku") or "").strip()
        content = (row.get("content") or "").strip()
        if not sku or not content:
            raise HTTPException(
                status_code=400,
                detail=f"Row {i}: sku and content are required",
            )
        products.append({"sku": sku, "content": content})

    if not products:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    upsert_products_batch(products)
    return {"upserted": len(products)}