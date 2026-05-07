from app.ai.model_settings import ModelSettings
from app.core.config import Settings


def test_model_settings_from_settings():
    s = Settings()
    ms = ModelSettings.from_settings(s)
    assert ms.provider == "ollama"
    assert ms.model == "qwen3:8b"
    assert ms.base_url == "http://localhost:11434/v1"
    assert ms.supports_tools is False
    assert ms.supports_structured_output is False
    assert ms.supports_thinking is False
    assert ms.supports_streaming is False


def test_model_settings_no_api_key(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "super-secret")
    s = Settings()
    ms = ModelSettings.from_settings(s)
    assert not hasattr(ms, "api_key")
    assert "super-secret" not in str(ms.model_dump().values())
