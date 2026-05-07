import logging

import structlog

from app.core.config import Settings
from app.core.request_context import get_request_id


def _add_request_id(logger, method_name, event_dict):  # noqa: ARG001
    event_dict["request_id"] = get_request_id()
    return event_dict


def configure_logging(settings: Settings) -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            _add_request_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
