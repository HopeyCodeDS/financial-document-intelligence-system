"""
Structured logging configuration using structlog.

- Development: coloured, human-readable console output
- Production: JSON lines, machine-parseable, no ANSI codes

All log records include: timestamp, level, logger name, and any bound context.
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Configure structlog and stdlib logging for the application.

    Must be called once at application startup before any loggers are created.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # Production: JSON lines
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.dict_tracebacks,
                renderer,
            ],
            foreign_pre_chain=shared_processors,
        )
    else:
        # Development: pretty console
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
            foreign_pre_chain=shared_processors,
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "asyncio", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
