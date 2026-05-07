def test_models_current_returns_provider_and_model(client):
    response = client.get("/rest/v1/models/current")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen3:8b"
    assert data["base_url"] == "http://localhost:11434/v1"
    assert isinstance(data["supports_tools"], bool)
    assert isinstance(data["supports_streaming"], bool)


def test_models_current_no_api_key(client):
    response = client.get("/rest/v1/models/current")
    body_str = str(response.json())
    assert "api_key" not in body_str
    assert "AI_API_KEY" not in body_str
