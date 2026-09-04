from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

from ecommerce_agent.api.routes import ask as ask_route


def test_ask_with_dummy_product_question(client, monkeypatch, dummy_products):
    vest = next(p for p in dummy_products if p["sku"] == "G-001")
    result = Mock()
    result.final_output = (
        f"{vest['name']} is SKU {vest['sku']} and costs {vest['price']}."
    )
    monkeypatch.setattr(ask_route.Runner, "run", AsyncMock(return_value=result))

    response = client.post(
        "/ask",
        json={"question": f"Do you have the {vest['name']}?"},
    )

    assert response.status_code == 200
    assert response.json() == {"answer": result.final_output}
    ask_route.Runner.run.assert_awaited_once()
    args = ask_route.Runner.run.await_args.args
    assert vest["name"] in args[1]


def test_ask_requires_question(client):
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_accepts_optional_session_id(client, monkeypatch):
    result = Mock()
    result.final_output = "ok"
    monkeypatch.setattr(ask_route.Runner, "run", AsyncMock(return_value=result))

    response = client.post(
        "/ask",
        json={"question": "hello", "session_id": "chat-session-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "ok"}


def test_ask_records_langfuse_span_when_enabled(client, monkeypatch):
    result = Mock()
    result.final_output = "traced answer"
    monkeypatch.setattr(ask_route.Runner, "run", AsyncMock(return_value=result))
    monkeypatch.setattr(
        ask_route,
        "settings",
        SimpleNamespace(
            langfuse_enabled=True,
            llm_provider="openai",
            model="gpt-4o-mini",
        ),
    )
    observation = MagicMock()
    observation.__enter__.return_value = observation
    observation.__exit__.return_value = False
    langfuse = MagicMock()
    langfuse.start_as_current_observation.return_value = observation
    monkeypatch.setattr(ask_route, "get_client", lambda: langfuse)
    monkeypatch.setattr(ask_route, "propagate_attributes", MagicMock())

    response = client.post(
        "/ask",
        json={"question": "How long does shipping take?", "session_id": "s1"},
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "traced answer"}
    langfuse.start_as_current_observation.assert_called_once()
    kwargs = langfuse.start_as_current_observation.call_args.kwargs
    assert kwargs["name"] == "ask"
    assert kwargs["input"] == "How long does shipping take?"
    observation.update.assert_called_once_with(output="traced answer")
