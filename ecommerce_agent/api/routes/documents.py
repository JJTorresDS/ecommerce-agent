from fastapi import APIRouter, HTTPException
from googleapiclient.errors import HttpError

from ecommerce_agent.api.schemas import GoogleDocIngest, GoogleDocStructuredIngest
from ecommerce_agent.config import settings
from ecommerce_agent.ingest.documents import (
    upsert_document,
    upsert_documents_structured,
)
from ecommerce_agent.integrations.google_docs import get_doc, google_doc_id_from_url

router = APIRouter()


def _load_google_doc(document_url: str) -> tuple[str, str, str]:
    """Return `(document_id, title, content)` or raise HTTPException."""
    document_id = google_doc_id_from_url(document_url)
    if not document_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paste the Google Doc URL from your browser, "
                "e.g. https://docs.google.com/document/d/<id>/edit"
            ),
        )

    try:
        title, content = get_doc(document_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Google service account credentials not found. "
                f"Expected file at '{settings.google_service_account_file}' "
                "(or set GOOGLE_SERVICE_ACCOUNT_FILE)."
            ),
        ) from None
    except HttpError as exc:
        status = int(exc.resp.status)
        if status == 404:
            raise HTTPException(status_code=404, detail="Google Doc not found") from exc
        if status in (401, 403):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Cannot access this Google Doc. Share it with the "
                    "service account as a Viewer. Enable the Google Drive "
                    "API if you use the sync job."
                ),
            ) from exc
        raise HTTPException(
            status_code=502, detail=f"Google Docs API error: {exc}"
        ) from exc

    if not content.strip():
        raise HTTPException(
            status_code=400, detail="Google Doc has no text to embed"
        )
    return document_id, title, content


@router.post(
    "/documents/google-doc",
    summary="Ingest a Google Doc by URL (character chunks)",
    description=(
        "Paste the Google Doc URL from your browser. "
        "You do not need to copy the document ID — the full link is enough. "
        "Share the document with the service account as a Viewer first. "
        "chunk_chars is optional: omit it for OpenAI's 3200-character default, "
        "use 1200–1400 for FAQs, or ~3200 for contracts and legal text. "
        "For heading-based FAQ chunking, use POST /documents/google-doc/structured."
    ),
)
async def ingest_google_doc(payload: GoogleDocIngest):
    document_id, title, content = _load_google_doc(payload.document_url)
    try:
        return upsert_document(
            filename=title or document_id,
            content=content,
            document_id=document_id,
            summary=(payload.summary or "").strip() or None,
            chunk_chars=payload.chunk_chars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/documents/google-doc/structured",
    summary="Ingest a Google Doc by heading tags",
    description=(
        "Paste the Google Doc URL from your browser. "
        "summary_tag (for example h1) supplies documents.summary from the "
        "text beneath that heading unless you pass summary. "
        "question_tag (for example h2) embeds each heading plus the text "
        "beneath it as one chunk. Use Heading 1 / Heading 2 styles in the Doc."
    ),
)
async def ingest_structured_google_doc(payload: GoogleDocStructuredIngest):
    document_id, title, content = _load_google_doc(payload.document_url)
    try:
        return upsert_documents_structured(
            filename=title or document_id,
            content=content,
            summary_tag=payload.summary_tag,
            question_tag=payload.question_tag,
            document_id=document_id,
            summary=(payload.summary or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
