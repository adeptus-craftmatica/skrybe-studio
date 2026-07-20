"""Top-level unhandled-exception handling.

The core logs and formats the failure but never imports Qt to display
it - the application layer registers an `ErrorPresenter` (typically
backed by a dialog) so core stays UI-framework-agnostic.
"""

from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Callable
from types import TracebackType

logger = logging.getLogger(__name__)

ErrorPresenter = Callable[[str, str], None]  # (user_facing_summary, technical_detail)

_presenter: ErrorPresenter | None = None


def set_error_presenter(presenter: ErrorPresenter | None) -> None:
    global _presenter
    _presenter = presenter


def install_excepthook() -> None:
    sys.excepthook = _handle_uncaught_exception


def _handle_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    technical_detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    summary = f"An unexpected error occurred: {exc_value}"
    if _presenter is None:
        print(summary, file=sys.stderr)
        return
    try:
        _presenter(summary, technical_detail)
    except Exception:
        logger.exception("Error presenter itself raised while reporting an unhandled exception")
