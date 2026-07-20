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
    # Only override font-family when a real, installed font name is set -
    # otherwise leave Qt's native per-platform default font alone (see the
    # comment on TypographyTokens.font_family for why).
    font_family_rule = f"font-family: {t.font_family};" if t.font_family else ""
    return f"""
    QWidget {{
        {font_family_rule}
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
    QLineEdit, QTextEdit, QPlainTextEdit, QListView, QTreeView, QSpinBox {{
        background: {c.surface};
        border: 1px solid {c.border};
        border-radius: {r.sm}px;
        padding: {s.xs}px;
        selection-background-color: {c.selection};
    }}
    QComboBox {{
        background: {c.surface};
        border: 1px solid {c.border};
        border-radius: {r.sm}px;
        /* Extra right padding reserves room for the drop-down arrow - without
           it, uniform padding shrinks the visible text area and Qt's
           sizeHint() doesn't compensate, clipping the current item's text. */
        padding: {s.xs}px {s.lg}px {s.xs}px {s.sm}px;
        selection-background-color: {c.selection};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: {s.lg}px;
        border: none;
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
