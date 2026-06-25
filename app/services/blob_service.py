"""
app/services/blob_service.py
-----------------------------
Azure Blob Storage operations for item images.

Container: item-images  (public blob read access — URLs are directly servable)

Supported formats
  - JPG / JPEG  (image/jpeg)
  - PNG         (image/png)

Images are stored as:
  {item_id}/{uuid}-{original_filename}

This keeps blobs grouped by item and avoids name collisions when the same
item's image is replaced multiple times.
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
        """Write bytes to blob storage and return the public URL."""
        if len(data) > MAX_BYTES:
            raise ValueError(f"Image exceeds the 8 MB limit ({len(data) // 1024} KB received)")

        blob_name = f"{item_id}/{uuid.uuid4().hex}-{filename}"
        blob_client = self._container.get_blob_client(blob_name)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    def _delete_by_url(self, image_url: str) -> None:
        """Delete a blob given its full URL. Silently ignores 'not found'."""
        # URL format: https://<account>.blob.core.windows.net/<container>/<blob_name>
        try:
            # Everything after the container name is the blob name
            container_prefix = f"/{self.CONTAINER}/"
            blob_name = image_url.split(container_prefix, 1)[-1]
            self._container.delete_blob(blob_name)
        except ResourceNotFoundError:
            logger.warning("Blob not found when trying to delete: %s", image_url)

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_file(self, item_id: str, file_bytes: bytes, filename: str) -> str:
        """
        Upload raw file bytes (from a multipart form upload).
        Returns the public blob URL.
        """
        _validate_extension(filename)
        content_type = _content_type_from_filename(filename)
        return self._upload(item_id, file_bytes, filename, content_type)

    def upload_base64(self, item_id: str, b64_string: str, filename: str) -> str:
        """
        Decode a base64 string and upload the resulting bytes.
        Auto-detects JPEG vs PNG from magic bytes.
        Returns the public blob URL.
        """
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

    def delete_image(self, image_url: str) -> None:
        """Remove a blob by its public URL."""
        self._delete_by_url(image_url)


# ── Module-level singleton ────────────────────────────────────────────────────

_blob_service: Optional[BlobService] = None


def get_blob_service() -> BlobService:
    """Dependency-injection factory — builds the BlobServiceClient once."""
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobService()
    return _blob_service
