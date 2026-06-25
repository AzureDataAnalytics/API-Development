"""
app/services/blob_service.py
-----------------------------
Azure Blob Storage operations for item images.

Container: item-images  (private — no public internet access)

Images are never served directly from blob storage. The API proxies all reads
through GET /{item_id}/image so access control stays in the application layer.

Blob paths are stored in the Cosmos document's `imageUrl` field in the form:
  {item_id}/{uuid}-{original_filename}

Supported formats
  - JPG / JPEG  (image/jpeg)
  - PNG         (image/png)
"""
from __future__ import annotations

import base64
import logging
import uuid
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_BYTES = 8 * 1024 * 1024  # 8 MB hard limit


def _content_type_from_filename(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    return "image/png" if ext == "png" else "image/jpeg"


def _content_type_from_magic(data: bytes) -> str:
    """Detect image type from leading bytes so base64 payloads are self-describing."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    raise ValueError("Unsupported image format — only JPEG and PNG are accepted")


def _validate_extension(filename: str) -> None:
    ext = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' not allowed. Use .jpg, .jpeg, or .png")


class BlobService:
    """Upload, replace and delete item images in Azure Blob Storage."""

    CONTAINER = "item-images"

    def __init__(self) -> None:
        settings = get_settings()
        client = BlobServiceClient.from_connection_string(settings.storage_connection_string)
        self._container = client.get_container_client(settings.storage_image_container)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _upload(self, item_id: str, data: bytes, filename: str, content_type: str) -> str:
        """Write bytes to blob storage and return the internal blob path."""
        if len(data) > MAX_BYTES:
            raise ValueError(f"Image exceeds the 8 MB limit ({len(data) // 1024} KB received)")

        blob_name = f"{item_id}/{uuid.uuid4().hex}-{filename}"
        blob_client = self._container.get_blob_client(blob_name)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_name  # internal path, never exposed directly to callers

    def _resolve_blob_path(self, stored_value: str) -> str:
        """Normalise legacy full URLs to bare blob paths."""
        if stored_value.startswith("https://"):
            # Legacy documents stored the full public URL — extract the path portion.
            return stored_value.split(f"/{self.CONTAINER}/", 1)[-1]
        return stored_value

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_file(self, item_id: str, file_bytes: bytes, filename: str) -> str:
        """Upload raw bytes and return the internal blob path."""
        _validate_extension(filename)
        content_type = _content_type_from_filename(filename)
        return self._upload(item_id, file_bytes, filename, content_type)

    def upload_base64(self, item_id: str, b64_string: str, filename: str) -> str:
        """Decode a base64 payload, upload, and return the internal blob path."""
        _validate_extension(filename)
        # Strip a data-URI prefix if the caller included one (e.g. "data:image/png;base64,")
        if "," in b64_string and b64_string.startswith("data:"):
            b64_string = b64_string.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(b64_string)
        except Exception as exc:
            raise ValueError(f"Invalid base64 string: {exc}") from exc

        content_type = _content_type_from_magic(image_bytes)
        return self._upload(item_id, image_bytes, filename, content_type)

    def download_image(self, blob_path: str) -> tuple[bytes, str]:
        """
        Stream blob bytes through the application so they never touch a public URL.
        Returns (image_bytes, content_type).
        Raises FileNotFoundError when the blob does not exist.
        """
        blob_path = self._resolve_blob_path(blob_path)
        blob_client = self._container.get_blob_client(blob_path)
        try:
            downloader = blob_client.download_blob()
            content_type = (
                downloader.properties.content_settings.content_type or "image/jpeg"
            )
            return downloader.readall(), content_type
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Image blob not found: {blob_path}")

    def delete_image(self, blob_path: str) -> None:
        """Remove a blob by its internal path (or legacy full URL)."""
        blob_path = self._resolve_blob_path(blob_path)
        try:
            self._container.delete_blob(blob_path)
        except ResourceNotFoundError:
            logger.warning("Blob not found when deleting: %s", blob_path)


# ── Module-level singleton ────────────────────────────────────────────────────

_blob_service: Optional[BlobService] = None


def get_blob_service() -> BlobService:
    """Dependency-injection factory — builds the BlobServiceClient once."""
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobService()
    return _blob_service
