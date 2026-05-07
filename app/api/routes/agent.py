from fastapi import APIRouter, Depends

from app.agents.schemas import AgentRunRequest
from app.api.dependencies import get_agent_service
from app.api.envelope import ok
from app.services.agent_service import AgentService

router = APIRouter(tags=["agent"])


@router.post("/agent/run", response_model=None)
async def run_agent(
    body: AgentRunRequest,
    service: AgentService = Depends(get_agent_service),
):
    result = await service.run(body)
    return ok(result.model_dump())
