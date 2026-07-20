"""Runs `Job`s on a managed Qt thread pool and marshals results to the main thread.

Qt automatically queues signal delivery across thread boundaries, so the
`on_success`/`on_error` callbacks always run on the main/UI thread even
though the job itself executes on a worker thread.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from skrybe_studio.core.jobs.job import CancellationToken, Job

logger = logging.getLogger(__name__)


class _JobSignals(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)


class _JobRunnable(QRunnable):
    def __init__(
        self, job_id: str, job: Job, token: CancellationToken, signals: _JobSignals
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._job = job
        self._token = token
        self._signals = signals

    @Slot()
    def run(self) -> None:
        try:
            result = self._job.run(self._token)
        except Exception as exc:
            logger.exception("Background job %s failed", self._job_id)
            self._signals.failed.emit(self._job_id, str(exc))
        else:
            self._signals.finished.emit(self._job_id, result)


class JobManager(QObject):
    """Submits `Job`s to a bounded thread pool with per-job cancellation."""

    def __init__(self, max_thread_count: int = 4) -> None:
        super().__init__()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(max_thread_count)
        self._tokens: dict[str, CancellationToken] = {}
        self._signals = _JobSignals()
        self._signals.finished.connect(self._on_finished)
        self._signals.failed.connect(self._on_failed)
        self._on_success: dict[str, Callable[[object], None]] = {}
        self._on_error: dict[str, Callable[[str], None]] = {}

    def submit(
        self,
        job: Job,
        *,
        on_success: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        token = CancellationToken()
        self._tokens[job_id] = token
        if on_success is not None:
            self._on_success[job_id] = on_success
        if on_error is not None:
            self._on_error[job_id] = on_error
        runnable = _JobRunnable(job_id, job, token, self._signals)
        self._pool.start(runnable)
        logger.debug("Submitted background job %s (%s)", job_id, type(job).__name__)
        return job_id

    def cancel(self, job_id: str) -> None:
        token = self._tokens.get(job_id)
        if token is not None:
            token.cancel()

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        return self._pool.waitForDone(timeout_ms)

    @Slot(str, object)
    def _on_finished(self, job_id: str, result: object) -> None:
        callback = self._on_success.pop(job_id, None)
        self._on_error.pop(job_id, None)
        self._tokens.pop(job_id, None)
        if callback is not None:
            callback(result)

    @Slot(str, str)
    def _on_failed(self, job_id: str, message: str) -> None:
        callback = self._on_error.pop(job_id, None)
        self._on_success.pop(job_id, None)
        self._tokens.pop(job_id, None)
        if callback is not None:
            callback(message)
