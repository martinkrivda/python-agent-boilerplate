from app.agents.schemas import AgentRunResponse
from app.ai.model_client import ChatMessage, GenerateParams, ModelClient
from app.ai.model_settings import ModelSettings

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024


class AssistantAgent:
    def __init__(
        self,
        model_client: ModelClient,
        model_settings: ModelSettings,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = model_client
        self._settings = model_settings
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def run(self, message: str) -> AgentRunResponse:
        messages = [
            ChatMessage(role="system", content=self._system_prompt),
            ChatMessage(role="user", content=message),
        ]
        params = GenerateParams(temperature=self._temperature, max_tokens=self._max_tokens)
        result = await self._client.generate(messages, params)
        return AgentRunResponse(
            answer=result.content,
            provider=result.provider,
            model=result.model,
            usage=result.usage,
        )
