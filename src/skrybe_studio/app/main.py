"""Desktop application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.ui.main_window import MainWindow


def main() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Skrybe Studio")
    qt_app.setOrganizationName("adeptus-craftmatica")
    qt_app.setApplicationVersion("0.1.0")

    application = Application()
    application.load_plugins()

    window = MainWindow(application)
    window.show()

    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
