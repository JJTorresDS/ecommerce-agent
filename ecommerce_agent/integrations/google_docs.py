"""Read Google Doc title/text and Drive modifiedTime via a service account."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ecommerce_agent.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
_GDOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def google_doc_id_from_url(url: str) -> str | None:
    match = _GDOC_ID_RE.search(url.strip())
    if match:
        return match.group(1)
    return None


def _credentials(creds_path: str | None = None):
    path = creds_path or settings.google_service_account_file
    return service_account.Credentials.from_service_account_file(
        path, scopes=SCOPES
    )


def get_doc(document_id: str, creds_path: str | None = None) -> tuple[str, str]:
    """Fetch a Google Doc and return `(title, plain text)`."""
    credentials = _credentials(creds_path)
    service = build("docs", "v1", credentials=credentials)
    doc = service.documents().get(documentId=document_id).execute()

    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for run in paragraph.get("elements", []):
            text_run = run.get("textRun")
            if text_run and "content" in text_run:
                text_parts.append(text_run["content"])

    title = (doc.get("title") or "").strip()
    return title, "".join(text_parts)


def get_doc_text(document_id: str, creds_path: str | None = None) -> str:
    """Fetch a Google Doc and return its plain text content."""
    _, text = get_doc(document_id, creds_path)
    return text


def get_doc_text_from_json_string(document_id: str, key_json: str) -> str:
    info = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    service = build("docs", "v1", credentials=credentials)
    doc = service.documents().get(documentId=document_id).execute()
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for run in paragraph.get("elements", []):
            text_run = run.get("textRun")
            if text_run and "content" in text_run:
                text_parts.append(text_run["content"])
    return "".join(text_parts)


def get_doc_modified_time(
    document_id: str, creds_path: str | None = None
) -> datetime:
    """Return Drive `modifiedTime` as an aware UTC datetime."""
    credentials = _credentials(creds_path)
    drive = build("drive", "v3", credentials=credentials)
    meta = (
        drive.files()
        .get(fileId=document_id, fields="modifiedTime")
        .execute()
    )
    raw = meta["modifiedTime"]
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read a Google Doc's text content.")
    parser.add_argument("document_id", help="The Google Doc's document ID (from its URL)")
    parser.add_argument(
        "--creds",
        default=None,
        help="Path to the service account JSON key file",
    )
    args = parser.parse_args()

    try:
        text = get_doc_text(args.document_id, args.creds)
    except FileNotFoundError:
        path = args.creds or settings.google_service_account_file
        print(f"Error: credentials file not found at '{path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading document: {e}", file=sys.stderr)
        sys.exit(1)

    print(text)


if __name__ == "__main__":
    main()
