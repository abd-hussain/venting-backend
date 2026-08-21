"""Business logic for admin audit-log and note APIs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.notes.schemas import (
    AdminNoteCreateRequest,
    AdminNoteItem,
    AdminNoteList,
    AdminNoteUpdateRequest,
    AuditLogItem,
    AuditLogList,
)
from app.core.errors import not_found
from app.core.pagination import clamp_page
from app.models.admin import AdminAuditLog, AdminNote


def _note_item(row: AdminNote) -> AdminNoteItem:
    return AdminNoteItem(
        id=str(row.id),
        admin_user_id=str(row.admin_user_id),
        entity_type=row.entity_type,
        entity_id=str(row.entity_id),
        body=row.body,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_audit_logs(
    db: Session,
    *,
    admin_user_id: UUID | None,
    entity_type: str | None,
    entity_id: str | None,
    from_at: datetime | None,
    to_at: datetime | None,
    page: int,
) -> AuditLogList:
    page, page_size = clamp_page(page)
    query = db.query(AdminAuditLog)
    if admin_user_id is not None:
        query = query.filter(AdminAuditLog.admin_user_id == admin_user_id)
    if entity_type is not None:
        query = query.filter(AdminAuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AdminAuditLog.entity_id == entity_id)
    if from_at is not None:
        query = query.filter(AdminAuditLog.created_at >= from_at)
    if to_at is not None:
        query = query.filter(AdminAuditLog.created_at <= to_at)

    total = query.count()
    rows = (
        query.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogList(
        items=[
            AuditLogItem(
                id=str(row.id),
                admin_user_id=str(row.admin_user_id),
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                before=row.before,
                after=row.after,
                ip=str(row.ip) if row.ip is not None else None,
                user_agent=row.user_agent,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_notes(
    db: Session, *, entity_type: str, entity_id: UUID, page: int
) -> AdminNoteList:
    page, page_size = clamp_page(page)
    query = db.query(AdminNote).filter(
        AdminNote.entity_type == entity_type,
        AdminNote.entity_id == entity_id,
    )
    total = query.count()
    rows = (
        query.order_by(AdminNote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminNoteList(
        items=[_note_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_note(
    db: Session,
    admin: AdminPrincipal,
    payload: AdminNoteCreateRequest,
) -> AdminNoteItem:
    row = AdminNote(
        admin_user_id=admin.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        body=payload.body,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="note.create",
        entity_type="admin_note",
        entity_id=row.id,
        after={
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id),
            "body": row.body,
        },
    )
    db.commit()
    db.refresh(row)
    return _note_item(row)


def update_note(
    db: Session,
    admin: AdminPrincipal,
    note_id: UUID,
    payload: AdminNoteUpdateRequest,
) -> AdminNoteItem:
    row = db.query(AdminNote).filter(AdminNote.id == note_id).one_or_none()
    if row is None:
        raise not_found("Note")
    before = {"body": row.body}
    row.body = payload.body
    write_audit(
        db,
        admin_user_id=admin.id,
        action="note.update",
        entity_type="admin_note",
        entity_id=row.id,
        before=before,
        after={"body": row.body},
    )
    db.commit()
    db.refresh(row)
    return _note_item(row)
