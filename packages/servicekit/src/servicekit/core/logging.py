"""Structured logging configuration with request tracing support."""

import logging
import os
import sys
from typing import Any

import structlog
from structlog.typing import Processor


def configure_logging() -> None:
    """Configure structlog and intercept standard library logging."""
    log_format = os.getenv("LOG_FORMAT", "console").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)

    # Shared processors for structlog
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    # Choose renderer based on format
    if log_format == "json":
        formatter_processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        formatter_processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog to use standard library logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(processors=formatter_processors))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Configure uvicorn and gunicorn loggers to use the same handler
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "gunicorn.access", "gunicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False


def get_logger(name: str | None = None) -> Any:
    """Get a configured structlog logger instance."""
    return structlog.get_logger(name)


def add_request_context(**context: Any) -> None:
    """Add context variables that will be included in all log messages."""
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context(*keys: str) -> None:
    """Clear specific context variables."""
    structlog.contextvars.unbind_contextvars(*keys)


def reset_request_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()
