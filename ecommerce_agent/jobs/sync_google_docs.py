"""Re-embed Google Docs when Drive last_modified is newer than our copy."""

from __future__ import annotations

from datetime import datetime, timezone

from googleapiclient.errors import HttpError

from ecommerce_agent.ingest.documents import upsert_document
from ecommerce_agent.integrations.google_docs import get_doc, get_doc_modified_time
from ecommerce_agent.retrieval.documents import list_google_documents


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _needs_refresh(drive_modified: datetime, row: dict) -> bool:
    local = _as_utc(row.get("embedded_at")) or _as_utc(row.get("updated_at"))
    if local is None:
        return True
    return drive_modified > local


def sync_google_docs() -> list[dict]:
    """Refresh ingested Google Docs whose Drive file is newer than our embed."""
    results = []
    for row in list_google_documents():
        document_id = row["document_id"]
        try:
            drive_modified = get_doc_modified_time(document_id)
        except HttpError as exc:
            results.append(
                {
                    "document_id": document_id,
                    "filename": row["filename"],
                    "status": "error",
                    "detail": str(exc),
                }
            )
            continue

        if not _needs_refresh(drive_modified, row):
            results.append(
                {
                    "document_id": document_id,
                    "filename": row["filename"],
                    "status": "unchanged",
                    "drive_modified": drive_modified.isoformat(),
                }
            )
            continue

        title, content = get_doc(document_id)
        if not content.strip():
            results.append(
                {
                    "document_id": document_id,
                    "filename": row["filename"],
                    "status": "skipped",
                    "detail": "Google Doc has no text to embed",
                }
            )
            continue

        upserted = upsert_document(
            filename=title or document_id,
            content=content,
            document_id=document_id,
            summary=row.get("summary"),
        )
        results.append(
            {
                "document_id": document_id,
                "filename": upserted["filename"],
                "status": "reembedded",
                "chunks": upserted["chunks"],
                "drive_modified": drive_modified.isoformat(),
            }
        )
    return results


def main() -> None:
    results = sync_google_docs()
    if not results:
        print("No Google Docs in the knowledge base.")
        return
    for row in results:
        status = row["status"]
        name = row.get("filename") or row["document_id"]
        extra = row.get("detail") or row.get("drive_modified") or ""
        print(f"{status}: {name} {extra}".rstrip())


if __name__ == "__main__":
    main()
