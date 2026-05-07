from fastapi import Depends, Request

from app.ai.model_client import ModelClient
from app.ai.model_settings import ModelSettings
from app.services.agent_service import AgentService


def get_model_client(request: Request) -> ModelClient:
    return request.app.state.model_client


def get_model_settings(request: Request) -> ModelSettings:
    return request.app.state.model_settings


def get_agent_service(
    model_client: ModelClient = Depends(get_model_client),
    model_settings: ModelSettings = Depends(get_model_settings),
) -> AgentService:
    return AgentService(model_client, model_settings)
