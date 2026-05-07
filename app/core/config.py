from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=False)

    app_name: str = "python-agent-boilerplate"
    app_env: str = "development"
    log_level: str = "INFO"

    ai_provider: str = "ollama"
    ai_model: str = "qwen3:8b"
    ai_base_url: str = "http://localhost:11434/v1"
    ai_api_key: str = "ollama"
    ai_request_timeout: int = 60
    ai_supports_tools: bool = False
    ai_supports_structured_output: bool = False
    ai_supports_thinking: bool = False
    ai_supports_streaming: bool = False
    ai_probe_on_ready: bool = False

    openrouter_http_referer: str = ""
    openrouter_title: str = ""

    # Build provenance — baked at Docker build time via ARG → ENV.
    # Empty in local dev (no Docker build args present).
    build_commit: str = ""
    build_timestamp: str = ""
