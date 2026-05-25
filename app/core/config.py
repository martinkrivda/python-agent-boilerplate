from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=False)

    app_name: str = "python-agent-boilerplate"
    app_env: str = "development"
    log_level: str = "INFO"

    # Logging — stream logging is the production default for Docker/K8s.
    # LOG_TARGET controls where logs are written:
    # "stdout" (Docker/K8s default), "stderr", "file", or "none".
    # File logging needs a writable filesystem, so use it only when LOG_DIR is writable.
    log_target: Literal["stdout", "stderr", "file", "none"] = "stdout"

    # When LOG_TARGET=file: TimedRotatingFileHandler writes to {log_dir}/{log_file_name},
    # rotates by `log_rotation_when` (midnight = daily), gzips rotated files,
    # and keeps the last `log_rotation_backup_count` (default 30 → ~30 days).
    log_dir: str = "logs"
    log_file_name: str = "app.log"
    log_rotation_when: str = "midnight"
    log_rotation_backup_count: int = 30
    log_format: str = "json"  # "json" | "console" (console = pretty for local dev)

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
