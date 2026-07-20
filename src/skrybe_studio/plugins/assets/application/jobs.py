"""Background job: copy a source file into the managed assets directory, hash it,
and generate a thumbnail - entirely off the Qt main thread.

`QImage` (unlike `QPixmap`) is safe to load, scale, and save from a
worker thread, so thumbnailing happens here rather than after the result
is marshaled back to the main thread.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from skrybe_studio.core.jobs.job import CancellationToken, Job

THUMBNAIL_SIZE = 160
_READ_CHUNK_SIZE = 65536


@dataclass(frozen=True, slots=True)
class AssetImportResult:
    asset_id: UUID
    stored_path: Path
    content_hash: str
    size_bytes: int
    thumbnail_path: Path | None


class AssetImportJob(Job):
    def __init__(
        self,
        asset_id: UUID,
        source_path: Path,
        assets_dir: Path,
        cache_dir: Path,
        stored_filename: str,
    ) -> None:
        self._asset_id = asset_id
        self._source_path = source_path
        self._assets_dir = assets_dir
        self._cache_dir = cache_dir
        self._stored_filename = stored_filename

    def run(self, cancellation_token: CancellationToken) -> AssetImportResult:
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self._assets_dir / self._stored_filename

        cancellation_token.raise_if_cancelled()
        shutil.copy2(self._source_path, stored_path)

        cancellation_token.raise_if_cancelled()
        content_hash = _hash_file(stored_path)

        thumbnail_path = self._generate_thumbnail(stored_path)

        return AssetImportResult(
            asset_id=self._asset_id,
            stored_path=stored_path,
            content_hash=content_hash,
            size_bytes=stored_path.stat().st_size,
            thumbnail_path=thumbnail_path,
        )

    def _generate_thumbnail(self, stored_path: Path) -> Path | None:
        image = QImage(str(stored_path))
        if image.isNull():
            return None
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = self._cache_dir / f"{self._asset_id}.png"
        scaled = image.scaled(
            THUMBNAIL_SIZE,
            THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if not scaled.save(str(thumbnail_path)):
            return None
        return thumbnail_path


def _hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
