from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.notifications.schemas import (
    BroadcastRequest,
    BroadcastResponse,
    NotificationMessage,
    NotificationResponse,
)
from app.core.errors import not_found
from app.core.pagination import Paginated, clamp_page
from app.models.auth import User
from app.models.enums import NotificationType, UserRole
from app.models.notifications import Notification


def _response(row: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=row.id,
        user_id=row.user_id,
        type=row.type.value if hasattr(row.type, "value") else str(row.type),
        title=row.title,
        body=row.body,
        is_read=row.is_read,
        created_at=row.created_at,
    )


def broadcast(
    db: Session, payload: BroadcastRequest, admin: AdminPrincipal
) -> BroadcastResponse:
    query = db.query(User.id).filter(User.deleted_at.is_(None), User.is_active.is_(True))
    if payload.audience == "ventor":
        query = query.filter(User.role == UserRole.ventor)
    elif payload.audience == "listener":
        query = query.filter(User.role == UserRole.listener)
    elif payload.audience == "user_ids":
        query = query.filter(User.id.in_(set(payload.user_ids or [])))
    user_ids = [row[0] for row in query.all()]
    db.add_all(
        [
            Notification(
                user_id=user_id,
                type=NotificationType.system,
                title=payload.title,
                body=payload.body,
            )
            for user_id in user_ids
        ]
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="notification.broadcast",
        entity_type="notification",
        entity_id="broadcast",
        after={"audience": payload.audience, "created_count": len(user_ids)},
    )
    db.commit()
    return BroadcastResponse(created_count=len(user_ids))


def list_system_notifications(
    db: Session, *, page: int = 1, page_size: int = 20
) -> Paginated[NotificationResponse]:
    page, page_size = clamp_page(page, page_size)
    query = db.query(Notification).filter(
        Notification.type == NotificationType.system,
        Notification.deleted_at.is_(None),
    )
    total = query.with_entities(func.count(Notification.id)).scalar() or 0
    rows = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Paginated(
        items=[_response(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def send_to_user(
    db: Session, user_id: UUID, payload: NotificationMessage
) -> NotificationResponse:
    user = (
        db.query(User.id)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None:
        raise not_found("User")
    row = Notification(
        user_id=user_id,
        type=NotificationType.system,
        title=payload.title,
        body=payload.body,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _response(row)
