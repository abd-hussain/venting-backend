from __future__ import annotations

import re
from typing import Any

from fastapi import Request, UploadFile
from pydantic import ValidationError

from app.api.v1.admin.catalogs.schemas import (
    CatalogUpsertRequest,
    BoundaryUpsertRequest,
    ComfortAreaUpsertRequest,
    LanguageUpsertRequest,
    LifeExperienceUpsertRequest,
)
from app.core.errors import validation_error

_CATALOG_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_catalog_id(item_id: str, *, max_length: int = 64) -> None:
    if not item_id or len(item_id) > max_length or not _CATALOG_ID_RE.match(item_id):
        raise validation_error(
            "Invalid catalog id slug",
            en="Invalid catalog id slug",
            ar="معرّف الفئة غير صالح",
        )


def _parse_bool(value: Any, *, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return default


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def parse_catalog_upsert(
    request: Request,
) -> tuple[CatalogUpsertRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image = form.get("image")
        upload: UploadFile | None = None
        if isinstance(image, UploadFile) and image.filename:
            upload = image
        try:
            payload = CatalogUpsertRequest(
                name_en=str(form.get("name_en", "")),
                name_ar=str(form.get("name_ar", "")),
                is_active=_parse_bool(form.get("is_active")),
            )
        except ValidationError as exc:
            raise validation_error(str(exc.errors()[0]["msg"])) from exc
        return payload, upload

    try:
        payload = CatalogUpsertRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise validation_error(str(exc.errors()[0]["msg"])) from exc
    return payload, None


async def parse_life_experience_upsert(
    request: Request,
) -> tuple[LifeExperienceUpsertRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image = form.get("image")
        upload: UploadFile | None = None
        if isinstance(image, UploadFile) and image.filename:
            upload = image
        try:
            payload = LifeExperienceUpsertRequest(
                name_en=str(form.get("name_en", "")),
                name_ar=str(form.get("name_ar", "")),
                sort_order=int(form.get("sort_order") or 0),
                is_active=_parse_bool(form.get("is_active")),
            )
        except ValidationError as exc:
            raise validation_error(str(exc.errors()[0]["msg"])) from exc
        return payload, upload

    try:
        payload = LifeExperienceUpsertRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise validation_error(str(exc.errors()[0]["msg"])) from exc
    return payload, None


async def parse_language_upsert(
    request: Request,
) -> tuple[LanguageUpsertRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image = form.get("image")
        upload: UploadFile | None = None
        if isinstance(image, UploadFile) and image.filename:
            upload = image
        try:
            payload = LanguageUpsertRequest(
                name_en=str(form.get("name_en", "")),
                name_native=str(form.get("name_native") or form.get("name_en") or ""),
                name_ar=str(form.get("name_ar", "")),
                flag_emoji=_optional_str(form.get("flag_emoji")),
                sort_order=int(form.get("sort_order") or 0),
                is_active=_parse_bool(form.get("is_active")),
            )
        except ValidationError as exc:
            raise validation_error(str(exc.errors()[0]["msg"])) from exc
        return payload, upload

    try:
        payload = LanguageUpsertRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise validation_error(str(exc.errors()[0]["msg"])) from exc
    return payload, None


async def parse_comfort_area_upsert(
    request: Request,
) -> tuple[ComfortAreaUpsertRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image = form.get("image")
        upload: UploadFile | None = None
        if isinstance(image, UploadFile) and image.filename:
            upload = image
        try:
            payload = ComfortAreaUpsertRequest(
                name_en=str(form.get("name_en", "")),
                name_ar=str(form.get("name_ar", "")),
                topic_group=_optional_str(form.get("topic_group")),
                icon_emoji=str(form.get("icon_emoji") or "📌"),
                sort_order=int(form.get("sort_order") or 0),
                allows_custom_text=_parse_bool(
                    form.get("allows_custom_text"), default=False
                ),
                audience=str(form.get("audience") or "all"),
                is_active=_parse_bool(form.get("is_active")),
            )
        except ValidationError as exc:
            raise validation_error(str(exc.errors()[0]["msg"])) from exc
        return payload, upload

    try:
        payload = ComfortAreaUpsertRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise validation_error(str(exc.errors()[0]["msg"])) from exc
    return payload, None


async def parse_boundary_upsert(
    request: Request,
) -> tuple[BoundaryUpsertRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image = form.get("image")
        upload: UploadFile | None = None
        if isinstance(image, UploadFile) and image.filename:
            upload = image
        try:
            payload = BoundaryUpsertRequest(
                name_en=str(form.get("name_en", "")),
                name_ar=str(form.get("name_ar", "")),
                icon_emoji=str(form.get("icon_emoji") or "🛡️"),
                sort_order=int(form.get("sort_order") or 0),
                allows_custom_text=_parse_bool(
                    form.get("allows_custom_text"), default=False
                ),
                is_active=_parse_bool(form.get("is_active")),
            )
        except ValidationError as exc:
            raise validation_error(str(exc.errors()[0]["msg"])) from exc
        return payload, upload

    try:
        payload = BoundaryUpsertRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise validation_error(str(exc.errors()[0]["msg"])) from exc
    return payload, None
