"""Rotating application log configuration."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(log_dir: Path, *, level: int = logging.INFO) -> Path:
    """Configure the root logger with a rotating file handler and console output.

    Returns the path of the active log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "skrybe-studio.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.getLogger(__name__).info("Logging configured; writing to %s", log_file)
    return log_file
