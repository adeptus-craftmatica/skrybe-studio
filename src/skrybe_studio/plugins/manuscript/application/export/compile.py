"""The typed compile intermediate representation and the compiler that builds it.

This is deliberately not tied to HTML, Markdown, or DOCX: it is just the
manuscript hierarchy plus each text-bearing node's document content,
traversed once, deterministically (sort order, depth-first), with
archived nodes always excluded and `include_in_compile` respected when
the request asks for it. A future Publishing plugin can add its own
exporters against this same `CompileDocument` without importing
Manuscript's persistence models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from skrybe_studio.plugins.manuscript.domain.document_ir import EMPTY_DOCUMENT, DocumentContent
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.infrastructure.repositories import ManuscriptRepository


@dataclass(frozen=True, slots=True)
class CompileRequest:
    manuscript_id: UUID
    respect_compile_flag: bool = True


@dataclass(frozen=True, slots=True)
class CompileSection:
    node_id: UUID
    node_type: ManuscriptNodeType
    title: str
    level: int
    blocks: DocumentContent
    children: tuple[CompileSection, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CompileDocument:
    manuscript_id: UUID
    title: str
    sections: tuple[CompileSection, ...]


@dataclass(frozen=True, slots=True)
class ExportWarning:
    message: str


@dataclass(frozen=True, slots=True)
class ExportError:
    message: str


@dataclass(frozen=True, slots=True)
class CompileResult:
    document: CompileDocument | None
    warnings: tuple[ExportWarning, ...] = ()
    errors: tuple[ExportError, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.document is not None and not self.errors


class Compiler:
    def __init__(self, repository: ManuscriptRepository) -> None:
        self._repository = repository

    def compile(self, request: CompileRequest) -> CompileResult:
        root = self._repository.get_node(request.manuscript_id)
        if root is None:
            return CompileResult(
                document=None,
                errors=(ExportError(f"Manuscript {request.manuscript_id} not found"),),
            )
        warnings: list[ExportWarning] = []
        sections = self._compile_children(root.id, level=1, request=request, warnings=warnings)
        if not sections:
            warnings.append(ExportWarning("Manuscript has no included content to compile."))
        document = CompileDocument(
            manuscript_id=root.id, title=root.title, sections=tuple(sections)
        )
        return CompileResult(document=document, warnings=tuple(warnings))

    def _compile_children(
        self, parent_id: UUID, *, level: int, request: CompileRequest, warnings: list[ExportWarning]
    ) -> list[CompileSection]:
        sections: list[CompileSection] = []
        for child in self._repository.list_children(parent_id, include_archived=False):
            if request.respect_compile_flag and not child.include_in_compile:
                continue
            blocks = (
                self._repository.get_document_content(child.id)
                if child.is_text_bearing
                else EMPTY_DOCUMENT
            )
            if child.is_text_bearing and not blocks:
                warnings.append(ExportWarning(f"'{child.title}' has no content."))
            children = (
                self._compile_children(
                    child.id, level=level + 1, request=request, warnings=warnings
                )
                if child.is_container
                else []
            )
            sections.append(
                CompileSection(
                    node_id=child.id,
                    node_type=child.node_type,
                    title=child.title,
                    level=level,
                    blocks=blocks,
                    children=tuple(children),
                )
            )
        return sections
