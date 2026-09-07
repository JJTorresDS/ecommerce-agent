"""Postgres-backed conversation memory for the Agents SDK Session protocol."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ecommerce_agent.db import engine

CREATE_SESSIONS_SQL = """
    CREATE TABLE IF NOT EXISTS agent_sessions (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
"""

CREATE_MESSAGES_SQL = """
    CREATE TABLE IF NOT EXISTS agent_messages (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL
            REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
        message_data JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    )
"""

CREATE_MESSAGES_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS agent_messages_session_id_idx
    ON agent_messages (session_id, id)
"""


def ensure_memory_tables(session: Session | None = None) -> None:
    """Create conversation tables if they are missing. Safe on existing DBs."""
    if session is not None:
        session.execute(text(CREATE_SESSIONS_SQL))
        session.execute(text(CREATE_MESSAGES_SQL))
        session.execute(text(CREATE_MESSAGES_INDEX_SQL))
        return

    with Session(engine) as owned:
        owned.execute(text(CREATE_SESSIONS_SQL))
        owned.execute(text(CREATE_MESSAGES_SQL))
        owned.execute(text(CREATE_MESSAGES_INDEX_SQL))
        owned.commit()


def _decode_item(message_data: Any) -> dict | None:
    if isinstance(message_data, (bytes, bytearray)):
        message_data = message_data.decode()
    if isinstance(message_data, str):
        try:
            return json.loads(message_data)
        except json.JSONDecodeError:
            return None
    if isinstance(message_data, dict):
        return message_data
    return None


class PostgresSession:
    """Agents SDK Session stored in Postgres, keyed by `session_id`."""

    session_settings = None

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def get_items(self, limit: int | None = None) -> list[dict]:
        ensure_memory_tables()
        with Session(engine) as session:
            if limit is None:
                rows = session.execute(
                    text("""
                        SELECT message_data FROM agent_messages
                        WHERE session_id = :session_id
                        ORDER BY id ASC
                    """),
                    {"session_id": self.session_id},
                ).all()
            else:
                rows = session.execute(
                    text("""
                        SELECT message_data FROM (
                            SELECT message_data, id
                            FROM agent_messages
                            WHERE session_id = :session_id
                            ORDER BY id DESC
                            LIMIT :limit
                        ) AS recent
                        ORDER BY id ASC
                    """),
                    {"session_id": self.session_id, "limit": limit},
                ).all()
        items: list[dict] = []
        for row in rows:
            item = _decode_item(row.message_data)
            if item is not None:
                items.append(item)
        return items

    async def add_items(self, items: list) -> None:
        if not items:
            return
        ensure_memory_tables()
        with Session(engine) as session:
            session.execute(
                text("""
                    INSERT INTO agent_sessions (session_id)
                    VALUES (:session_id)
                    ON CONFLICT (session_id) DO UPDATE
                    SET updated_at = now()
                """),
                {"session_id": self.session_id},
            )
            for item in items:
                session.execute(
                    text("""
                        INSERT INTO agent_messages (session_id, message_data)
                        VALUES (:session_id, CAST(:message_data AS jsonb))
                    """),
                    {
                        "session_id": self.session_id,
                        "message_data": json.dumps(item),
                    },
                )
            session.commit()

    async def pop_item(self) -> dict | None:
        ensure_memory_tables()
        with Session(engine) as session:
            row = session.execute(
                text("""
                    DELETE FROM agent_messages
                    WHERE id = (
                        SELECT id FROM agent_messages
                        WHERE session_id = :session_id
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    RETURNING message_data
                """),
                {"session_id": self.session_id},
            ).first()
            session.commit()
        if row is None:
            return None
        return _decode_item(row.message_data)

    async def clear_session(self) -> None:
        ensure_memory_tables()
        with Session(engine) as session:
            session.execute(
                text("""
                    DELETE FROM agent_messages
                    WHERE session_id = :session_id
                """),
                {"session_id": self.session_id},
            )
            session.execute(
                text("""
                    DELETE FROM agent_sessions
                    WHERE session_id = :session_id
                """),
                {"session_id": self.session_id},
            )
            session.commit()
