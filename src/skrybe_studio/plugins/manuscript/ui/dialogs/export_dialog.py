"""Export dialog: pick a format and a preset before choosing an output file."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.plugins.manuscript.application.export.service import (
    EXPORT_FORMAT_LABELS,
    EXPORT_PRESET_LABELS,
    ExportFormat,
    ExportPreset,
)


class ExportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Manuscript")
        self.setMinimumWidth(360)

        self._format_combo = QComboBox()
        for export_format in ExportFormat:
            self._format_combo.addItem(EXPORT_FORMAT_LABELS[export_format], export_format)

        self._preset_combo = QComboBox()
        for preset in ExportPreset:
            self._preset_combo.addItem(EXPORT_PRESET_LABELS[preset], preset)
        self._preset_combo.setCurrentIndex(
            self._preset_combo.findData(ExportPreset.SUBMISSION_DRAFT)
        )

        form = QFormLayout()
        form.addRow("Format", self._format_combo)
        form.addRow("Preset", self._preset_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("Export…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def export_format(self) -> ExportFormat:
        return self._format_combo.currentData()

    def preset(self) -> ExportPreset:
        return self._preset_combo.currentData()
