"""
Storage service — abstract file I/O with a local filesystem implementation.

Files are stored as {uuid}.pdf under {root}/{year}/{month}/.
The original filename is NEVER used on disk — only the UUID path.
"""
from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
import aiofiles.os

from app.core.exceptions import FileNotFoundInStorageError, StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AbstractStorageService(ABC):
    @abstractmethod
    async def save(self, file_id: uuid.UUID, content: bytes) -> str:
        """Persist file bytes and return the storage path."""

    @abstractmethod
    async def load(self, path: str) -> bytes:
        """Load file bytes from the given storage path."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Remove a file from storage."""

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class LocalStorageService(AbstractStorageService):
    """Stores files on the local filesystem inside a Docker volume."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _build_path(self, file_id: uuid.UUID) -> Path:
        now = datetime.now(UTC)
        return self._root / str(now.year) / f"{now.month:02d}" / f"{file_id}.pdf"

    async def save(self, file_id: uuid.UUID, content: bytes) -> str:
        path = self._build_path(file_id)
        try:
            await aiofiles.os.makedirs(str(path.parent), exist_ok=True)
            async with aiofiles.open(str(path), "wb") as f:
                await f.write(content)
            logger.info("file_saved", path=str(path), size=len(content))
            return str(path)
        except OSError as exc:
            raise StorageError(f"Failed to save file {file_id}: {exc}") from exc

    async def load(self, path: str) -> bytes:
        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except FileNotFoundError:
            raise FileNotFoundInStorageError(path)
        except OSError as exc:
            raise StorageError(f"Failed to load file {path}: {exc}") from exc

    async def delete(self, path: str) -> None:
        try:
            await aiofiles.os.remove(path)
            logger.info("file_deleted", path=path)
        except FileNotFoundError:
            pass  # Idempotent delete
        except OSError as exc:
            raise StorageError(f"Failed to delete file {path}: {exc}") from exc
