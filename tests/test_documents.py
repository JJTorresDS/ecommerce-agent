from unittest.mock import Mock

from googleapiclient.errors import HttpError

from ecommerce_agent.api.routes import documents as documents_route
from tests.conftest import FAQ_DOCUMENT_ID, FAQ_DOCUMENT_URL, FAQ_TEXT, FAQ_TITLE


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
