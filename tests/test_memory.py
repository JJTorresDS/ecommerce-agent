import asyncio
import json
from types import SimpleNamespace

from ecommerce_agent.agent import memory as memory_mod


class FakeResult:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class MemoryStore:
    def __init__(self):
        self.sessions: set[str] = set()
        self.messages: list[dict] = []
        self._next_id = 1


class FakeSession:
    def __init__(self, store: MemoryStore):
        self.store = store
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True

    def execute(self, statement, params=None):
        sql = statement.text if hasattr(statement, "text") else str(statement)
        sql_u = " ".join(sql.upper().split())
        params = params or {}
        session_id = params.get("session_id")

        if sql_u.startswith("CREATE TABLE") or sql_u.startswith("CREATE INDEX"):
            return FakeResult()

        if "INSERT INTO AGENT_SESSIONS" in sql_u:
            self.store.sessions.add(session_id)
            return FakeResult()

        if "INSERT INTO AGENT_MESSAGES" in sql_u:
            raw = params.get("message_data")
            self.store.messages.append(
                {
                    "id": self.store._next_id,
                    "session_id": session_id,
                    "message_data": raw,
                }
            )
            self.store._next_id += 1
            return FakeResult()

        if sql_u.startswith("UPDATE AGENT_SESSIONS"):
            return FakeResult()

        if "DELETE FROM AGENT_MESSAGES" in sql_u and "RETURNING" in sql_u:
            matching = [
                row for row in self.store.messages if row["session_id"] == session_id
            ]
            if not matching:
                return FakeResult()
            popped = matching[-1]
            self.store.messages.remove(popped)
            return FakeResult([SimpleNamespace(message_data=popped["message_data"])])

        if "DELETE FROM AGENT_MESSAGES" in sql_u:
            self.store.messages = [
                row for row in self.store.messages if row["session_id"] != session_id
            ]
            return FakeResult()

        if "DELETE FROM AGENT_SESSIONS" in sql_u:
            self.store.sessions.discard(session_id)
            return FakeResult()

        if "SELECT MESSAGE_DATA FROM AGENT_MESSAGES" in sql_u:
            matching = [
                row for row in self.store.messages if row["session_id"] == session_id
            ]
            if "DESC" in sql_u:
                matching = list(reversed(matching))
            limit = params.get("limit")
            if limit is not None:
                matching = matching[: int(limit)]
                if "DESC" in sql_u:
                    matching = list(reversed(matching))
            return FakeResult(
                [SimpleNamespace(message_data=row["message_data"]) for row in matching]
            )

        return FakeResult()


def test_ensure_memory_tables_creates_sessions_and_messages(monkeypatch):
    executed = []

    class RecordingSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement, params=None):
            executed.append(statement.text if hasattr(statement, "text") else str(statement))
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(memory_mod, "Session", lambda _engine: RecordingSession())

    memory_mod.ensure_memory_tables()

    joined = "\n".join(executed).upper()
    assert "CREATE TABLE IF NOT EXISTS AGENT_SESSIONS" in joined
    assert "CREATE TABLE IF NOT EXISTS AGENT_MESSAGES" in joined
    assert "SESSION_ID" in joined
    assert "MESSAGE_DATA" in joined
    assert "CREATE INDEX IF NOT EXISTS" in joined


def test_postgres_session_roundtrip_items(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(memory_mod, "Session", lambda _engine: FakeSession(store))
    monkeypatch.setattr(memory_mod, "ensure_memory_tables", lambda: None)

    session = memory_mod.PostgresSession("chat-1")
    items = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    asyncio.run(session.add_items(items))
    history = asyncio.run(session.get_items())

    assert history == items
    assert "chat-1" in store.sessions


def test_postgres_session_isolates_sessions(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(memory_mod, "Session", lambda _engine: FakeSession(store))
    monkeypatch.setattr(memory_mod, "ensure_memory_tables", lambda: None)

    first = memory_mod.PostgresSession("a")
    second = memory_mod.PostgresSession("b")
    asyncio.run(first.add_items([{"role": "user", "content": "from a"}]))
    asyncio.run(second.add_items([{"role": "user", "content": "from b"}]))

    assert asyncio.run(first.get_items()) == [{"role": "user", "content": "from a"}]
    assert asyncio.run(second.get_items()) == [{"role": "user", "content": "from b"}]


def test_postgres_session_pop_and_clear(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(memory_mod, "Session", lambda _engine: FakeSession(store))
    monkeypatch.setattr(memory_mod, "ensure_memory_tables", lambda: None)

    session = memory_mod.PostgresSession("chat-1")
    asyncio.run(
        session.add_items(
            [
                {"role": "user", "content": "one"},
                {"role": "user", "content": "two"},
            ]
        )
    )

    popped = asyncio.run(session.pop_item())
    assert popped == {"role": "user", "content": "two"}
    assert asyncio.run(session.get_items()) == [{"role": "user", "content": "one"}]

    asyncio.run(session.clear_session())
    assert asyncio.run(session.get_items()) == []
    assert "chat-1" not in store.sessions


def test_postgres_session_decodes_json_strings(monkeypatch):
    store = MemoryStore()
    store.messages.append(
        {
            "id": 1,
            "session_id": "chat-1",
            "message_data": json.dumps({"role": "user", "content": "stored"}),
        }
    )
    monkeypatch.setattr(memory_mod, "Session", lambda _engine: FakeSession(store))
    monkeypatch.setattr(memory_mod, "ensure_memory_tables", lambda: None)

    session = memory_mod.PostgresSession("chat-1")
    assert asyncio.run(session.get_items()) == [{"role": "user", "content": "stored"}]
