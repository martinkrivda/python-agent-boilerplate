from app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.app_name == "python-agent-boilerplate"
    assert s.ai_provider == "ollama"
    assert s.ai_model == "qwen3:8b"
    assert s.ai_base_url == "http://localhost:11434/v1"
    assert s.ai_api_key == "ollama"
    assert s.ai_request_timeout == 60
    assert s.ai_supports_tools is False
    assert s.ai_supports_structured_output is False
    assert s.ai_supports_thinking is False
    assert s.ai_supports_streaming is False
    assert s.ai_probe_on_ready is False
    assert s.log_level == "INFO"
    assert s.log_target == "stdout"
    assert s.app_env == "development"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "gpt-4o")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    s = Settings()
    assert s.ai_model == "gpt-4o"
    assert s.ai_provider == "openai"
