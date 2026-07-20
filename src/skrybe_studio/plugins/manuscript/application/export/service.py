"""Orchestrates compile + background export, with a small preset model.

The compile step (DB reads) runs synchronously on the caller's thread -
it is fast, and our SQLite connections are not safe to use from a worker
thread. Only the exporter's actual formatting/writing work - which
receives an already-built, DB-free `CompileDocument` - runs in the
background `Job`, matching the pattern established by the Asset Library
plugin's import job.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from skrybe_studio.core.jobs.job import CancellationToken, Job
from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.plugins.manuscript.application.export.compile import (
    CompileDocument,
    Compiler,
    CompileRequest,
    CompileResult,
)
from skrybe_studio.plugins.manuscript.application.export.docx_exporter import export_docx
from skrybe_studio.plugins.manuscript.application.export.html import export_html
from skrybe_studio.plugins.manuscript.application.export.markdown import export_markdown
from skrybe_studio.plugins.manuscript.application.export.plain_text import export_plain_text


class ExportFormat(StrEnum):
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"


EXPORT_FORMAT_LABELS: dict[ExportFormat, str] = {
    ExportFormat.PLAIN_TEXT: "Plain Text (.txt)",
    ExportFormat.MARKDOWN: "Markdown (.md)",
    ExportFormat.HTML: "HTML (.html)",
    ExportFormat.DOCX: "Word Document (.docx)",
}

EXPORT_FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    ExportFormat.PLAIN_TEXT: ".txt",
    ExportFormat.MARKDOWN: ".md",
    ExportFormat.HTML: ".html",
    ExportFormat.DOCX: ".docx",
}

_EXPORTER_BY_FORMAT: dict[ExportFormat, Callable[[CompileDocument, Path], Path]] = {
    ExportFormat.PLAIN_TEXT: export_plain_text,
    ExportFormat.MARKDOWN: export_markdown,
    ExportFormat.HTML: export_html,
    ExportFormat.DOCX: export_docx,
}


class ExportPreset(StrEnum):
    FULL_MANUSCRIPT = "full_manuscript"
    SUBMISSION_DRAFT = "submission_draft"
    PLAIN_BACKUP = "plain_backup"


EXPORT_PRESET_LABELS: dict[ExportPreset, str] = {
    ExportPreset.FULL_MANUSCRIPT: "Full Manuscript",
    ExportPreset.SUBMISSION_DRAFT: "Submission Draft",
    ExportPreset.PLAIN_BACKUP: "Plain Backup",
}


def preset_to_request(preset: ExportPreset, manuscript_id: UUID) -> CompileRequest:
    respect_compile_flag = preset == ExportPreset.SUBMISSION_DRAFT
    return CompileRequest(manuscript_id=manuscript_id, respect_compile_flag=respect_compile_flag)


class ExportJob(Job):
    """Runs one exporter against an already-compiled document, off the main thread."""

    def __init__(
        self,
        document: CompileDocument,
        exporter: Callable[[CompileDocument, Path], Path],
        output_path: Path,
    ) -> None:
        self._document = document
        self._exporter = exporter
        self._output_path = output_path

    def run(self, cancellation_token: CancellationToken) -> Path:
        cancellation_token.raise_if_cancelled()
        return self._exporter(self._document, self._output_path)


class ExportService:
    def __init__(self, compiler: Compiler, jobs: JobManager) -> None:
        self._compiler = compiler
        self._jobs = jobs

    def export(
        self,
        manuscript_id: UUID,
        export_format: ExportFormat,
        output_path: Path,
        *,
        preset: ExportPreset = ExportPreset.SUBMISSION_DRAFT,
        on_success: Callable[[Path], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> CompileResult:
        """Compiles synchronously (fast DB reads) and submits the write step
        as a background job. Returns the `CompileResult` immediately so the
        caller can surface compile warnings/errors before the job finishes."""
        request = preset_to_request(preset, manuscript_id)
        result = self._compiler.compile(request)
        if not result.succeeded or result.document is None:
            if on_error is not None:
                message = "; ".join(error.message for error in result.errors) or "Compile failed"
                on_error(message)
            return result

        exporter = _EXPORTER_BY_FORMAT[export_format]
        job = ExportJob(result.document, exporter, output_path)

        def _handle_success(path: object) -> None:
            if on_success is not None:
                assert isinstance(path, Path)
                on_success(path)

        self._jobs.submit(job, on_success=_handle_success, on_error=on_error)
        return result
