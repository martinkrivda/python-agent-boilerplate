"""Structured logging configuration.

stdlib `logging` provides the actual handlers (console + optional rotating file
with gzip compression and retention). structlog wraps it so every event — from
`structlog.get_logger()` or stdlib `logging.getLogger(...)` — flows through the
same processor pipeline and renders identically.

Static fields (service, env, version, hostname) are added by a processor on
every event. Per-request fields (request_id, client_ip, method, path, user_id)
are managed via `structlog.contextvars` and emitted by `merge_contextvars`.
"""

from __future__ import annotations

import gzip
import logging
import logging.handlers
import os
import shutil
import socket
from pathlib import Path
from typing import Any

import structlog

from app import __version__
from app.core.config import Settings

_HOSTNAME = socket.gethostname()


def _gz_namer(name: str) -> str:
    """Append .gz to the rotated file name (also makes cleanup track .gz files)."""
    return name + ".gz"


def _gz_rotator(source: str, dest: str) -> None:
    """Rotate by gzipping `source` into `dest` and removing the original."""
    with open(source, "rb") as sf, gzip.open(dest, "wb") as df:
        shutil.copyfileobj(sf, df)
    os.remove(source)


def _build_static_processor(settings: Settings):
    """Return a structlog processor that injects per-process static fields."""
    static = {
        "service": settings.app_name,
        "env": settings.app_env,
        "version": __version__,
        "hostname": _HOSTNAME,
    }

    def _add_static(logger: Any, method_name: str, event_dict: dict) -> dict:
        for k, v in static.items():
            event_dict.setdefault(k, v)
        return event_dict

    return _add_static


def _build_renderer(fmt: str):
    if fmt == "console":
        return structlog.dev.ConsoleRenderer(colors=True)
    return structlog.processors.JSONRenderer()


def _build_file_handler(settings: Settings) -> logging.Handler:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_dir / settings.log_file_name),
        when=settings.log_rotation_when,
        backupCount=settings.log_rotation_backup_count,
        encoding="utf-8",
        utc=True,
    )
    handler.namer = _gz_namer
    handler.rotator = _gz_rotator
    return handler


def configure_logging(settings: Settings) -> None:
    """Configure stdlib + structlog. Idempotent — safe to call more than once."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Reset prior handlers so re-configuration (reload, tests) is clean.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(log_level)

    # Pre-chain runs for events from both structlog AND foreign stdlib loggers,
    # so the output shape is identical regardless of source.
    pre_chain: list = [
        structlog.contextvars.merge_contextvars,
        _build_static_processor(settings),
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.stdlib.add_log_level,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=_build_renderer(settings.log_format),
        foreign_pre_chain=pre_chain,
    )

    # Console handler — always present (12-factor / Docker / K8s friendly).
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler — opt-in via LOG_TO_FILE.
    if settings.log_to_file:
        fh = _build_file_handler(settings)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    structlog.configure(
        processors=[
            *pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
