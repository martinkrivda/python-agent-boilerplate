from app.agents.assistant_agent import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    AssistantAgent,
)
from app.agents.schemas import AgentRunRequest, AgentRunResponse
from app.ai.model_client import ModelClient
from app.ai.model_settings import ModelSettings


class AgentService:
    def __init__(self, model_client: ModelClient, model_settings: ModelSettings) -> None:
        self._model_client = model_client
        self._model_settings = model_settings

    async def run(self, request: AgentRunRequest) -> AgentRunResponse:
        agent = AssistantAgent(
            model_client=self._model_client,
            model_settings=self._model_settings,
            system_prompt=request.system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=(
                request.temperature if request.temperature is not None else DEFAULT_TEMPERATURE
            ),
            max_tokens=(
                request.max_tokens if request.max_tokens is not None else DEFAULT_MAX_TOKENS
            ),
        )
        return await agent.run(request.message)
