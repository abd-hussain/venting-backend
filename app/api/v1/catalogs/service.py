from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.catalogs.schemas import (
    CatalogBundleResponse,
    CatalogItemResponse,
    CategoryResponse,
    ComfortAreaResponse,
    LanguageResponse,
)
from app.core.errors import invalid_catalog_audience, validation_error
from app.models.lookups import Boundary, ComfortArea, Language, LifeExperience

VALID_CATEGORY_AUDIENCES = {"ventor", "listener", "all"}


def _item(row: LifeExperience | Boundary) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        image_url=row.image_url,
    )


def _language_item(row: Language) -> LanguageResponse:
    return LanguageResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        sort_order=row.sort_order,
        image_url=row.image_url,
    )


def _comfort_item(row: ComfortArea) -> ComfortAreaResponse:
    return ComfortAreaResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        topic_group=row.topic_group,
        image_url=row.image_url,
        icon_key=row.icon_key,
        sort_order=row.sort_order,
        allows_custom_text=row.allows_custom_text,
        audience=row.audience,
    )


def _category_item(row: ComfortArea) -> CategoryResponse:
    return CategoryResponse(
        id=row.id,
        name_en=row.name_en,
        name_ar=row.name_ar,
        icon_key=row.icon_key,
        sort_order=row.sort_order,
        allows_custom_text=row.allows_custom_text,
        topic_group=row.topic_group,
    )


def list_languages(db: Session) -> list[LanguageResponse]:
    rows = (
        db.query(Language)
        .filter(Language.is_active.is_(True))
        .order_by(Language.sort_order, Language.id)
        .all()
    )
    return [_language_item(row) for row in rows]


def assert_active_language(db: Session, language_id: str) -> Language:
    """Validate a speaking-language id against the languages catalog."""
    row = (
        db.query(Language)
        .filter(Language.id == language_id, Language.is_active.is_(True))
        .one_or_none()
    )
    if row is None:
        raise validation_error(
            f"Unknown speech language: {language_id}",
            ar="لغة التحدث غير معروفة",
        )
    return row


def list_comfort_areas(db: Session) -> list[ComfortAreaResponse]:
    rows = (
        db.query(ComfortArea)
        .filter(ComfortArea.is_active.is_(True))
        .order_by(ComfortArea.sort_order, ComfortArea.id)
        .all()
    )
    return [_comfort_item(row) for row in rows]


def list_categories(db: Session, *, audience: str = "all") -> list[CategoryResponse]:
    if audience not in VALID_CATEGORY_AUDIENCES:
        raise invalid_catalog_audience()

    query = db.query(ComfortArea).filter(ComfortArea.is_active.is_(True))
    if audience != "all":
        query = query.filter(
            or_(ComfortArea.audience == audience, ComfortArea.audience == "all")
        )

    rows = query.order_by(ComfortArea.sort_order, ComfortArea.id).all()
    return [_category_item(row) for row in rows]


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
