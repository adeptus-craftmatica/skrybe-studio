from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import uuid4

from PySide6.QtGui import QColor, QImage

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import ApplicationPaths
from skrybe_studio.plugins.assets.application.events import AssetSelectionChanged
from skrybe_studio.plugins.assets.plugin import AssetsPlugin
from skrybe_studio.plugins.assets.ui.details_panel import AssetDetailsPanel

ASSETS_PLUGIN_ID = "com.adeptus-craftmatica.skrybe.assets"


def _make_image(path: Path, color: str = "red") -> Path:
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    image.save(str(path))
    return path


def _assets_plugin(app: Application) -> AssetsPlugin:
    return cast(
        AssetsPlugin,
        next(
            loaded.instance
            for loaded in app.loaded_plugins
            if loaded.manifest.id == ASSETS_PLUGIN_ID
        ),
    )


def test_selecting_an_image_asset_shows_a_preview(
    app_paths: ApplicationPaths, project_root: Path, tmp_path: Path, qapp, qtbot
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Preview Test")
    plugin = _assets_plugin(app)
    assert plugin.service is not None

    asset_id = plugin.service.import_asset(_make_image(tmp_path / "source.png"))
    app.jobs.wait_for_done(5000)
    qapp.processEvents()

    panel = AssetDetailsPanel(plugin, app.events)
    qtbot.addWidget(panel)
    app.events.publish(AssetSelectionChanged(asset_id=asset_id))

    assert panel._original_pixmap is not None
    assert not panel._original_pixmap.isNull()

    app.close_project()
    app.shutdown()


def test_selecting_a_non_image_asset_shows_no_preview(
    app_paths: ApplicationPaths, project_root: Path, tmp_path: Path, qapp, qtbot
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "No Preview Test")
    plugin = _assets_plugin(app)
    assert plugin.service is not None

    source = tmp_path / "notes.txt"
    source.write_text("plain text asset")
    asset_id = plugin.service.import_asset(source)
    app.jobs.wait_for_done(5000)
    qapp.processEvents()

    panel = AssetDetailsPanel(plugin, app.events)
    qtbot.addWidget(panel)
    app.events.publish(AssetSelectionChanged(asset_id=asset_id))

    assert panel._original_pixmap is None

    app.close_project()
    app.shutdown()


def test_selecting_an_asset_with_no_relationships_hides_the_links_section(
    app_paths: ApplicationPaths, project_root: Path, tmp_path: Path, qapp, qtbot
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Links Test")
    plugin = _assets_plugin(app)
    assert plugin.service is not None

    asset_id = plugin.service.import_asset(_make_image(tmp_path / "source.png"))
    app.jobs.wait_for_done(5000)
    qapp.processEvents()

    panel = AssetDetailsPanel(plugin, app.events)
    qtbot.addWidget(panel)
    panel.show()
    app.events.publish(AssetSelectionChanged(asset_id=asset_id))

    assert panel._links_list.isVisible() is False

    app.close_project()
    app.shutdown()


def test_selecting_an_asset_referenced_by_another_entity_shows_the_backlink(
    app_paths: ApplicationPaths, project_root: Path, tmp_path: Path, qapp, qtbot
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Backlink Test")
    plugin = _assets_plugin(app)
    assert plugin.service is not None
    assert plugin.entities is not None
    assert plugin.relationships is not None

    asset_id = plugin.service.import_asset(_make_image(tmp_path / "cover.png"))
    app.jobs.wait_for_done(5000)
    qapp.processEvents()

    referencing_entity = plugin.entities.create(
        entity_type="manuscript.node",
        title="My Novel",
        plugin_owner="com.adeptus-craftmatica.skrybe.manuscript",
        entity_id=uuid4(),
    )
    plugin.relationships.create(
        source_entity_id=referencing_entity.id,
        target_entity_id=asset_id,
        relationship_type="manuscript.cover_asset",
        plugin_owner="com.adeptus-craftmatica.skrybe.manuscript",
    )

    panel = AssetDetailsPanel(plugin, app.events)
    qtbot.addWidget(panel)
    panel.show()
    app.events.publish(AssetSelectionChanged(asset_id=asset_id))

    assert panel._links_list.isVisible() is True
    assert panel._links_list.count() == 1
    assert panel._links_list.item(0).text() == "My Novel  —  Cover Asset"

    app.close_project()
    app.shutdown()
