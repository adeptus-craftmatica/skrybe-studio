"""A minimal JSON-file-backed key/value settings store.

Secrets must never be stored here. When secure credential storage is
introduced, it will be a separate store behind the same narrow
`get`/`set` shape so callers do not need to change.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SENTINEL = object()


class JsonSettingsStore:
    """Thread-safe, dotted-key JSON settings store backed by a single file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load settings from %s; starting empty", self._path)
            self._data = {}

    def save(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8"
            )

    def get(self, key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
        if save:
            self.save()

    def unset(self, key: str, *, save: bool = True) -> None:
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                if not isinstance(node, dict) or part not in node:
                    return
                node = node[part]
            node.pop(parts[-1], _SENTINEL)
        if save:
            self.save()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
