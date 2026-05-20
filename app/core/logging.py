from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog
from structlog.contextvars import merge_contextvars
from structlog.dev import ConsoleRenderer
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    add_log_level,
    format_exc_info,
)

if TYPE_CHECKING:
    from app.core.config import Settings

_configured = False


def configure_logging(settings: Settings) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    log_level = getattr(logging, settings.log_level, logging.INFO)

    timestamper = TimeStamper(fmt="iso")

    shared_processors: list[structlog.types.Processor] = [
        merge_contextvars,
        add_log_level,
        timestamper,
        StackInfoRenderer(),
        format_exc_info,
    ]

    if settings.log_format == "pretty":
        renderer: structlog.types.Processor = ConsoleRenderer(colors=True)
    else:
        renderer = JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        stdlib_logger = logging.getLogger(logger_name)
        stdlib_logger.handlers.clear()
        stdlib_logger.propagate = True
        stdlib_logger.setLevel(log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)
