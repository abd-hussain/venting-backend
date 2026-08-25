import re

from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.help.schemas import (
    HelpDocumentAdminResponse,
    HelpDocumentUpsertRequest,
)
from app.core.errors import invalid_help_locale, invalid_help_topic
from app.models.help import HelpDocument

SUPPORTED_LOCALES = frozenset({"en", "ar"})
TOPIC_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _row(row: HelpDocument) -> HelpDocumentAdminResponse:
    return HelpDocumentAdminResponse(
        id=row.id,
        topic=row.topic,
        locale=row.locale,
        title=row.title,
        url=row.url,
        is_published=row.is_published,
        updated_at=row.updated_at,
        created_at=row.created_at,
    )


def _parse_topic(topic: str) -> str:
    value = topic.strip().lower()
    if not TOPIC_RE.fullmatch(value):
        raise invalid_help_topic()
    return value


def _parse_locale(locale: str) -> str:
    value = locale.strip().lower()
    if value not in SUPPORTED_LOCALES:
        raise invalid_help_locale()
    return value


def list_documents(db: Session) -> list[HelpDocumentAdminResponse]:
    rows = (
        db.query(HelpDocument)
        .order_by(HelpDocument.topic.asc(), HelpDocument.locale.asc())
        .all()
    )
    return [_row(row) for row in rows]


def upsert_document(
    db: Session,
    *,
    topic: str,
    locale: str,
    payload: HelpDocumentUpsertRequest,
    admin: AdminPrincipal,
) -> HelpDocumentAdminResponse:
    topic_key = _parse_topic(topic)
    loc = _parse_locale(locale)
    row = (
        db.query(HelpDocument)
        .filter(HelpDocument.topic == topic_key, HelpDocument.locale == loc)
        .one_or_none()
    )
    created = row is None
    if row is None:
        row = HelpDocument(
            topic=topic_key,
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
        action="help_document.create" if created else "help_document.update",
        entity_type="help_documents",
        entity_id=row.id,
        after={
            "topic": topic_key,
            "locale": loc,
            "title": row.title,
            "url": row.url,
            "is_published": row.is_published,
        },
    )
    db.commit()
    db.refresh(row)
    return _row(row)
