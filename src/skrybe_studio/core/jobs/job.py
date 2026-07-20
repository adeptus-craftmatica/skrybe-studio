"""The unit of background work: a `Job` plus a cooperative cancellation token."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod


class JobCancelledError(Exception):
    """Raised by a `Job` to unwind cleanly once cancellation is observed."""


class CancellationToken:
    """A cooperative cancellation flag passed into a running `Job`."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise JobCancelledError


class Job(ABC):
    """A unit of work executed on a background thread by the `JobManager`."""

    @abstractmethod
    def run(self, cancellation_token: CancellationToken) -> object:
        """Perform the work and return a result delivered on the main thread."""
