from unittest.mock import AsyncMock, Mock

from ecommerce_agent.api.routes import ask as ask_route


def test_word_count_splits_on_whitespace():
    from ecommerce_agent.monitoring.metrics import word_count

    assert word_count("hello world") == 2
    assert word_count("  one   two three ") == 3
    assert word_count("") == 0


def test_metrics_endpoint_includes_ask_and_feedback_series(client, monkeypatch):
    result = Mock()
    result.final_output = "short answer"
    monkeypatch.setattr(ask_route.Runner, "run", AsyncMock(return_value=result))
    monkeypatch.setattr(
        ask_route,
        "record_ask_turn",
        lambda **kwargs: "turn-metrics",
    )

    ask_response = client.post("/ask", json={"question": "hello there"})
    assert ask_response.status_code == 200

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    for name in (
        "ask_latency_seconds",
        "ask_question_words",
        "ask_answer_words",
        "ask_turns_total",
        "feedback_total",
    ):
        assert name in body
