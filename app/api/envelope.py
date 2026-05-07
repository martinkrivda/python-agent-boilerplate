from __future__ import annotations
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.errors import AppError
from app.core.request_context import get_request_id

T = TypeVar("T")


class ResponseMeta(BaseModel):
    requestId: str
    timestamp: str


class FieldError(BaseModel):
    pointer: str
    message: str
    code: str


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    requestId: str
    errors: list[FieldError] | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ProblemDetails | None
    meta: ResponseMeta


def _meta(request_id: str) -> ResponseMeta:
    return ResponseMeta(
        requestId=request_id,
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def ok(data: Any, status_code: int = 200) -> JSONResponse:
    request_id = get_request_id()
    body = ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={"X-Request-Id": request_id},
    )


def error_response(err: AppError, instance: str, request_id: str) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://httpstatuses.com/{err.status}",
        title=err.title,
        status=err.status,
        detail=err.detail,
        instance=instance,
        code=err.code,
        requestId=request_id,
        errors=None,
    )
    body = ApiResponse(
        success=False,
        data=None,
        error=problem,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=err.status,
        content=body.model_dump(),
        headers={"Cache-Control": "no-store", "X-Request-Id": request_id},
    )


def error_response_with_fields(
    err: AppError,
    fields: list[FieldError],
    instance: str,
    request_id: str,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://httpstatuses.com/{err.status}",
        title=err.title,
        status=err.status,
        detail=err.detail,
        instance=instance,
        code=err.code,
        requestId=request_id,
        errors=fields,
    )
    body = ApiResponse(
        success=False,
        data=None,
        error=problem,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=err.status,
        content=body.model_dump(),
        headers={"Cache-Control": "no-store", "X-Request-Id": request_id},
    )
