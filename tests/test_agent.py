import uuid
from fastapi.testclient import TestClient
from app.api.dependencies import get_model_client
from app.core.errors import ProviderError


def test_agent_run_happy_path(client):
    response = client.post("/rest/v1/agent/run", json={"message": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "fake answer"
    assert body["data"]["provider"] == "fake"
    assert body["error"] is None


def test_agent_run_echoes_request_id(client):
    custom_id = str(uuid.uuid4())
    response = client.post(
        "/rest/v1/agent/run",
        json={"message": "hi"},
        headers={"X-Request-Id": custom_id},
    )
    body = response.json()
    assert body["meta"]["requestId"] == custom_id
    assert response.headers["x-request-id"] == custom_id


def test_agent_run_generates_request_id_when_absent(client):
    response = client.post("/rest/v1/agent/run", json={"message": "hi"})
    body = response.json()
    assert len(body["meta"]["requestId"]) > 0
    assert response.headers.get("x-request-id")


def test_agent_run_missing_message_returns_422(client):
    response = client.post("/rest/v1/agent/run", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E1001"
    assert body["error"]["errors"][0]["pointer"] == "/message"
    assert body["error"]["errors"][0]["code"] == "REQUIRED"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("x-request-id")


def test_agent_run_provider_timeout(app, raises_model_client):
    app.dependency_overrides[get_model_client] = lambda: raises_model_client(ProviderError.timeout())
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/rest/v1/agent/run", json={"message": "hi"})
    assert response.status_code == 504
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E2001"
    assert "stack" not in response.text
    assert "traceback" not in response.text.lower()
    app.dependency_overrides.clear()


def test_agent_run_unhandled_exception(app, raises_model_client):
    app.dependency_overrides[get_model_client] = lambda: raises_model_client(RuntimeError("boom"))
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/rest/v1/agent/run", json={"message": "hi"})
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "E3001"
    app.dependency_overrides.clear()


def test_no_request_id_leakage(client):
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    r1 = client.post("/rest/v1/agent/run", json={"message": "a"}, headers={"X-Request-Id": id1})
    r2 = client.post("/rest/v1/agent/run", json={"message": "b"}, headers={"X-Request-Id": id2})
    assert r1.json()["meta"]["requestId"] == id1
    assert r2.json()["meta"]["requestId"] == id2
    assert id1 not in r2.text
    assert id2 not in r1.text
