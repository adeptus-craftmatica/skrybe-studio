"""User-friendly presentation of an unhandled exception.

The plain-language summary is the primary message; the raw traceback is
hidden behind a "Show Details" toggle and is copyable, never the
headline the user sees first.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ErrorDialog(QDialog):
    def __init__(self, summary: str, technical_detail: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Something went wrong")
        self.setMinimumWidth(480)
        self._technical_detail = technical_detail

        layout = QVBoxLayout(self)

        summary_label = QLabel(summary)
        summary_label.setObjectName("error")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        self._details = QPlainTextEdit(technical_detail)
        self._details.setReadOnly(True)
        self._details.setVisible(False)
        self._details.setMinimumHeight(160)
        layout.addWidget(self._details)

        buttons = QDialogButtonBox()
        self._toggle_button = QPushButton("Show Details")
        self._toggle_button.clicked.connect(self._toggle_details)
        copy_button = QPushButton("Copy Details")
        copy_button.clicked.connect(self._copy_details)
        buttons.addButton(self._toggle_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _toggle_details(self) -> None:
        visible = not self._details.isVisible()
        self._details.setVisible(visible)
        self._toggle_button.setText("Hide Details" if visible else "Show Details")

    def _copy_details(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._technical_detail)
