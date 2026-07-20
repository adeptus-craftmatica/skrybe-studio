# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Skrybe Studio.

Built via `release.py` or CI (`.github/workflows/release.yml`), never run
directly by end users. Produces a onedir bundle per platform:
  macOS   -> dist/SkrybeStudio.app  (wrapped into a .dmg by release.py/CI)
  Windows -> dist/SkrybeStudio/     (zipped by release.py/CI)
  Linux   -> dist/SkrybeStudio/     (tarred by release.py/CI)
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)
SRC = ROOT / "src"

block_cipher = None


def _find_modules(root: Path) -> list[str]:
    """Dotted module names for every .py file under `root`.

    Walking the tree ourselves (rather than `collect_submodules`, which
    requires the package to already be importable on the build machine)
    is what catches the plugin entrypoints - `skrybe_studio.plugins.*.plugin`
    is only ever reached via `importlib.import_module()` at runtime, so
    PyInstaller's static analysis can't discover it on its own.
    """
    modules = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".py"):
                rel = Path(dirpath).relative_to(root.parent)
                mod = str(rel / fname[:-3]).replace(os.sep, ".").replace("/", ".")
                modules.append(mod)
    return modules


_hidden_modules = _find_modules(SRC / "skrybe_studio")

a = Analysis(
    [str(SRC / "skrybe_studio" / "app" / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # Plugin packages - physically present so the plugin loader can walk
        # each plugin directory's manifest.json at runtime.
        (str(SRC / "skrybe_studio" / "plugins"), "skrybe_studio/plugins"),
    ],
    hiddenimports=[
        *_hidden_modules,
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "sqlalchemy.dialects.sqlite",
        "sqlite3",
        "_sqlite3",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SkrybeStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # TODO(icon): no brand icon assets exist yet - add icon.icns/icon.ico
    # under a resources/ directory and reference them here once available.
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SkrybeStudio",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SkrybeStudio.app",
        icon=None,
        bundle_identifier="com.adeptus-craftmatica.skrybestudio",
        info_plist={
            "CFBundleName": "Skrybe Studio",
            "CFBundleDisplayName": "Skrybe Studio",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
