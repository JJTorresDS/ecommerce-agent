def test_chat_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_ecommerce_catalog_ui(client):
    response = client.get("/ecommerce")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "KID LOVE VEST" in body
    assert "G-001" in body
