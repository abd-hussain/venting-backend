from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.cms.schemas import (
    CmsBannerCreate,
    CmsBannerResponse,
    CmsBannerUpdate,
    CmsPageCreate,
    CmsPageResponse,
    CmsPageUpdate,
)
from app.api.v1.admin.deps import AdminPrincipal
from app.core.errors import conflict, not_found
from app.models.admin import CmsBanner, CmsPage
from app.models.enums import BannerPlacement, CmsPageStatus


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _page(row: CmsPage) -> CmsPageResponse:
    return CmsPageResponse(
        id=row.id,
        slug=row.slug,
        title=row.title,
        locale=row.locale,
        body_markdown=row.body_markdown,
        status=_value(row.status),
        published_at=row.published_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _banner(row: CmsBanner) -> CmsBannerResponse:
    return CmsBannerResponse(
        id=row.id,
        title=row.title,
        body=row.body,
        cta_label=row.cta_label,
        cta_url=row.cta_url,
        placement=_value(row.placement),
        audience=row.audience,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _commit_page(db: Session, row: CmsPage) -> CmsPageResponse:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("A CMS page already exists for this slug and locale") from None
    db.refresh(row)
    return _page(row)


def list_pages(db: Session) -> list[CmsPageResponse]:
    return [
        _page(row)
        for row in db.query(CmsPage).order_by(CmsPage.updated_at.desc()).all()
    ]


def create_page(
    db: Session, payload: CmsPageCreate, admin: AdminPrincipal
) -> CmsPageResponse:
    row = CmsPage(
        **payload.model_dump(),
        status=CmsPageStatus.draft,
        updated_by=admin.id,
    )
    db.add(row)
    return _commit_page(db, row)


def update_page(
    db: Session, page_id: UUID, payload: CmsPageUpdate, admin: AdminPrincipal
) -> CmsPageResponse:
    row = db.get(CmsPage, page_id)
    if row is None:
        raise not_found("CMS page")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, field, value)
    row.updated_by = admin.id
    return _commit_page(db, row)


def publish_page(
    db: Session, page_id: UUID, admin: AdminPrincipal
) -> CmsPageResponse:
    row = db.get(CmsPage, page_id)
    if row is None:
        raise not_found("CMS page")
    before = {
        "status": _value(row.status),
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }
    row.status = CmsPageStatus.published
    row.published_at = datetime.now(timezone.utc)
    row.updated_by = admin.id
    write_audit(
        db,
        admin_user_id=admin.id,
        action="cms_page.publish",
        entity_type="cms_page",
        entity_id=row.id,
        before=before,
        after={"status": "published", "published_at": row.published_at.isoformat()},
    )
    return _commit_page(db, row)


def public_page(db: Session, slug: str, locale: str) -> CmsPageResponse:
    row = (
        db.query(CmsPage)
        .filter(
            CmsPage.slug == slug,
            CmsPage.locale == locale,
            CmsPage.status == CmsPageStatus.published,
        )
        .one_or_none()
    )
    if row is None:
        raise not_found("CMS page")
    return _page(row)


def list_banners(db: Session) -> list[CmsBannerResponse]:
    return [
        _banner(row)
        for row in db.query(CmsBanner).order_by(CmsBanner.created_at.desc()).all()
    ]


def create_banner(db: Session, payload: CmsBannerCreate) -> CmsBannerResponse:
    row = CmsBanner(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _banner(row)


def update_banner(
    db: Session, banner_id: UUID, payload: CmsBannerUpdate
) -> CmsBannerResponse:
    row = db.get(CmsBanner, banner_id)
    if row is None:
        raise not_found("CMS banner")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None or field in {"cta_label", "cta_url", "ends_at"}:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _banner(row)


def deactivate_banner(db: Session, banner_id: UUID) -> CmsBannerResponse:
    row = db.get(CmsBanner, banner_id)
    if row is None:
        raise not_found("CMS banner")
    row.is_active = False
    db.commit()
    db.refresh(row)
    return _banner(row)


def public_banners(
    db: Session, placement: BannerPlacement | None
) -> list[CmsBannerResponse]:
    now = datetime.now(timezone.utc)
    query = db.query(CmsBanner).filter(
        CmsBanner.is_active.is_(True),
        CmsBanner.starts_at <= now,
        or_(CmsBanner.ends_at.is_(None), CmsBanner.ends_at > now),
    )
    if placement is not None:
        query = query.filter(CmsBanner.placement == placement)
    return [_banner(row) for row in query.order_by(CmsBanner.created_at.desc()).all()]
