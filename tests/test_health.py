import uuid


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_health_ready(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_health_meta_has_request_id(client):
    response = client.get("/health")
    body = response.json()
    assert "requestId" in body["meta"]
    assert len(body["meta"]["requestId"]) > 0


def test_health_x_request_id_header_matches_meta(client):
    response = client.get("/health")
    body = response.json()
    assert response.headers["x-request-id"] == body["meta"]["requestId"]


def test_health_echoes_provided_request_id(client):
    custom_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-Id": custom_id})
    body = response.json()
    assert body["meta"]["requestId"] == custom_id
    assert response.headers["x-request-id"] == custom_id
