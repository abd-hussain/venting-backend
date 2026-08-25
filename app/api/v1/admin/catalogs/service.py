from __future__ import annotations

from typing import TypeVar

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.catalogs.schemas import (
    BoundaryResponse,
    BoundaryUpsertRequest,
    CatalogItemResponse,
    CatalogUpsertRequest,
    ComfortAreaResponse,
    ComfortAreaUpsertRequest,
    LanguageResponse,
    LanguageUpsertRequest,
    LifeExperienceUpsertRequest,
)
from app.api.v1.admin.deps import AdminPrincipal
from app.core.config import Settings
from app.core.errors import image_required
from app.models.lookups import Boundary, ComfortArea, Language, LifeExperience
from app.services.catalog_images import save_catalog_image

CatalogModel = TypeVar(
    "CatalogModel",
    Language,
    ComfortArea,
    LifeExperience,
    Boundary,
)


def _item(row: LifeExperience) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        is_active=row.is_active,
        image_url=row.image_url,
        sort_order=row.sort_order,
    )


def _boundary_icon_url(row: Boundary) -> str | None:
    return row.icon_url or row.image_url


def _boundary_item(row: Boundary) -> BoundaryResponse:
    return BoundaryResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        icon_emoji=row.icon_emoji,
        icon_url=_boundary_icon_url(row),
        sort_order=row.sort_order,
        allows_custom_text=row.allows_custom_text,
        is_active=row.is_active,
    )


def _language_item(row: Language) -> LanguageResponse:
    return LanguageResponse(
        id=row.id,
        name_en=row.name_en,
        name_native=row.name_native,
        name_ar=row.name_ar,
        flag_url=row.flag_url,
        flag_emoji=row.flag_emoji,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


def _comfort_item(row: ComfortArea) -> ComfortAreaResponse:
    return ComfortAreaResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        icon_emoji=row.icon_emoji,
        icon_url=row.icon_url,
        topic_group=row.topic_group,
        is_active=row.is_active,
        sort_order=row.sort_order,
        allows_custom_text=row.allows_custom_text,
        audience=row.audience,
    )


def list_languages(db: Session) -> list[LanguageResponse]:
    return [
        _language_item(row)
        for row in db.query(Language).order_by(Language.sort_order, Language.id).all()
    ]


def list_comfort_areas(db: Session) -> list[ComfortAreaResponse]:
    return [
        _comfort_item(row)
        for row in db.query(ComfortArea)
        .order_by(ComfortArea.sort_order, ComfortArea.id)
        .all()
    ]


def list_life_experiences(db: Session) -> list[CatalogItemResponse]:
    return [
        _item(row)
        for row in db.query(LifeExperience)
        .order_by(LifeExperience.sort_order, LifeExperience.id)
        .all()
    ]


def list_boundaries(db: Session) -> list[BoundaryResponse]:
    return [
        _boundary_item(row)
        for row in db.query(Boundary)
        .order_by(Boundary.sort_order, Boundary.id)
        .all()
    ]


def _audit_snapshot(row: CatalogModel) -> dict[str, object]:
    data: dict[str, object] = {
        "name_en": row.name_en,
        "name_ar": row.name_ar,
        "is_active": row.is_active,
    }
    if isinstance(row, Language):
        data.update(
            {
                "name_native": row.name_native,
                "flag_url": row.flag_url,
                "flag_emoji": row.flag_emoji,
                "sort_order": row.sort_order,
            }
        )
    elif isinstance(row, ComfortArea):
        data.update(
            {
                "icon_emoji": row.icon_emoji,
                "icon_url": row.icon_url,
                "topic_group": row.topic_group,
                "sort_order": row.sort_order,
                "allows_custom_text": row.allows_custom_text,
                "audience": row.audience,
            }
        )
    elif isinstance(row, LifeExperience):
        data.update(
            {
                "image_url": row.image_url,
                "sort_order": row.sort_order,
            }
        )
    elif isinstance(row, Boundary):
        data.update(
            {
                "icon_emoji": row.icon_emoji,
                "icon_url": _boundary_icon_url(row),
                "sort_order": row.sort_order,
                "allows_custom_text": row.allows_custom_text,
            }
        )
    else:
        data["image_url"] = row.image_url
    return data


async def _apply_image_field(
    *,
    current_url: str | None,
    is_new: bool,
    image: UploadFile | None,
    catalog_type: str,
    item_id: str,
    settings: Settings,
) -> str:
    if image is not None:
        return await save_catalog_image(
            image,
            catalog_type=catalog_type,
            item_id=item_id,
            settings=settings,
        )
    if is_new and not current_url:
        raise image_required()
    return current_url or ""


async def _upsert_tagged(
    db: Session,
    *,
    model: type[LifeExperience],
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    entity_type: str,
    catalog_type: str,
    image: UploadFile | None,
    settings: Settings,
) -> LifeExperience:
    row = db.get(model, item_id)
    is_new = row is None
    before = None
    if is_new:
        row = model(id=item_id)
        db.add(row)
    else:
        before = _audit_snapshot(row)
    row.name_en = payload.name_en
    row.name_ar = payload.name_ar
    row.is_active = payload.is_active
    if isinstance(payload, LifeExperienceUpsertRequest) and hasattr(row, "sort_order"):
        row.sort_order = payload.sort_order
    row.image_url = await _apply_image_field(
        current_url=row.image_url,
        is_new=is_new,
        image=image,
        catalog_type=catalog_type,
        item_id=item_id,
        settings=settings,
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type=entity_type,
        entity_id=item_id,
        before=before,
        after=_audit_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return row


async def upsert_life_experience(
    db: Session,
    item_id: str,
    payload: LifeExperienceUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> CatalogItemResponse:
    return _item(
        await _upsert_tagged(
            db,
            model=LifeExperience,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="life_experience",
            catalog_type="life_experiences",
            image=image,
            settings=settings,
        )
    )


async def upsert_language(
    db: Session,
    item_id: str,
    payload: LanguageUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> LanguageResponse:
    row = db.get(Language, item_id)
    is_new = row is None
    before = None
    if is_new:
        row = Language(id=item_id, name_native=payload.name_native)
        db.add(row)
    else:
        before = _audit_snapshot(row)
    row.name_en = payload.name_en
    row.name_native = payload.name_native
    row.name_ar = payload.name_ar
    row.flag_emoji = payload.flag_emoji
    row.sort_order = payload.sort_order
    row.is_active = payload.is_active
    row.flag_url = await _apply_image_field(
        current_url=row.flag_url,
        is_new=is_new,
        image=image,
        catalog_type="languages",
        item_id=item_id,
        settings=settings,
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type="language",
        entity_id=item_id,
        before=before,
        after=_audit_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _language_item(row)


async def upsert_boundary(
    db: Session,
    item_id: str,
    payload: BoundaryUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> BoundaryResponse:
    row = db.get(Boundary, item_id)
    is_new = row is None
    before = None
    if is_new:
        row = Boundary(id=item_id)
        db.add(row)
    else:
        before = _audit_snapshot(row)
    row.name_en = payload.name_en
    row.name_ar = payload.name_ar
    row.icon_emoji = payload.icon_emoji
    row.sort_order = payload.sort_order
    row.allows_custom_text = payload.allows_custom_text
    row.is_active = payload.is_active
    if image is not None:
        row.icon_url = await save_catalog_image(
            image,
            catalog_type="boundaries",
            item_id=item_id,
            settings=settings,
        )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type="boundary",
        entity_id=item_id,
        before=before,
        after=_audit_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _boundary_item(row)


async def upsert_comfort_area(
    db: Session,
    item_id: str,
    payload: ComfortAreaUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> ComfortAreaResponse:
    row = db.get(ComfortArea, item_id)
    is_new = row is None
    before = None
    if is_new:
        row = ComfortArea(id=item_id)
        db.add(row)
    else:
        before = _audit_snapshot(row)
    row.name_en = payload.name_en
    row.name_ar = payload.name_ar
    row.topic_group = payload.topic_group
    row.icon_emoji = payload.icon_emoji
    row.sort_order = payload.sort_order
    row.allows_custom_text = payload.allows_custom_text
    row.audience = payload.audience
    row.is_active = payload.is_active
    # Image upload is optional for comfort areas (emoji is the primary icon).
    if image is not None:
        row.icon_url = await save_catalog_image(
            image,
            catalog_type="comfort_areas",
            item_id=item_id,
            settings=settings,
        )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type="comfort_area",
        entity_id=item_id,
        before=before,
        after=_audit_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _comfort_item(row)
