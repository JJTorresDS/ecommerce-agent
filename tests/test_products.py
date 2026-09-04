from ecommerce_agent.api.routes import products as products_route


def test_upload_dummy_products_csv(client, monkeypatch, dummy_products, dummy_products_csv):
    captured = {}

    def fake_upsert(products):
        captured["products"] = products

    monkeypatch.setattr(products_route, "upsert_products_batch", fake_upsert)

    response = client.post(
        "/products/upload",
        files={"file": ("dummy_products.csv", dummy_products_csv, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"upserted": len(dummy_products)}
    assert [p["sku"] for p in captured["products"]] == [
        p["sku"] for p in dummy_products
    ]
    assert captured["products"][0]["description"] == dummy_products[0]["description"]


def test_upload_rejects_non_csv(client):
    response = client.post(
        "/products/upload",
        files={"file": ("products.txt", b"sku,description\nG-001,x\n", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be a .csv"


def test_upload_rejects_missing_description_column(client):
    response = client.post(
        "/products/upload",
        files={"file": ("products.csv", b"sku,content\nG-001,a vest\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "description" in response.json()["detail"]


def test_upload_rejects_empty_rows(client):
    response = client.post(
        "/products/upload",
        files={"file": ("products.csv", b"sku,description\n", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "CSV has no data rows"
