from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.v1.catalogs.schemas import (
    CatalogBundleResponse,
    CatalogItemResponse,
    ComfortAreaResponse,
)
from app.models.lookups import Boundary, ComfortArea, Language, LifeExperience


def _item(row: Language | LifeExperience | Boundary) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        image_url=row.image_url,
    )


def _comfort_item(row: ComfortArea) -> ComfortAreaResponse:
    return ComfortAreaResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        topic_group=row.topic_group,
        image_url=row.image_url,
    )


def list_languages(db: Session) -> list[CatalogItemResponse]:
    rows = (
        db.query(Language)
        .filter(Language.is_active.is_(True))
        .order_by(Language.id)
        .all()
    )
    return [_item(row) for row in rows]


def list_comfort_areas(db: Session) -> list[ComfortAreaResponse]:
    rows = (
        db.query(ComfortArea)
        .filter(ComfortArea.is_active.is_(True))
        .order_by(ComfortArea.id)
        .all()
    )
    return [_comfort_item(row) for row in rows]


def list_life_experiences(db: Session) -> list[CatalogItemResponse]:
    rows = (
        db.query(LifeExperience)
        .filter(LifeExperience.is_active.is_(True))
        .order_by(LifeExperience.id)
        .all()
    )
    return [_item(row) for row in rows]


def list_boundaries(db: Session) -> list[CatalogItemResponse]:
    rows = (
        db.query(Boundary)
        .filter(Boundary.is_active.is_(True))
        .order_by(Boundary.id)
        .all()
    )
    return [_item(row) for row in rows]


def list_all_catalogs(db: Session) -> CatalogBundleResponse:
    return CatalogBundleResponse(
        languages=list_languages(db),
        comfort_areas=list_comfort_areas(db),
        life_experiences=list_life_experiences(db),
        boundaries=list_boundaries(db),
    )
