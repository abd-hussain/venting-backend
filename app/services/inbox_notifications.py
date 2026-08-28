"""Inbox notifications — list, mark read, create with onboarding triggers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.core.pagination import clamp_page
from app.models.auth import User
from app.models.enums import NotificationType, SessionStatus, UserRole
from app.models.notifications import Notification
from app.models.profiles import VentorProfile
from app.models.sessions import Session as VentingSession
from app.services.registration_progress import (
    LISTENER_REGISTER_STEPS,
    VENTOR_REGISTER_STEPS,
    next_step_for,
)

WELCOME_COPY = (
    "Welcome to Venting",
    "Complete your profile so you can start connecting.",
)
COMPLETE_REGISTRATION_COPY = (
    "Finish setting up",
    "You're almost there — pick up where you left off.",
)
BOOK_FIRST_SESSION_VENTOR_COPY = (
    "Book your first session",
    "Find a listener who's ready when you are.",
)
BOOK_FIRST_SESSION_LISTENER_COPY = (
    "You're approved — go online",
    "Set your availability and start helping people.",
)


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    body: str
    created_at: str
    is_read: bool
    data: dict | None = None


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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def has_unread_of_type(
    db: Session,
    user_id: UUID,
    notification_type: NotificationType,
) -> bool:
    return (
        db.query(Notification.id)
        .filter(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def create_inbox_notification(
    db: Session,
    user_id: UUID,
    notification_type: NotificationType,
    *,
    title: str,
    body: str,
    data: dict | None = None,
    dedupe_unread: bool = True,
) -> Notification | None:
    if dedupe_unread and has_unread_of_type(db, user_id, notification_type):
        return None
    row = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        data=data,
    )
    db.add(row)
    return row


def send_welcome_notification(db: Session, user: User) -> Notification | None:
    return create_inbox_notification(
        db,
        user.id,
        NotificationType.welcome,
        title=WELCOME_COPY[0],
        body=WELCOME_COPY[1],
        data={"action": "open_registration"},
    )


def send_complete_registration_nudge(db: Session, user: User) -> Notification | None:
    steps = (
        LISTENER_REGISTER_STEPS if user.role == UserRole.listener else VENTOR_REGISTER_STEPS
    )
    data: dict = {"action": "open_registration"}
    next_step = user.registration_next_step or next_step_for(user, steps)
    if next_step:
        data["next_step"] = next_step
    return create_inbox_notification(
        db,
        user.id,
        NotificationType.complete_registration,
        title=COMPLETE_REGISTRATION_COPY[0],
        body=COMPLETE_REGISTRATION_COPY[1],
        data=data,
    )


def _ventor_has_completed_sessions(db: Session, ventor_id: UUID) -> bool:
    profile = db.get(VentorProfile, ventor_id)
    if profile is not None and (profile.completed_sessions_count or 0) > 0:
        return True
    return (
        db.query(VentingSession.id)
        .filter(
            VentingSession.ventor_id == ventor_id,
            VentingSession.status == SessionStatus.completed,
        )
        .first()
        is not None
    )


def _listener_has_completed_sessions(db: Session, listener_id: UUID) -> bool:
    return (
        db.query(VentingSession.id)
        .filter(
            VentingSession.listener_id == listener_id,
            VentingSession.status == SessionStatus.completed,
        )
        .first()
        is not None
    )


def send_book_first_session_ventor(db: Session, user: User) -> Notification | None:
    if _ventor_has_completed_sessions(db, user.id):
        return None
    return create_inbox_notification(
        db,
        user.id,
        NotificationType.book_first_session,
        title=BOOK_FIRST_SESSION_VENTOR_COPY[0],
        body=BOOK_FIRST_SESSION_VENTOR_COPY[1],
        data={"action": "book_first_session"},
    )


def send_book_first_session_listener(db: Session, user_id: UUID) -> Notification | None:
    if _listener_has_completed_sessions(db, user_id):
        return None
    return create_inbox_notification(
        db,
        user_id,
        NotificationType.book_first_session,
        title=BOOK_FIRST_SESSION_LISTENER_COPY[0],
        body=BOOK_FIRST_SESSION_LISTENER_COPY[1],
        data={"action": "open_availability"},
    )


def run_complete_registration_job(db: Session, *, inactive_hours: int = 24) -> int:
    cutoff = _utc_now() - timedelta(hours=inactive_hours)
    users = (
        db.query(User)
        .filter(
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.registration_complete.is_(False),
            User.last_login_at.isnot(None),
            User.last_login_at <= cutoff,
        )
        .all()
    )
    created = 0
    for user in users:
        if send_complete_registration_nudge(db, user) is not None:
            created += 1
    if created:
        db.commit()
    return created


def run_book_first_session_reminders(db: Session, *, after_hours: int = 48) -> int:
    cutoff = _utc_now() - timedelta(hours=after_hours)
    created = 0

    ventors = (
        db.query(User)
        .join(VentorProfile, VentorProfile.user_id == User.id)
        .filter(
            User.deleted_at.is_(None),
            User.role == UserRole.ventor,
            User.registration_complete.is_(True),
            User.updated_at <= cutoff,
        )
        .all()
    )
    for user in ventors:
        if _ventor_has_completed_sessions(db, user.id):
            continue
        if send_book_first_session_ventor(db, user) is not None:
            created += 1

    from app.models.enums import ProfileStatus
    from app.models.profiles import ListenerProfile

    listeners = (
        db.query(User)
        .join(ListenerProfile, ListenerProfile.user_id == User.id)
        .filter(
            User.deleted_at.is_(None),
            User.role == UserRole.listener,
            ListenerProfile.profile_status == ProfileStatus.approved,
            ListenerProfile.reviewed_at.isnot(None),
            ListenerProfile.reviewed_at <= cutoff,
        )
        .all()
    )
    for user in listeners:
        if _listener_has_completed_sessions(db, user.id):
            continue
        if send_book_first_session_listener(db, user.id) is not None:
            created += 1

    if created:
        db.commit()
    return created


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
                data=r.data if isinstance(r.data, dict) else None,
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
    row.deleted_at = _utc_now()
    db.commit()
    return OkCountResponse(ok=True)
