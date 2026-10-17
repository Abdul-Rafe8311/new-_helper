"""structlog setup: pretty console logs in dev, JSON lines in prod."""

import logging
import sys

import structlog

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[
            *shared,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s", force=True)
