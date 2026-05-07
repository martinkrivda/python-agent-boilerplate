"""request_context is now a thin read-only wrapper over structlog.contextvars."""

from __future__ import annotations

import structlog

from app.core.request_context import get_request_id


def test_default_request_id_is_empty():
    structlog.contextvars.clear_contextvars()
    assert get_request_id() == ""


def test_get_request_id_reads_bound_value():
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="abc-123")
    try:
        assert get_request_id() == "abc-123"
    finally:
        structlog.contextvars.clear_contextvars()


def test_get_request_id_after_clear():
    structlog.contextvars.bind_contextvars(request_id="x")
    structlog.contextvars.clear_contextvars()
    assert get_request_id() == ""
