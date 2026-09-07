from unittest.mock import AsyncMock, Mock

from ecommerce_agent.api.routes import ask as ask_route


def test_ask_returns_turn_id_and_records_production_metrics(client, monkeypatch):
    result = Mock()
    result.final_output = "one two three"
    monkeypatch.setattr(ask_route.Runner, "run", AsyncMock(return_value=result))
    captured = {}

    def fake_record_ask_turn(**kwargs):
        captured.update(kwargs)
        return "turn-123"

    monkeypatch.setattr(ask_route, "record_ask_turn", fake_record_ask_turn)

    response = client.post(
        "/ask",
        json={"question": "hello world", "session_id": "sess-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "one two three"
    assert body["turn_id"] == "turn-123"
    assert captured["session_id"] == "sess-1"
    assert captured["question"] == "hello world"
    assert captured["answer"] == "one two three"
    assert captured["question_words"] == 2
    assert captured["answer_words"] == 3
    assert captured["latency_ms"] >= 0


def test_feedback_thumbs_up(client, monkeypatch):
    from ecommerce_agent.api.routes import feedback as feedback_route

    captured = {}

    def fake_record_feedback(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(feedback_route, "record_feedback", fake_record_feedback)

    response = client.post(
        "/feedback",
        json={"session_id": "sess-1", "turn_id": "turn-123", "rating": "up"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured["session_id"] == "sess-1"
    assert captured["turn_id"] == "turn-123"
    assert captured["rating"] == "up"


def test_feedback_thumbs_down(client, monkeypatch):
    from ecommerce_agent.api.routes import feedback as feedback_route

    monkeypatch.setattr(feedback_route, "record_feedback", lambda **kwargs: None)

    response = client.post(
        "/feedback",
        json={"session_id": "sess-1", "rating": "down"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_feedback_rejects_invalid_rating(client):
    response = client.post(
        "/feedback",
        json={"session_id": "sess-1", "rating": "meh"},
    )
    assert response.status_code == 422


def test_feedback_requires_session_id(client):
    response = client.post("/feedback", json={"rating": "up"})
    assert response.status_code == 422
