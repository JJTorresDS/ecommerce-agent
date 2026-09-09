def test_chat_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()
    assert "session_id" in response.text
    assert "sessionStorage" in response.text
    assert "/feedback" in response.text
    assert "thumbs-up" in response.text
    assert "thumbs-down" in response.text
    assert "turn_id" in response.text
    assert "Helpful" in response.text
    assert "Not helpful" in response.text
    assert "agent-turn" in response.text
    assert "send(1," in response.text
    assert "send(-1," in response.text
    assert "Feedback failed" in response.text
    assert "Ecommerce Agent" in response.text
    assert "Local Agent" not in response.text


def test_ecommerce_catalog_ui(client):
    response = client.get("/ecommerce")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "KID LOVE VEST" in body
    assert "G-001" in body
