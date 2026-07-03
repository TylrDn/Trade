"""Structured logging setup (structlog + stdlib).

Call `configure_logging()` once at process start. All modules should use
the stdlib `logging.getLogger(__name__)`; structlog wraps stdlib records
so no code changes are needed at call sites.
"""

from __future__ import annotations

import logging
import sys

import structlog

from nautilus_trade.config import system_cfg


def configure_logging(json_output: bool | None = None) -> None:
    """Configure structlog + stdlib logging.

    Args:
        json_output: If True, emit JSON logs (production). If False, emit
            colored console logs (research). If None, choose based on env.
    """
    if json_output is None:
        json_output = system_cfg.is_live

    level = getattr(logging, system_cfg.nautilus_log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
