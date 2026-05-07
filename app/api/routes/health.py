from fastapi import APIRouter, Request

from app import __version__
from app.api.envelope import ok

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    data: dict = {"status": "ok", "version": __version__}
    build = getattr(request.app.state, "build_info", None)
    if build is not None:
        if build.commit:
            data["commit"] = build.commit
        if build.timestamp:
            data["built_at"] = build.timestamp
    return ok(data)


@router.get("/health/live")
async def health_live():
    return ok({"status": "ok"})


@router.get("/health/ready")
async def health_ready(request: Request):
    client = getattr(request.app.state, "model_client", None)
    settings = getattr(request.app.state, "model_settings", None)
    ready = client is not None and settings is not None
    return ok({"status": "ready" if ready else "not_ready"})
