"""Builds a single Qt stylesheet from `DesignTokens`.

This is the only place a color, spacing, or radius value should be
written as a literal for widget styling - everything else references
`DesignTokens` or object names targeted here, so retheming never
requires hunting through widget code.
"""

from __future__ import annotations

from skrybe_studio.core.themes.tokens import DesignTokens


def build_stylesheet(tokens: DesignTokens) -> str:
    c = tokens.colors
    t = tokens.typography
    r = tokens.radius
    s = tokens.spacing
    return f"""
    QWidget {{
        font-family: {t.font_family};
        font-size: {t.size_body}px;
        color: {c.text};
    }}
    QMainWindow, QDialog {{
        background: {c.background};
    }}
    QWidget#panel, QFrame#panel {{
        background: {c.surface};
        border: 1px solid {c.border};
        border-radius: {r.md}px;
    }}
    QMenuBar {{
        background: {c.surface};
        border-bottom: 1px solid {c.border};
    }}
    QMenuBar::item:selected {{
        background: {c.selection};
    }}
    QMenu {{
        background: {c.surface};
        border: 1px solid {c.border};
    }}
    QMenu::item:selected {{
        background: {c.selection};
    }}
    QToolBar {{
        background: {c.surface};
        border-bottom: 1px solid {c.border};
        spacing: {s.sm}px;
        padding: {s.xs}px;
    }}
    QStatusBar {{
        background: {c.surface};
        border-top: 1px solid {c.border};
        color: {c.text_muted};
    }}
    QDockWidget {{
        color: {c.text_muted};
        titlebar-close-icon: none;
    }}
    QDockWidget::title {{
        background: {c.surface_alt};
        padding: {s.xs}px {s.sm}px;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QListView, QTreeView, QComboBox, QSpinBox {{
        background: {c.surface};
        border: 1px solid {c.border};
        border-radius: {r.sm}px;
        padding: {s.xs}px;
        selection-background-color: {c.selection};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {c.accent};
    }}
    QPushButton {{
        background: {c.surface_alt};
        border: 1px solid {c.border};
        border-radius: {r.sm}px;
        padding: {s.xs}px {s.md}px;
    }}
    QPushButton:hover {{
        border-color: {c.accent};
    }}
    QPushButton:disabled {{
        color: {c.text_muted};
    }}
    QPushButton#primary {{
        background: {c.accent};
        color: {c.accent_text};
        border: none;
        font-weight: {t.weight_medium};
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {c.selection};
    }}
    QLabel#muted {{
        color: {c.text_muted};
    }}
    QLabel#error {{
        color: {c.error};
    }}
    QLabel#success {{
        color: {c.success};
    }}
    QLabel#warning {{
        color: {c.warning};
    }}
    QLabel#heading {{
        font-size: {t.size_heading}px;
        font-weight: {t.weight_medium};
    }}
    QLabel#title {{
        font-size: {t.size_title}px;
        font-weight: {t.weight_bold};
    }}
    """
