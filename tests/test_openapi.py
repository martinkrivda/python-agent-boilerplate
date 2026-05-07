def test_doc_endpoint_returns_json(client):
    response = client.get("/doc")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert "openapi" in body
    assert "success" not in body


def test_doc_not_enveloped(client):
    response = client.get("/doc")
    body = response.json()
    assert "meta" not in body
    assert "requestId" not in body


def test_metrics_not_enveloped_openapi(client):
    response = client.get("/metrics")
    assert "meta" not in response.text
    assert "requestId" not in response.text
