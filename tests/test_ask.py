from unittest.mock import AsyncMock, Mock

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
