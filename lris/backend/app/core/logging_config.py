"""Centralized logging configuration.

Every module obtains its logger via `logging.getLogger(__name__)`; this
module is only responsible for configuring handlers/formatters once, at
application startup (FastAPI startup event, or top of a scraper/CLI
entrypoint).
"""

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure the root logger with a consistent format.

    Idempotent: safe to call multiple times (e.g. once from `main.py` and
    once from a standalone scraper script) without duplicating handlers.
    """
    settings = get_settings()
    root_logger = logging.getLogger()

    if root_logger.handlers:
        # Already configured (e.g. re-imported in tests) — avoid duplicate
        # handlers which would duplicate every log line.
        root_logger.setLevel(settings.log_level)
        return

    root_logger.setLevel(settings.log_level)

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers by default.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
