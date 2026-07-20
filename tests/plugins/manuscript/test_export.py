from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.export.compile import (
    CompileDocument,
    Compiler,
    CompileRequest,
    CompileSection,
)
from skrybe_studio.plugins.manuscript.application.export.docx_exporter import export_docx
from skrybe_studio.plugins.manuscript.application.export.html import export_html
from skrybe_studio.plugins.manuscript.application.export.markdown import export_markdown
from skrybe_studio.plugins.manuscript.application.export.plain_text import export_plain_text
from skrybe_studio.plugins.manuscript.application.export.service import (
    ExportFormat,
    ExportPreset,
    ExportService,
)
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.domain.document_ir import DocumentBlock, TextSpan, paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.infrastructure.repositories import ManuscriptRepository


def _build_novel(hierarchy: HierarchyService, documents: DocumentService):
    manuscript = hierarchy.create_manuscript("My Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Chapter One")
    scene_a = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Scene One")
    scene_b = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Scene Two")
    documents.save_content(scene_a.id, (paragraph("The first scene."),))
    documents.save_content(scene_b.id, (paragraph("The second scene."),))
    return manuscript, chapter, scene_a, scene_b


def test_compile_produces_deterministic_order(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
) -> None:
    manuscript, _chapter, _scene_a, _scene_b = _build_novel(hierarchy, documents)
    compiler = Compiler(manuscript_repository)

    result = compiler.compile(CompileRequest(manuscript_id=manuscript.id))

    assert result.succeeded
    assert result.document is not None
    assert result.document.sections[0].title == "Chapter One"
    assert [s.title for s in result.document.sections[0].children] == ["Scene One", "Scene Two"]


def test_compile_excludes_nodes_flagged_out_of_compile(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
) -> None:
    manuscript, _chapter, _scene_a, scene_b = _build_novel(hierarchy, documents)
    hierarchy.update_metadata(scene_b.id, include_in_compile=False)
    compiler = Compiler(manuscript_repository)

    result = compiler.compile(
        CompileRequest(manuscript_id=manuscript.id, respect_compile_flag=True)
    )

    assert result.document is not None
    titles = [s.title for s in result.document.sections[0].children]
    assert titles == ["Scene One"]


def test_compile_can_ignore_compile_flag_for_full_manuscript_preset(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
) -> None:
    manuscript, _chapter, _scene_a, scene_b = _build_novel(hierarchy, documents)
    hierarchy.update_metadata(scene_b.id, include_in_compile=False)
    compiler = Compiler(manuscript_repository)

    result = compiler.compile(
        CompileRequest(manuscript_id=manuscript.id, respect_compile_flag=False)
    )

    assert result.document is not None
    titles = [s.title for s in result.document.sections[0].children]
    assert titles == ["Scene One", "Scene Two"]


def test_compile_excludes_archived_nodes(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
) -> None:
    manuscript, _chapter, scene_a, _scene_b = _build_novel(hierarchy, documents)
    hierarchy.archive_node(scene_a.id)
    compiler = Compiler(manuscript_repository)

    result = compiler.compile(
        CompileRequest(manuscript_id=manuscript.id, respect_compile_flag=False)
    )

    assert result.document is not None
    titles = [s.title for s in result.document.sections[0].children]
    assert titles == ["Scene Two"]


def test_compile_unknown_manuscript_returns_error(
    manuscript_repository: ManuscriptRepository,
) -> None:
    compiler = Compiler(manuscript_repository)
    result = compiler.compile(CompileRequest(manuscript_id=uuid4()))

    assert not result.succeeded
    assert result.document is None
    assert result.errors


def _compile_document(
    hierarchy: HierarchyService, documents: DocumentService, manuscript_repository
):
    manuscript, *_ = _build_novel(hierarchy, documents)
    compiler = Compiler(manuscript_repository)
    result = compiler.compile(
        CompileRequest(manuscript_id=manuscript.id, respect_compile_flag=False)
    )
    assert result.document is not None
    return result.document


def test_plain_text_exporter_includes_titles_and_scene_content(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
    tmp_path: Path,
) -> None:
    document = _compile_document(hierarchy, documents, manuscript_repository)
    output = tmp_path / "out.txt"

    export_plain_text(document, output)

    text = output.read_text()
    assert "My Novel" in text
    assert "Chapter One" in text
    assert "The first scene." in text
    assert "The second scene." in text
    assert "* * *" in text  # separator between two consecutive scenes


def test_markdown_exporter_uses_headings_and_bold_italic(tmp_path: Path) -> None:
    section = CompileSection(
        node_id=uuid4(),
        node_type=ManuscriptNodeType.CHAPTER,
        title="Chapter One",
        level=1,
        blocks=(),
        children=(
            CompileSection(
                node_id=uuid4(),
                node_type=ManuscriptNodeType.SCENE,
                title="Scene One",
                level=2,
                blocks=(
                    DocumentBlock(
                        spans=(
                            TextSpan(text="bold", bold=True),
                            TextSpan(text=" and "),
                            TextSpan(text="italic", italic=True),
                        )
                    ),
                ),
            ),
        ),
    )
    document = CompileDocument(manuscript_id=uuid4(), title="My Novel", sections=(section,))
    output = tmp_path / "out.md"

    export_markdown(document, output)

    text = output.read_text()
    assert "# My Novel" in text
    assert "## Chapter One" in text
    assert "**bold**" in text
    assert "*italic*" in text


def test_html_exporter_escapes_user_content(tmp_path: Path) -> None:
    section = CompileSection(
        node_id=uuid4(),
        node_type=ManuscriptNodeType.SCENE,
        title="Scene",
        level=1,
        blocks=(paragraph("<script>alert('x')</script>"),),
    )
    document = CompileDocument(manuscript_id=uuid4(), title="Novel", sections=(section,))
    output = tmp_path / "out.html"

    export_html(document, output)

    text = output.read_text()
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_docx_exporter_produces_a_valid_file(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
    tmp_path: Path,
) -> None:
    document = _compile_document(hierarchy, documents, manuscript_repository)
    output = tmp_path / "out.docx"

    export_docx(document, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_export_service_runs_export_in_background_job(
    hierarchy: HierarchyService,
    documents: DocumentService,
    manuscript_repository: ManuscriptRepository,
    tmp_path: Path,
    qapp,
) -> None:
    manuscript, *_ = _build_novel(hierarchy, documents)
    jobs = JobManager()
    service = ExportService(Compiler(manuscript_repository), jobs)
    output = tmp_path / "out.txt"
    outcomes: list[Path] = []

    result = service.export(
        manuscript.id,
        ExportFormat.PLAIN_TEXT,
        output,
        preset=ExportPreset.FULL_MANUSCRIPT,
        on_success=outcomes.append,
    )
    jobs.wait_for_done(5000)
    qapp.processEvents()

    assert result.succeeded
    assert output.exists()
    assert outcomes == [output]


def test_export_service_reports_compile_errors_without_touching_disk(
    manuscript_repository: ManuscriptRepository, tmp_path: Path
) -> None:
    from uuid import uuid4

    jobs = JobManager()
    service = ExportService(Compiler(manuscript_repository), jobs)
    output = tmp_path / "out.txt"
    errors: list[str] = []

    service.export(uuid4(), ExportFormat.PLAIN_TEXT, output, on_error=errors.append)

    assert errors
    assert not output.exists()
