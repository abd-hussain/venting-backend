"""Listener notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.core.pagination import clamp_page
from app.models.notifications import Notification
from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    body: str
    created_at: str
    is_read: bool


class NotificationsResponse(BaseModel):
    items: list[NotificationItem]
    total: int = 0
    page: int = 1
    page_size: int = 20


class OkCountResponse(BaseModel):
    ok: bool = True
    updated_count: int | None = None


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def list_notifications(
    db: Session,
    user_id: UUID,
    *,
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> NotificationsResponse:
    page, page_size = clamp_page(page, page_size)
    query = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.deleted_at.is_(None),
    )
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    total = query.with_entities(func.count(Notification.id)).scalar() or 0
    rows = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return NotificationsResponse(
        items=[
            NotificationItem(
                id=str(r.id),
                type=r.type.value,
                title=r.title,
                body=r.body,
                created_at=_iso(r.created_at),
                is_read=r.is_read,
            )
            for r in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def mark_all_read(db: Session, user_id: UUID) -> OkCountResponse:
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.deleted_at.is_(None),
            Notification.is_read.is_(False),
        )
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return OkCountResponse(ok=True, updated_count=int(count))


def delete_notification(db: Session, user_id: UUID, notification_id: UUID) -> OkCountResponse:
    row = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if row is None:
        raise not_found("Notification")
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return OkCountResponse(ok=True)
