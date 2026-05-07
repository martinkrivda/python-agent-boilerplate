import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.request_context import get_request_id, reset_request_id, set_request_id

log = structlog.get_logger()

_EXCLUDED_PATHS = {"/metrics", "/doc", "/reference"}


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        except Exception:
            log.error("middleware_exception", request_id=request_id, exc_info=True)
            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "type": "https://httpstatuses.com/500",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "An unexpected error occurred.",
                        "instance": str(request.url.path),
                        "code": "E3001",
                        "requestId": request_id,
                        "errors": None,
                    },
                    "meta": {"requestId": request_id, "timestamp": _utc_now()},
                },
                headers={"Cache-Control": "no-store"},
            )
        finally:
            reset_request_id(token)
        response.headers["X-Request-Id"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=get_request_id(),
        )
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics=None) -> None:
        super().__init__(app)
        from app.core.metrics import get_metrics
        self._metrics = metrics or get_metrics()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        route = _get_route(request)
        method = request.method
        status = str(response.status_code)
        try:
            self._metrics.http_requests_total.labels(
                method=method, route=route, status_code=status
            ).inc()
            self._metrics.http_request_duration_seconds.labels(
                method=method, route=route
            ).observe(duration)
            if response.status_code >= 400:
                self._metrics.http_errors_total.labels(
                    status_code=status, error_code="unknown"
                ).inc()
        except Exception:
            log.error("metrics_middleware_error", exc_info=True)
        return response


def _get_route(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return "unmatched"


def _utc_now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
