def test_ensure_monitoring_tables_recreates_text_rating(monkeypatch):
    from ecommerce_agent.monitoring import store as mod

    executed = []

    class FakeResult:
        def first(self):
            return ("text",)

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement, params=None):
            executed.append(statement.text if hasattr(statement, "text") else str(statement))
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(mod, "Session", lambda _engine: FakeSession())
    mod.ensure_monitoring_tables()
    joined = "\n".join(executed).upper()
    assert "DROP TABLE IF EXISTS CONVERSATION_FEEDBACK" in joined
    assert "CREATE TABLE IF NOT EXISTS CONVERSATION_FEEDBACK" in joined
    assert "RATING INTEGER" in joined


def test_ensure_monitoring_tables_keeps_integer_rating(monkeypatch):
    from ecommerce_agent.monitoring import store as mod

    executed = []

    class FakeResult:
        def first(self):
            return ("integer",)

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement, params=None):
            executed.append(statement.text if hasattr(statement, "text") else str(statement))
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(mod, "Session", lambda _engine: FakeSession())
    mod.ensure_monitoring_tables()
    joined = "\n".join(executed).upper()
    assert "DROP TABLE" not in joined
    assert "CREATE TABLE IF NOT EXISTS CONVERSATION_FEEDBACK" in joined
