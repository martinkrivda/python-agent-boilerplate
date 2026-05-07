"""Request-scoped context — backed by ``structlog.contextvars``.

Per-request fields are bound by the ``CorrelationIdMiddleware`` (request_id,
client_ip, method, path) and by the agent route (user_id when present in the
request body). Every log event picks them up automatically through the
``merge_contextvars`` processor.

The ``get_request_id()`` helper is kept as a small read-only convenience for
the response envelope (``ok()`` / ``error_response()``).
"""

from __future__ import annotations

from structlog.contextvars import get_contextvars


def get_request_id() -> str:
    """Return the current request id, or an empty string if not set."""
    value = get_contextvars().get("request_id", "")
    return value if isinstance(value, str) else str(value)
