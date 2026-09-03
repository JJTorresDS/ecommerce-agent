"""
Read the text content of a Google Doc using a service account.

Setup:
1. In Google Cloud Console, create (or reuse) a project, enable the
   "Google Docs API", and create a Service Account.
2. Create a JSON key for that service account and download it
   (e.g. save as `service_account.json` in your project).
3. Open the target Google Doc, click "Share", and share it with the
   service account's email address (looks like
   xxxx@xxxx.iam.gserviceaccount.com) — Viewer access is enough.
4. Install dependencies:
   pip install google-api-python-client google-auth --break-system-packages
5. Run:
   python google_doc_reader.py <DOCUMENT_ID> --creds service_account.json

The DOCUMENT_ID is the long string in the doc's URL:
https://docs.google.com/document/d/<DOCUMENT_ID>/edit
"""

import argparse
import json
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


def _build_docs_service(credentials):
    return build("docs", "v1", credentials=credentials)


def get_doc(document_id: str, creds_path: str) -> tuple[str, str]:
    """Fetch a Google Doc and return `(title, plain text)`."""
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return _get_doc_with_credentials(document_id, credentials)


def get_doc_text(document_id: str, creds_path: str) -> str:
    """Fetch a Google Doc and return its plain text content, given a path to a JSON key file."""
    _, text = get_doc(document_id, creds_path)
    return text


def get_doc_text_from_json_string(document_id: str, key_json: str) -> str:
    """Fetch a Google Doc and return its plain text content, given the service
    account key as a raw JSON string (e.g. imported from a secrets .py module)."""
    info = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    _, text = _get_doc_with_credentials(document_id, credentials)
    return text


def _get_doc_with_credentials(document_id: str, credentials) -> tuple[str, str]:
    service = _build_docs_service(credentials)
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


def main():
    parser = argparse.ArgumentParser(description="Read a Google Doc's text content.")
    parser.add_argument("document_id", help="The Google Doc's document ID (from its URL)")
    parser.add_argument(
        "--creds",
        default="service_account.json",
        help="Path to the service account JSON key file (default: service_account.json)",
    )
    args = parser.parse_args()

    try:
        text = get_doc_text(args.document_id, args.creds)
    except FileNotFoundError:
        print(f"Error: credentials file not found at '{args.creds}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading document: {e}", file=sys.stderr)
        sys.exit(1)

    print(text)


if __name__ == "__main__":
    main()