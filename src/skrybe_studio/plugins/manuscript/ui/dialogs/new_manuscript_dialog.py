"""New Manuscript dialog: a title and an optional local template."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.plugins.manuscript.application.templates import (
    TEMPLATE_LABELS,
    ManuscriptTemplate,
)


class NewManuscriptDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Manuscript")
        self.setMinimumWidth(360)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Untitled Manuscript")
        self._template_combo = QComboBox()
        for template in ManuscriptTemplate:
            self._template_combo.addItem(TEMPLATE_LABELS[template], template)

        form = QFormLayout()
        form.addRow("Title", self._title_edit)
        form.addRow("Template", self._template_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def title(self) -> str:
        return self._title_edit.text().strip() or "Untitled Manuscript"

    def template(self) -> ManuscriptTemplate:
        return self._template_combo.currentData()
