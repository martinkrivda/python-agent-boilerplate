from fastapi import APIRouter, Depends

from app.ai.model_settings import ModelSettings
from app.api.dependencies import get_model_settings
from app.api.envelope import ok

router = APIRouter(tags=["models"])


@router.get("/models/current", response_model=None)
async def get_current_model(settings: ModelSettings = Depends(get_model_settings)):
    return ok(settings.model_dump())
