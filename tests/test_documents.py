from unittest.mock import Mock

from googleapiclient.errors import HttpError
import pytest

from ecommerce_agent.api.routes import documents as documents_route
from ecommerce_agent.ingest.chunking import parse_structured_document
from ecommerce_agent.ingest.documents import upsert_documents_structured
from tests.conftest import (
    FAQ_DOCUMENT_ID,
    FAQ_DOCUMENT_URL,
    FAQ_STRUCTURED_TEXT,
    FAQ_TEXT,
    FAQ_TITLE,
)


def test_ingest_example_google_doc(client, monkeypatch):
    monkeypatch.setattr(
        documents_route,
        "get_doc",
        lambda document_id: (FAQ_TITLE, FAQ_TEXT),
    )

    captured = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return {
            "document_id": kwargs["document_id"],
            "filename": kwargs["filename"],
            "summary": kwargs["summary"],
            "chunks": 1,
            "chunk_chars": kwargs["chunk_chars"] or 3200,
            "has_embedding": True,
        }

    monkeypatch.setattr(documents_route, "upsert_document", fake_upsert)

    response = client.post(
        "/documents/google-doc",
        json={
            "document_url": FAQ_DOCUMENT_URL,
            "summary": "FAQ covering shipping, returns, and customer support",
            "chunk_chars": 1300,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == FAQ_DOCUMENT_ID
    assert body["filename"] == FAQ_TITLE
    assert body["chunk_chars"] == 1300
    assert body["has_embedding"] is True
    assert captured["document_id"] == FAQ_DOCUMENT_ID
    assert captured["content"] == FAQ_TEXT
    assert captured["chunk_chars"] == 1300


def test_ingest_google_doc_rejects_non_docs_url(client):
    response = client.post(
        "/documents/google-doc",
        json={"document_url": "https://example.com/not-a-doc"},
    )
    assert response.status_code == 400
    assert "Google Doc URL" in response.json()["detail"]


def test_ingest_google_doc_not_found(client, monkeypatch):
    resp = Mock()
    resp.status = 404
    monkeypatch.setattr(
        documents_route,
        "get_doc",
        Mock(side_effect=HttpError(resp=resp, content=b"not found")),
    )

    response = client.post(
        "/documents/google-doc",
        json={"document_url": FAQ_DOCUMENT_URL},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Google Doc not found"


def test_ingest_google_doc_empty_text(client, monkeypatch):
    monkeypatch.setattr(
        documents_route,
        "get_doc",
        lambda document_id: (FAQ_TITLE, "   "),
    )

    response = client.post(
        "/documents/google-doc",
        json={"document_url": FAQ_DOCUMENT_URL},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Google Doc has no text to embed"


def test_ingest_structured_google_doc(client, monkeypatch):
    monkeypatch.setattr(
        documents_route,
        "get_doc",
        lambda document_id: (FAQ_TITLE, FAQ_STRUCTURED_TEXT),
    )

    captured = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return {
            "document_id": kwargs["document_id"],
            "filename": kwargs["filename"],
            "summary": kwargs.get("summary"),
            "chunks": 3,
            "has_embedding": True,
        }

    monkeypatch.setattr(
        documents_route, "upsert_documents_structured", fake_upsert
    )

    response = client.post(
        "/documents/google-doc/structured",
        json={
            "document_url": FAQ_DOCUMENT_URL,
            "summary_tag": "h1",
            "question_tag": "h2",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == FAQ_DOCUMENT_ID
    assert body["filename"] == FAQ_TITLE
    assert body["chunks"] == 3
    assert captured["document_id"] == FAQ_DOCUMENT_ID
    assert captured["content"] == FAQ_STRUCTURED_TEXT
    assert captured["summary_tag"] == "h1"
    assert captured["question_tag"] == "h2"
    assert captured["summary"] is None


def test_ingest_structured_google_doc_keeps_caller_summary(client, monkeypatch):
    monkeypatch.setattr(
        documents_route,
        "get_doc",
        lambda document_id: (FAQ_TITLE, FAQ_STRUCTURED_TEXT),
    )

    captured = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return {
            "document_id": kwargs["document_id"],
            "filename": kwargs["filename"],
            "summary": kwargs["summary"],
            "chunks": 3,
            "has_embedding": True,
        }

    monkeypatch.setattr(
        documents_route, "upsert_documents_structured", fake_upsert
    )

    response = client.post(
        "/documents/google-doc/structured",
        json={
            "document_url": FAQ_DOCUMENT_URL,
            "summary_tag": "h1",
            "question_tag": "h2",
            "summary": "Caller-provided summary",
        },
    )

    assert response.status_code == 200
    assert captured["summary"] == "Caller-provided summary"


def test_ingest_structured_google_doc_rejects_non_docs_url(client):
    response = client.post(
        "/documents/google-doc/structured",
        json={
            "document_url": "https://example.com/not-a-doc",
            "summary_tag": "h1",
            "question_tag": "h2",
        },
    )
    assert response.status_code == 400
    assert "Google Doc URL" in response.json()["detail"]


def test_parse_structured_document_uses_h1_body_as_summary():
    summary, chunks = parse_structured_document(
        FAQ_STRUCTURED_TEXT,
        summary_tag="h1",
        question_tag="h2",
    )

    assert summary == "FAQ covering shipping, returns, and customer support."
    assert chunks == [
        (
            "## How do I contact customer service?\n"
            "Chat with us here, email support@jonas-demo.com, or call."
        ),
        "## Do you accept credit cards\nYes",
        "## Are you opened on holidays\nLoremp ipsum",
    ]


def test_upsert_documents_structured_embeds_h2_chunks_and_h1_summary(monkeypatch):
    captured = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return {
            "document_id": kwargs["document_id"],
            "filename": kwargs["filename"],
            "summary": kwargs["summary"],
            "chunks": len(kwargs["chunks"]),
            "has_embedding": True,
        }

    monkeypatch.setattr(
        "ecommerce_agent.ingest.documents.upsert_document",
        fake_upsert,
    )

    result = upsert_documents_structured(
        filename=FAQ_TITLE,
        content=FAQ_STRUCTURED_TEXT,
        summary_tag="h1",
        question_tag="h2",
        document_id=FAQ_DOCUMENT_ID,
    )

    assert captured["document_id"] == FAQ_DOCUMENT_ID
    assert captured["filename"] == FAQ_TITLE
    assert captured["content"] == FAQ_STRUCTURED_TEXT
    assert captured["summary"] == (
        "FAQ covering shipping, returns, and customer support."
    )
    assert captured["chunks"] == [
        (
            "## How do I contact customer service?\n"
            "Chat with us here, email support@jonas-demo.com, or call."
        ),
        "## Do you accept credit cards\nYes",
        "## Are you opened on holidays\nLoremp ipsum",
    ]
    assert result["chunks"] == 3
    assert result["summary"] == captured["summary"]


def test_upsert_documents_structured_keeps_caller_summary(monkeypatch):
    captured = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return {
            "document_id": kwargs.get("document_id"),
            "filename": kwargs["filename"],
            "summary": kwargs["summary"],
            "chunks": len(kwargs["chunks"]),
            "has_embedding": True,
        }

    monkeypatch.setattr(
        "ecommerce_agent.ingest.documents.upsert_document",
        fake_upsert,
    )

    upsert_documents_structured(
        filename=FAQ_TITLE,
        content=FAQ_STRUCTURED_TEXT,
        summary_tag="h1",
        question_tag="h2",
        summary="Caller-provided summary",
    )

    assert captured["summary"] == "Caller-provided summary"


def test_upsert_documents_structured_requires_question_chunks():
    with pytest.raises(ValueError, match="no question"):
        upsert_documents_structured(
            filename=FAQ_TITLE,
            content="# Frequently Asked Questions\nOnly a summary, no questions.\n",
            summary_tag="h1",
            question_tag="h2",
        )


def test_google_doc_body_emits_markdown_headings():
    from ecommerce_agent.integrations.google_docs import doc_body_to_text

    body = {
        "content": [
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "elements": [
                        {"textRun": {"content": "Frequently Asked Questions\n"}}
                    ],
                }
            },
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    "elements": [
                        {
                            "textRun": {
                                "content": (
                                    "FAQ covering shipping, returns, "
                                    "and customer support.\n"
                                )
                            }
                        }
                    ],
                }
            },
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "HEADING_2"},
                    "elements": [
                        {"textRun": {"content": "Do you accept credit cards\n"}}
                    ],
                }
            },
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    "elements": [{"textRun": {"content": "Yes\n"}}],
                }
            },
        ]
    }

    text = doc_body_to_text(body)
    summary, chunks = parse_structured_document(
        text, summary_tag="h1", question_tag="h2"
    )
    assert summary == "FAQ covering shipping, returns, and customer support."
    assert chunks == ["## Do you accept credit cards\nYes"]
