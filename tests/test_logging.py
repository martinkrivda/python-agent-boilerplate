"""Tests for the structlog + stdlib file-logging pipeline."""

from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path

import pytest
import structlog

from app import __version__
from app.core.config import Settings
from app.core.logging import configure_logging


@pytest.fixture(autouse=True)
def _isolated_logging():
    """Reset stdlib + structlog state around every test in this module."""
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)


def _settings(tmp_path: Path, **overrides) -> Settings:
    base = {
        "log_to_file": True,
        "log_dir": str(tmp_path),
        "log_file_name": "app.log",
        "log_format": "json",
        "log_rotation_backup_count": 3,
    }
    base.update(overrides)
    return Settings(**base)


def _read_log_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_file_logging_writes_to_log_dir(tmp_path: Path):
    s = _settings(tmp_path)
    configure_logging(s)

    log = structlog.get_logger("test")
    log.info("hello", extra_field="x")

    log_file = tmp_path / "app.log"
    assert log_file.exists()
    lines = _read_log_lines(log_file)
    assert len(lines) == 1
    assert lines[0]["event"] == "hello"
    assert lines[0]["extra_field"] == "x"


def test_log_lines_include_static_fields(tmp_path: Path):
    s = _settings(tmp_path)
    configure_logging(s)

    structlog.get_logger("test").info("ping")
    line = _read_log_lines(tmp_path / "app.log")[0]

    assert line["service"] == "python-agent-boilerplate"
    assert line["env"] == "development"
    assert line["version"] == __version__
    assert line["hostname"]  # whatever socket.gethostname() returns
    assert line["timestamp"]  # ISO 8601 timestamp
    assert line["level"] == "info"


def test_log_lines_include_contextvars(tmp_path: Path):
    s = _settings(tmp_path)
    configure_logging(s)

    structlog.contextvars.bind_contextvars(
        request_id="r-1",
        client_ip="10.0.0.1",
        user_id="alice",
    )
    structlog.get_logger("test").info("event_in_request")
    line = _read_log_lines(tmp_path / "app.log")[0]

    assert line["request_id"] == "r-1"
    assert line["client_ip"] == "10.0.0.1"
    assert line["user_id"] == "alice"


def test_log_lines_omit_contextvars_after_clear(tmp_path: Path):
    s = _settings(tmp_path)
    configure_logging(s)

    structlog.contextvars.bind_contextvars(request_id="r-1")
    structlog.get_logger("test").info("first")
    structlog.contextvars.clear_contextvars()
    structlog.get_logger("test").info("second")

    lines = _read_log_lines(tmp_path / "app.log")
    assert lines[0].get("request_id") == "r-1"
    assert "request_id" not in lines[1]


def test_file_logging_can_be_disabled(tmp_path: Path):
    s = _settings(tmp_path, log_to_file=False)
    configure_logging(s)
    structlog.get_logger("test").info("only_console")
    assert not (tmp_path / "app.log").exists()


def test_rotation_produces_gzipped_backup(tmp_path: Path):
    s = _settings(tmp_path)
    configure_logging(s)

    structlog.get_logger("test").info("before_rotation")

    # Force a rotation now (without waiting for midnight).
    file_handler = next(
        h
        for h in logging.getLogger().handlers
        if h.__class__.__name__ == "TimedRotatingFileHandler"
    )
    file_handler.doRollover()

    structlog.get_logger("test").info("after_rotation")

    # Active file holds only the post-rotation line.
    active = _read_log_lines(tmp_path / "app.log")
    assert len(active) == 1
    assert active[0]["event"] == "after_rotation"

    # The rotated backup is gzipped and contains the pre-rotation line.
    rotated = list(tmp_path.glob("app.log.*.gz"))
    assert len(rotated) == 1
    with gzip.open(rotated[0], "rt") as fh:
        rotated_lines = [json.loads(line) for line in fh.read().splitlines() if line.strip()]
    assert rotated_lines[0]["event"] == "before_rotation"


def test_retention_caps_backup_count(tmp_path: Path):
    s = _settings(tmp_path, log_rotation_backup_count=2)
    configure_logging(s)

    file_handler = next(
        h
        for h in logging.getLogger().handlers
        if h.__class__.__name__ == "TimedRotatingFileHandler"
    )
    log = structlog.get_logger("test")
    for i in range(5):
        log.info("msg", n=i)
        file_handler.doRollover()

    rotated = sorted(tmp_path.glob("app.log.*.gz"))
    assert len(rotated) <= 2  # backupCount is honoured
