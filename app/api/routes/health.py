from fastapi import APIRouter, Request

from app.api.envelope import ok

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return ok({"status": "ok"})


@router.get("/health/live")
async def health_live():
    return ok({"status": "ok"})


@router.get("/health/ready")
async def health_ready(request: Request):
    client = getattr(request.app.state, "model_client", None)
    settings = getattr(request.app.state, "model_settings", None)
    ready = client is not None and settings is not None
    return ok({"status": "ready" if ready else "not_ready"})
