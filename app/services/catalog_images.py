"""Catalog category image uploads — stored under static/uploads/catalog/."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import file_too_large, invalid_image_type, validation_error

CATALOG_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
CATALOG_IMAGE_MAX_BYTES = 2 * 1024 * 1024


async def save_catalog_image(
    upload: UploadFile,
    *,
    catalog_type: str,
    item_id: str,
    settings: Settings,
) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in CATALOG_IMAGE_EXTENSIONS:
        raise invalid_image_type()

    content = await upload.read()
    if not content:
        raise validation_error("Uploaded file is empty", ar="الملف المرفوع فارغ")
    if len(content) > CATALOG_IMAGE_MAX_BYTES:
        raise file_too_large()

    filename = f"{uuid.uuid4().hex[:8]}{suffix}"
    dest_dir = Path(settings.upload_dir) / "catalog" / catalog_type / item_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(content)
    return f"/static/{settings.upload_subdir}/catalog/{catalog_type}/{item_id}/{filename}"
