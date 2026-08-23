from __future__ import annotations

from typing import TypeVar

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.catalogs.schemas import (
    CatalogItemResponse,
    CatalogUpsertRequest,
    ComfortAreaResponse,
    ComfortAreaUpsertRequest,
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


def _item(row: Language | LifeExperience | Boundary) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        is_active=row.is_active,
        image_url=row.image_url,
    )


def _comfort_item(row: ComfortArea) -> ComfortAreaResponse:
    return ComfortAreaResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        topic_group=row.topic_group,
        is_active=row.is_active,
        image_url=row.image_url,
    )


def list_languages(db: Session) -> list[CatalogItemResponse]:
    return [_item(row) for row in db.query(Language).order_by(Language.id).all()]


def list_comfort_areas(db: Session) -> list[ComfortAreaResponse]:
    return [
        _comfort_item(row)
        for row in db.query(ComfortArea).order_by(ComfortArea.id).all()
    ]


def list_life_experiences(db: Session) -> list[CatalogItemResponse]:
    return [
        _item(row)
        for row in db.query(LifeExperience).order_by(LifeExperience.id).all()
    ]


def list_boundaries(db: Session) -> list[CatalogItemResponse]:
    return [_item(row) for row in db.query(Boundary).order_by(Boundary.id).all()]


def _audit_snapshot(row: CatalogModel) -> dict[str, object]:
    data: dict[str, object] = {
        "name_en": row.name_en,
        "name_ar": row.name_ar,
        "is_active": row.is_active,
        "image_url": row.image_url,
    }
    if isinstance(row, ComfortArea):
        data["topic_group"] = row.topic_group
    return data


async def _apply_image(
    *,
    row: CatalogModel,
    is_new: bool,
    image: UploadFile | None,
    catalog_type: str,
    settings: Settings,
) -> None:
    if image is not None:
        row.image_url = await save_catalog_image(
            image,
            catalog_type=catalog_type,
            item_id=row.id,
            settings=settings,
        )
        return
    if is_new and not row.image_url:
        raise image_required()


async def _upsert(
    db: Session,
    *,
    model: type[CatalogModel],
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    entity_type: str,
    catalog_type: str,
    image: UploadFile | None,
    settings: Settings,
) -> CatalogModel:
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
    await _apply_image(
        row=row,
        is_new=is_new,
        image=image,
        catalog_type=catalog_type,
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


async def upsert_language(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> CatalogItemResponse:
    return _item(
        await _upsert(
            db,
            model=Language,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="language",
            catalog_type="languages",
            image=image,
            settings=settings,
        )
    )


async def upsert_life_experience(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> CatalogItemResponse:
    return _item(
        await _upsert(
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


async def upsert_boundary(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    *,
    image: UploadFile | None,
    settings: Settings,
) -> CatalogItemResponse:
    return _item(
        await _upsert(
            db,
            model=Boundary,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="boundary",
            catalog_type="boundaries",
            image=image,
            settings=settings,
        )
    )


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
    row.is_active = payload.is_active
    await _apply_image(
        row=row,
        is_new=is_new,
        image=image,
        catalog_type="comfort_areas",
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
