import pytest

from app.agents.assistant_agent import AssistantAgent
from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.ai.model_settings import ModelSettings
from app.core.config import Settings


class FakeModelClient(ModelClient):
    def __init__(self, content: str = "fake answer"):
        self._content = content
        self.last_messages: list[ChatMessage] = []
        self.last_params: GenerateParams | None = None

    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        self.last_messages = messages
        self.last_params = params
        return GenerateResult(content=self._content, provider="fake", model="fake-model", usage={})


@pytest.fixture
def model_settings():
    return ModelSettings.from_settings(Settings())


@pytest.mark.asyncio
async def test_assistant_agent_returns_answer(model_settings):
    fake = FakeModelClient("hello from fake")
    agent = AssistantAgent(
        model_client=fake,
        model_settings=model_settings,
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=512,
    )
    result = await agent.run("say hello")
    assert result.answer == "hello from fake"
    assert result.provider == "fake"
    assert result.model == "fake-model"


@pytest.mark.asyncio
async def test_assistant_agent_builds_correct_messages(model_settings):
    fake = FakeModelClient()
    agent = AssistantAgent(
        model_client=fake,
        model_settings=model_settings,
        system_prompt="You are a bot.",
        temperature=0.5,
        max_tokens=256,
    )
    await agent.run("what is 2+2?")
    assert fake.last_messages[0].role == "system"
    assert fake.last_messages[0].content == "You are a bot."
    assert fake.last_messages[1].role == "user"
    assert fake.last_messages[1].content == "what is 2+2?"
    assert fake.last_params.temperature == 0.5
    assert fake.last_params.max_tokens == 256
