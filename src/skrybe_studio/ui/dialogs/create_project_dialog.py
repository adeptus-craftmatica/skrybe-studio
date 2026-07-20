"""Create Project dialog: a name and a location, nothing more."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CreateProjectDialog(QDialog):
    def __init__(self, default_directory: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Project")
        self.setMinimumWidth(420)

        self._name_edit = QLineEdit()
        self._location_edit = QLineEdit(str(default_directory))

        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse)

        location_row = QHBoxLayout()
        location_row.addWidget(self._location_edit)
        location_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Project name", self._name_edit)
        form.addRow("Location", location_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        hint = QLabel("Creates a new project directory ending in .skrybe")
        hint.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Choose Location", self._location_edit.text()
        )
        if directory:
            self._location_edit.setText(directory)

    def project_name(self) -> str:
        return self._name_edit.text().strip()

    def project_root(self) -> Path:
        return Path(self._location_edit.text()).expanduser() / self.project_name()
