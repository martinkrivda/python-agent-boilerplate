import openai
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prometheus_client import CollectorRegistry

from app.ai.model_client import ChatMessage, GenerateParams
from app.ai.providers.openai_compatible import OpenAICompatibleModelClient
from app.core.config import Settings
from app.core.errors import ProviderError
from app.core.metrics import make_metrics


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")
    return Settings()


@pytest.fixture
def metrics():
    return make_metrics(registry=CollectorRegistry())


def _make_completion(content: str):
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    completion.model = "qwen3:8b"
    completion.usage = None
    return completion


@pytest.mark.asyncio
async def test_generate_returns_result(settings, metrics):
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    completion = _make_completion("hello world")
    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=completion)):
        result = await client.generate(
            [ChatMessage(role="user", content="hi")],
            GenerateParams(),
        )
    assert result.content == "hello world"
    assert result.provider == "ollama"
    assert result.model == "qwen3:8b"


@pytest.mark.asyncio
async def test_generate_timeout_raises_provider_error(settings, metrics):
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    with patch.object(
        client._client.chat.completions, "create",
        new=AsyncMock(side_effect=openai.APITimeoutError(request=MagicMock()))
    ):
        with pytest.raises(ProviderError) as exc_info:
            await client.generate([ChatMessage(role="user", content="hi")], GenerateParams())
    assert exc_info.value.code == "E2001"


@pytest.mark.asyncio
async def test_generate_auth_raises_provider_error(settings, metrics):
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    with patch.object(
        client._client.chat.completions, "create",
        new=AsyncMock(side_effect=openai.AuthenticationError(
            message="unauthorized", response=MagicMock(), body={}
        ))
    ):
        with pytest.raises(ProviderError) as exc_info:
            await client.generate([ChatMessage(role="user", content="hi")], GenerateParams())
    assert exc_info.value.code == "E2002"
