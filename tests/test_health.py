def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_title(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Ecommerce Agent API"
    assert "no-store" in response.headers.get("cache-control", "").lower()


def test_docs_page_title(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Ecommerce Agent API" in response.text
    assert "Local Agent" not in response.text
    assert "no-store" in response.headers.get("cache-control", "").lower()

