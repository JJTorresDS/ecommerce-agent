from fastapi import APIRouter, HTTPException
from googleapiclient.errors import HttpError

from ecommerce_agent.api.schemas import GoogleDocIngest
from ecommerce_agent.config import settings
from ecommerce_agent.ingest.documents import upsert_document
from ecommerce_agent.integrations.google_docs import get_doc, google_doc_id_from_url

router = APIRouter()


@router.post(
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
    document_id = google_doc_id_from_url(payload.document_url)
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
