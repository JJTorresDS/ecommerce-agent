"""Knowledge-base document writes."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine
from ecommerce_agent.embeddings import get_provider
from ecommerce_agent.ingest.chunking import (
    DEFAULT_CHUNK_CHARS,
    chunk_text,
    parse_structured_document,
)


def upsert_document(
    filename: str,
    content: str,
    document_id: str | None = None,
    summary: str | None = None,
    chunk_chars: int | None = None,
    chunks: list[str] | None = None,
) -> dict:
    """Insert or replace a document and embed its chunks.

    Re-uploading the same `document_id` (or `filename` when no id is
    given) replaces the previous file and its chunks. Pass `document_id`
    to use a stable identifier such as a Google Doc ID. Pass `chunks` to
    skip character-window splitting (used by structured heading ingest).
    """
    provider = get_provider()
    if chunks is None:
        max_chars = chunk_chars or DEFAULT_CHUNK_CHARS
        overlap = max_chars // 2
        chunks = chunk_text(content, max_chars=max_chars, overlap=overlap)
    else:
        max_chars = chunk_chars
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    if not chunks:
        raise ValueError(f"Document '{filename}' has no text to embed")

    vectors = provider.embed(chunks)

    with Session(engine) as session:
        existing_id = None
        if document_id is not None:
            existing_id = session.execute(
                text("SELECT id FROM documents WHERE id = :id"),
                {"id": document_id},
            ).scalar_one_or_none()
        else:
            existing_id = session.execute(
                text("SELECT id FROM documents WHERE filename = :filename"),
                {"filename": filename},
            ).scalar_one_or_none()

        if existing_id is None:
            document_id = document_id or f"file_{uuid.uuid4().hex}"
            session.execute(
                text("""
                    INSERT INTO documents (
                        id, filename, content, summary, has_embedding, updated_at
                    )
                    VALUES (
                        :id, :filename, :content, :summary, FALSE, now()
                    )
                """),
                {
                    "id": document_id,
                    "filename": filename,
                    "content": content,
                    "summary": summary,
                },
            )
        else:
            document_id = existing_id
            session.execute(
                text("""
                    UPDATE documents
                    SET filename = :filename,
                        content = :content,
                        summary = COALESCE(:summary, documents.summary),
                        has_embedding = FALSE,
                        updated_at = now(),
                        embedded_at = NULL
                    WHERE id = :id
                """),
                {
                    "id": document_id,
                    "filename": filename,
                    "content": content,
                    "summary": summary,
                },
            )
            session.execute(
                text("DELETE FROM document_embeddings WHERE document_id = :id"),
                {"id": document_id},
            )

        session.execute(
            text("""
                INSERT INTO document_embeddings (
                    document_id, chunk_index, content, embedding, embedding_model
                )
                VALUES (
                    :document_id, :chunk_index, :content,
                    CAST(:embedding AS vector), :embedding_model
                )
            """),
            [
                {
                    "document_id": document_id,
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": str(vector.tolist()),
                    "embedding_model": provider.model_name,
                }
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ],
        )
        session.execute(
            text("""
                UPDATE documents
                SET has_embedding = TRUE, embedded_at = now()
                WHERE id = :id
            """),
            {"id": document_id},
        )
        stored_summary = session.execute(
            text("SELECT summary FROM documents WHERE id = :id"),
            {"id": document_id},
        ).scalar_one()
        session.commit()

    return {
        "document_id": document_id,
        "filename": filename,
        "summary": stored_summary,
        "chunks": len(chunks),
        "chunk_chars": max_chars,
        "has_embedding": True,
    }


def upsert_documents_structured(
    filename: str,
    content: str,
    summary_tag: str,
    question_tag: str,
    document_id: str | None = None,
    summary: str | None = None,
) -> dict:
    """Insert or replace a heading-structured document (for example a FAQ).

    `summary_tag` and `question_tag` are heading levels such as `h1` /
    `h2`. Text beneath the summary heading is stored on `documents.summary`
    unless `summary` is passed. Each question heading plus the text
    beneath it is embedded as one chunk.
    """
    extracted_summary, chunks = parse_structured_document(
        content,
        summary_tag=summary_tag,
        question_tag=question_tag,
    )
    if not chunks:
        raise ValueError(
            f"Document '{filename}' has no question chunks to embed "
            f"(looking for {question_tag} headings)"
        )
    caller_summary = (summary or "").strip() or None
    return upsert_document(
        filename=filename,
        content=content,
        document_id=document_id,
        summary=caller_summary or extracted_summary,
        chunks=chunks,
    )
