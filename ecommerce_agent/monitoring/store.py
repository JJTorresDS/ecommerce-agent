"""Postgres persistence for production ask turns and user feedback."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine

CREATE_ASK_TURNS_SQL = """
    CREATE TABLE IF NOT EXISTS ask_turns (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        question_words INTEGER NOT NULL,
        answer_words INTEGER NOT NULL,
        latency_ms DOUBLE PRECISION NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    )
"""

CREATE_FEEDBACK_SQL = """
    CREATE TABLE IF NOT EXISTS conversation_feedback (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        turn_id TEXT,
        rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
        created_at TIMESTAMPTZ DEFAULT now()
    )
"""

CREATE_ASK_TURNS_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS ask_turns_created_at_idx
    ON ask_turns (created_at DESC)
"""

CREATE_FEEDBACK_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS conversation_feedback_created_at_idx
    ON conversation_feedback (created_at DESC)
"""


def ensure_monitoring_tables(session: Session | None = None) -> None:
    """Create production monitoring tables if missing. Safe on existing DBs."""
    if session is not None:
        session.execute(text(CREATE_ASK_TURNS_SQL))
        session.execute(text(CREATE_FEEDBACK_SQL))
        session.execute(text(CREATE_ASK_TURNS_INDEX_SQL))
        session.execute(text(CREATE_FEEDBACK_INDEX_SQL))
        return

    with Session(engine) as owned:
        owned.execute(text(CREATE_ASK_TURNS_SQL))
        owned.execute(text(CREATE_FEEDBACK_SQL))
        owned.execute(text(CREATE_ASK_TURNS_INDEX_SQL))
        owned.execute(text(CREATE_FEEDBACK_INDEX_SQL))
        owned.commit()


def persist_ask_turn(
    *,
    session_id: str | None,
    question: str,
    answer: str,
    question_words: int,
    answer_words: int,
    latency_ms: float,
) -> str:
    ensure_monitoring_tables()
    turn_id = str(uuid.uuid4())
    with Session(engine) as session:
        session.execute(
            text("""
                INSERT INTO ask_turns (
                    id, session_id, question, answer,
                    question_words, answer_words, latency_ms
                )
                VALUES (
                    :id, :session_id, :question, :answer,
                    :question_words, :answer_words, :latency_ms
                )
            """),
            {
                "id": turn_id,
                "session_id": session_id,
                "question": question,
                "answer": answer,
                "question_words": question_words,
                "answer_words": answer_words,
                "latency_ms": latency_ms,
            },
        )
        session.commit()
    return turn_id


def persist_feedback(
    *,
    session_id: str,
    rating: str,
    turn_id: str | None = None,
) -> None:
    ensure_monitoring_tables()
    with Session(engine) as session:
        session.execute(
            text("""
                INSERT INTO conversation_feedback (session_id, turn_id, rating)
                VALUES (:session_id, :turn_id, :rating)
            """),
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "rating": rating,
            },
        )
        session.commit()
