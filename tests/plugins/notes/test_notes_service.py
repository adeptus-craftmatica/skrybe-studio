from __future__ import annotations

from pathlib import Path

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.notes.application.events import NoteCreated, NoteDeleted
from skrybe_studio.plugins.notes.application.search_provider import NotesSearchProvider
from skrybe_studio.plugins.notes.application.service import NotesService
from skrybe_studio.plugins.notes.domain.note import ENTITY_TYPE
from skrybe_studio.plugins.notes.infrastructure.models import NotesBase
from skrybe_studio.plugins.notes.infrastructure.repository import NoteRepository


def _service(tmp_path: Path) -> tuple[NotesService, EntityService, EventBus]:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    NotesBase.metadata.create_all(database.engine)
    entities = EntityService(database)
    events = EventBus()
    repository = NoteRepository(database)
    return NotesService(repository, entities, events), entities, events


def test_create_note_also_creates_shared_entity(tmp_path: Path) -> None:
    service, entities, _events = _service(tmp_path)

    note = service.create_note("My Note", body="hello world")

    entity = entities.get(note.id)
    assert entity is not None
    assert entity.entity_type == ENTITY_TYPE
    assert entity.title == "My Note"


def test_create_note_publishes_event(tmp_path: Path) -> None:
    service, _entities, events = _service(tmp_path)
    received: list[str] = []
    events.subscribe(NoteCreated, lambda event: received.append(event.title))

    service.create_note("Chapter One")

    assert received == ["Chapter One"]


def test_word_count_reflects_body(tmp_path: Path) -> None:
    service, _entities, _events = _service(tmp_path)
    note = service.create_note("Note", body="one two three four")

    assert note.word_count == 4


def test_rename_note_renames_shared_entity_too(tmp_path: Path) -> None:
    service, entities, _events = _service(tmp_path)
    note = service.create_note("Old Title")

    service.rename_note(note.id, "New Title")

    entity = entities.get(note.id)
    renamed_note = service.get_note(note.id)
    assert entity is not None
    assert renamed_note is not None
    assert entity.title == "New Title"
    assert renamed_note.title == "New Title"


def test_delete_note_soft_deletes_entity_and_publishes_event(tmp_path: Path) -> None:
    service, entities, events = _service(tmp_path)
    note = service.create_note("Temporary")
    received: list[object] = []
    events.subscribe(NoteDeleted, received.append)

    assert service.delete_note(note.id) is True

    assert service.get_note(note.id) is None
    assert entities.get(note.id) is None
    assert len(received) == 1


def test_search_notes_matches_title_and_body(tmp_path: Path) -> None:
    service, _entities, _events = _service(tmp_path)
    service.create_note("Dragons of the North", body="A tale of ice and fire.")
    service.create_note("Unrelated", body="Nothing to do with dragons here either.")

    results = service.search_notes("dragon")

    assert {note.title for note in results} == {"Dragons of the North", "Unrelated"}


def test_search_provider_returns_shared_search_results(tmp_path: Path) -> None:
    service, _entities, _events = _service(tmp_path)
    note = service.create_note("Searchable Note", body="findable content")

    # A second Database handle onto the same file, as the plugin's activate() would create.
    provider = NotesSearchProvider(NoteRepository(Database(tmp_path / "project.db")))
    results = provider.search("findable")

    assert any(result.entity_id == note.id for result in results)
