from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.catalogs.schemas import (
    CatalogItemResponse,
    CatalogUpsertRequest,
    ComfortAreaResponse,
    ComfortAreaUpsertRequest,
)
from app.api.v1.admin.deps import AdminPrincipal
from app.models.lookups import Boundary, ComfortArea, Language, LifeExperience

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
    )


def _comfort_item(row: ComfortArea) -> ComfortAreaResponse:
    return ComfortAreaResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        topic_group=row.topic_group,
        is_active=row.is_active,
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


def _upsert(
    db: Session,
    *,
    model: type[CatalogModel],
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
    entity_type: str,
) -> CatalogModel:
    row = db.get(model, item_id)
    before = None
    if row is None:
        row = model(id=item_id)
        db.add(row)
    else:
        before = {
            "name_en": row.name_en,
            "name_ar": row.name_ar,
            "is_active": row.is_active,
        }
    row.name_en = payload.name_en
    row.name_ar = payload.name_ar
    row.is_active = payload.is_active
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type=entity_type,
        entity_id=item_id,
        before=before,
        after={
            "name_en": row.name_en,
            "name_ar": row.name_ar,
            "is_active": row.is_active,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def upsert_language(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
) -> CatalogItemResponse:
    return _item(
        _upsert(
            db,
            model=Language,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="language",
        )
    )


def upsert_life_experience(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
) -> CatalogItemResponse:
    return _item(
        _upsert(
            db,
            model=LifeExperience,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="life_experience",
        )
    )


def upsert_boundary(
    db: Session,
    item_id: str,
    payload: CatalogUpsertRequest,
    admin: AdminPrincipal,
) -> CatalogItemResponse:
    return _item(
        _upsert(
            db,
            model=Boundary,
            item_id=item_id,
            payload=payload,
            admin=admin,
            entity_type="boundary",
        )
    )


def upsert_comfort_area(
    db: Session,
    item_id: str,
    payload: ComfortAreaUpsertRequest,
    admin: AdminPrincipal,
) -> ComfortAreaResponse:
    row = db.get(ComfortArea, item_id)
    before = None
    if row is None:
        row = ComfortArea(id=item_id)
        db.add(row)
    else:
        before = {
            "name_en": row.name_en,
            "name_ar": row.name_ar,
            "topic_group": row.topic_group,
            "is_active": row.is_active,
        }
    row.name_en = payload.name_en
    row.name_ar = payload.name_ar
    row.topic_group = payload.topic_group
    row.is_active = payload.is_active
    write_audit(
        db,
        admin_user_id=admin.id,
        action="catalog.upsert",
        entity_type="comfort_area",
        entity_id=item_id,
        before=before,
        after={
            "name_en": row.name_en,
            "name_ar": row.name_ar,
            "topic_group": row.topic_group,
            "is_active": row.is_active,
        },
    )
    db.commit()
    db.refresh(row)
    return _comfort_item(row)
