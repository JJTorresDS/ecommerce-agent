from types import SimpleNamespace


def test_init_db_creates_vector_extension_before_tables(monkeypatch):
    from ecommerce_agent.ingest import schema as mod

    executed = []

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return []

        def first(self):
            return None

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement):
            executed.append(statement.text if hasattr(statement, "text") else str(statement))
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(mod, "get_provider", lambda: SimpleNamespace(embedding_dim=768))
    monkeypatch.setattr(mod, "Session", lambda _engine: FakeSession())

    mod.init_db()

    create_ext = next(i for i, sql in enumerate(executed) if "CREATE EXTENSION" in sql.upper())
    create_table = next(i for i, sql in enumerate(executed) if "CREATE TABLE" in sql.upper())
    assert "vector" in executed[create_ext].casefold()
    assert create_ext < create_table
    joined = "\n".join(executed).upper()
    assert "CREATE TABLE IF NOT EXISTS AGENT_SESSIONS" in joined
    assert "CREATE TABLE IF NOT EXISTS AGENT_MESSAGES" in joined
    assert "CREATE TABLE IF NOT EXISTS ASK_TURNS" in joined
    assert "CREATE TABLE IF NOT EXISTS CONVERSATION_FEEDBACK" in joined


def test_init_db_skips_extension_when_tables_already_exist(monkeypatch):
    from ecommerce_agent.ingest import schema as mod

    executed = []

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return ["product_embeddings"]

        def first(self):
            return None

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement):
            executed.append(statement.text if hasattr(statement, "text") else str(statement))
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(mod, "get_provider", lambda: SimpleNamespace(embedding_dim=768))
    monkeypatch.setattr(mod, "Session", lambda _engine: FakeSession())

    try:
        mod.init_db()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError when tables exist")

    assert not any("CREATE EXTENSION" in sql.upper() for sql in executed)
    joined = "\n".join(executed).upper()
    assert "CREATE TABLE IF NOT EXISTS AGENT_SESSIONS" in joined
    assert "CREATE TABLE IF NOT EXISTS AGENT_MESSAGES" in joined
    assert "CREATE TABLE IF NOT EXISTS ASK_TURNS" in joined
    assert "CREATE TABLE IF NOT EXISTS CONVERSATION_FEEDBACK" in joined
    assert not any(
        "CREATE TABLE PRODUCT_EMBEDDINGS" in sql.upper() for sql in executed
    )
