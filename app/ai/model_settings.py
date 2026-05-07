from __future__ import annotations

from pydantic import BaseModel

from app.core.config import Settings


class ModelSettings(BaseModel):
    provider: str
    model: str
    base_url: str
    supports_tools: bool
    supports_structured_output: bool
    supports_thinking: bool
    supports_streaming: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> ModelSettings:
        return cls(
            provider=settings.ai_provider,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
            supports_tools=settings.ai_supports_tools,
            supports_structured_output=settings.ai_supports_structured_output,
            supports_thinking=settings.ai_supports_thinking,
            supports_streaming=settings.ai_supports_streaming,
        )
