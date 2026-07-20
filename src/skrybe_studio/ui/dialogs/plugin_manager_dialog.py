"""Plugin manager/status dialog: what loaded, what didn't, and why."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.plugins.loader import LoadedPlugin, PluginLoadFailure


class PluginManagerDialog(QDialog):
    def __init__(
        self,
        loaded_plugins: list[LoadedPlugin],
        failures: list[PluginLoadFailure],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Plugins")
        self.setMinimumSize(560, 380)

        layout = QVBoxLayout(self)

        active_label = QLabel(f"Active plugins ({len(loaded_plugins)})")
        active_label.setObjectName("heading")
        layout.addWidget(active_label)

        active_tree = QTreeWidget()
        active_tree.setHeaderLabels(["Plugin", "Version", "Capabilities"])
        for loaded in loaded_plugins:
            active_tree.addTopLevelItem(
                QTreeWidgetItem(
                    [
                        loaded.manifest.name,
                        loaded.manifest.version,
                        ", ".join(loaded.manifest.capabilities),
                    ]
                )
            )
        layout.addWidget(active_tree)

        if failures:
            failed_label = QLabel(f"Failed to load ({len(failures)})")
            failed_label.setObjectName("error")
            layout.addWidget(failed_label)

            failed_tree = QTreeWidget()
            failed_tree.setHeaderLabels(["Plugin", "Category", "Reason"])
            for failure in failures:
                failed_tree.addTopLevelItem(
                    QTreeWidgetItem([failure.plugin_id, failure.category, failure.reason])
                )
            layout.addWidget(failed_tree)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.clicked.connect(self.accept)
        layout.addWidget(buttons)
