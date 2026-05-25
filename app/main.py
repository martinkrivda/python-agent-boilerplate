from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app import __version__
from app.ai.model_settings import ModelSettings
from app.ai.providers.openai_compatible import OpenAICompatibleModelClient
from app.api.envelope import FieldError, error_response, error_response_with_fields
from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.core.build_info import BuildInfo
from app.core.config import Settings
from app.core.errors import AppError, InternalError, ValidationError
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware, MetricsMiddleware, RequestLoggingMiddleware
from app.core.request_context import get_request_id

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "model_client"):
        settings = Settings()
        configure_logging(settings)
        app.state.model_client = OpenAICompatibleModelClient(settings)
        app.state.model_settings = ModelSettings.from_settings(settings)
        app.state.build_info = BuildInfo.from_settings(settings)
        log.info(
            "startup_complete",
            provider=settings.ai_provider,
            model=settings.ai_model,
            version=__version__,
            commit=app.state.build_info.commit or "unknown",
        )
    yield
    log.info("shutdown")


app = FastAPI(
    title="python-agent-boilerplate",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url="/doc",
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc, instance=str(request.url.path), request_id=get_request_id())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for error in exc.errors():
        loc = error.get("loc", ())
        parts = (
            [str(p) for p in loc[1:]]
            if loc and loc[0] in ("body", "query", "header")
            else [str(p) for p in loc]
        )
        pointer = "/" + "/".join(parts) if parts else "/"
        code = _validation_code(error.get("type", ""))
        fields.append(FieldError(pointer=pointer, message=error.get("msg", ""), code=code))
    err = ValidationError(detail="Request validation failed.")
    return error_response_with_fields(
        err, fields=fields, instance=str(request.url.path), request_id=get_request_id()
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", request_id=get_request_id(), exc_info=True)
    return error_response(
        InternalError(), instance=str(request.url.path), request_id=get_request_id()
    )


def _validation_code(error_type: str) -> str:
    mapping = {
        "missing": "REQUIRED",
        "string_type": "INVALID_TYPE",
        "int_type": "INVALID_TYPE",
        "float_type": "INVALID_TYPE",
        "bool_type": "INVALID_TYPE",
        "string_too_short": "TOO_SHORT",
        "string_too_long": "TOO_LONG",
        "greater_than_equal": "MIN_VALUE",
        "less_than_equal": "MAX_VALUE",
        "extra_forbidden": "EXTRA_FIELD",
    }
    return mapping.get(error_type, "INVALID_FORMAT")


# Middleware (last added = outermost)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Routers
app.include_router(health_router)
app.include_router(agent_router, prefix="/rest/v1")
app.include_router(models_router, prefix="/rest/v1")

# Prometheus ASGI app mounted at /metrics (excluded from envelope and self-instrumentation)
app.mount("/metrics", make_asgi_app())
