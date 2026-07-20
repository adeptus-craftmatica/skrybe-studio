"""Background job abstraction: work off the Qt main thread with cancellation."""

from skrybe_studio.core.jobs.job import CancellationToken, Job, JobCancelledError
from skrybe_studio.core.jobs.manager import JobManager

__all__ = ["CancellationToken", "Job", "JobCancelledError", "JobManager"]
