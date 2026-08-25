from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.legal.schemas import (
    LegalDocumentAdminResponse,
    LegalDocumentUpsertRequest,
)
from app.core.errors import invalid_legal_document, invalid_legal_locale
from app.models.legal import LegalDocument

SUPPORTED_LOCALES = frozenset({"en", "ar"})
SUPPORTED_DOCUMENTS = frozenset({"terms", "privacy"})


def _row(row: LegalDocument) -> LegalDocumentAdminResponse:
    return LegalDocumentAdminResponse(
        id=row.id,
        document=row.document,
        locale=row.locale,
        title=row.title,
        url=row.url,
        is_published=row.is_published,
        updated_at=row.updated_at,
        created_at=row.created_at,
    )


def _parse_document(document: str) -> str:
    value = document.strip().lower()
    if value not in SUPPORTED_DOCUMENTS:
        raise invalid_legal_document()
    return value


def _parse_locale(locale: str) -> str:
    value = locale.strip().lower()
    if value not in SUPPORTED_LOCALES:
        raise invalid_legal_locale()
    return value


def list_documents(db: Session) -> list[LegalDocumentAdminResponse]:
    rows = (
        db.query(LegalDocument)
        .order_by(LegalDocument.document.asc(), LegalDocument.locale.asc())
        .all()
    )
    return [_row(row) for row in rows]


def upsert_document(
    db: Session,
    *,
    document: str,
    locale: str,
    payload: LegalDocumentUpsertRequest,
    admin: AdminPrincipal,
) -> LegalDocumentAdminResponse:
    doc = _parse_document(document)
    loc = _parse_locale(locale)
    row = (
        db.query(LegalDocument)
        .filter(LegalDocument.document == doc, LegalDocument.locale == loc)
        .one_or_none()
    )
    created = row is None
    if row is None:
        row = LegalDocument(
            document=doc,
            locale=loc,
            title=payload.title.strip(),
            url=payload.url,
            is_published=payload.is_published,
        )
        db.add(row)
        db.flush()
    else:
        row.title = payload.title.strip()
        row.url = payload.url
        row.is_published = payload.is_published

    write_audit(
        db,
        admin_user_id=admin.id,
        action="legal_document.create" if created else "legal_document.update",
        entity_type="legal_documents",
        entity_id=row.id,
        after={
            "document": doc,
            "locale": loc,
            "title": row.title,
            "url": row.url,
            "is_published": row.is_published,
        },
    )
    db.commit()
    db.refresh(row)
    return _row(row)
