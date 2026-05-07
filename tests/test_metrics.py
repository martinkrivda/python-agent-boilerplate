def test_metrics_endpoint_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_not_enveloped(client):
    response = client.get("/metrics")
    body = response.text
    assert "success" not in body
    assert "requestId" not in body


def test_metrics_contains_http_requests_total(client):
    client.get("/health")  # generate a counted request
    response = client.get("/metrics")
    assert "http_requests_total" in response.text


def test_metrics_not_counted_in_http_requests_total(client):
    client.get("/metrics")
    response = client.get("/metrics")
    assert 'route="/metrics"' not in response.text
