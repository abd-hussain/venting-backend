"""Business logic for admin reports, moderation, ratings, and feedback."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.reports.schemas import (
    FeedbackItem,
    FeedbackList,
    ModerationActionItem,
    ModerationActionList,
    ModerationCreateRequest,
    RatingItem,
    RatingList,
    ReportItem,
    ReportList,
    ReportUpdateRequest,
)
from app.core.errors import not_found
from app.core.pagination import clamp_page
from app.models.admin import AdminUser, ModerationAction
from app.models.auth import RefreshToken, User
from app.models.enums import ModerationActionType
from app.models.sessions import (
    SessionListenerFeedback,
    SessionRating,
    SessionReport,
)


def _enum_value(value: object) -> str:
    return str(value.value) if hasattr(value, "value") else str(value)


def _report_item(row: SessionReport) -> ReportItem:
    return ReportItem(
        id=str(row.id),
        session_id=str(row.session_id),
        reporter_user_id=str(row.reporter_user_id),
        reported_role=_enum_value(row.reported_role),
        reason=_enum_value(row.reason),
        details=row.details,
        status=row.status,
        assigned_admin_id=str(row.assigned_admin_id) if row.assigned_admin_id else None,
        resolved_at=row.resolved_at,
        resolution_note=row.resolution_note,
        created_at=row.created_at,
    )


def _moderation_item(row: ModerationAction) -> ModerationActionItem:
    return ModerationActionItem(
        id=str(row.id),
        user_id=str(row.user_id),
        admin_user_id=str(row.admin_user_id),
        action=_enum_value(row.action),
        reason=row.reason,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        related_report_id=str(row.related_report_id) if row.related_report_id else None,
        created_at=row.created_at,
    )


def list_reports(
    db: Session, *, status: str | None, page: int
) -> ReportList:
    page, page_size = clamp_page(page)
    query = db.query(SessionReport)
    if status is not None:
        query = query.filter(SessionReport.status == status)
    total = query.count()
    rows = (
        query.order_by(SessionReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ReportList(
        items=[_report_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_report(db: Session, report_id: UUID) -> ReportItem:
    row = db.query(SessionReport).filter(SessionReport.id == report_id).one_or_none()
    if row is None:
        raise not_found("Report")
    return _report_item(row)


def update_report(
    db: Session,
    admin: AdminPrincipal,
    report_id: UUID,
    payload: ReportUpdateRequest,
) -> ReportItem:
    row = db.query(SessionReport).filter(SessionReport.id == report_id).one_or_none()
    if row is None:
        raise not_found("Report")

    fields = payload.model_fields_set
    before = {
        "assigned_admin_id": str(row.assigned_admin_id) if row.assigned_admin_id else None,
        "status": row.status,
        "resolution_note": row.resolution_note,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }

    if "assigned_admin_id" in fields:
        if payload.assigned_admin_id is not None:
            assignee = (
                db.query(AdminUser)
                .filter(AdminUser.id == payload.assigned_admin_id)
                .one_or_none()
            )
            if assignee is None:
                raise not_found("Admin")
        row.assigned_admin_id = payload.assigned_admin_id
    if "status" in fields and payload.status is not None:
        row.status = payload.status
        if payload.status == "closed":
            row.resolved_at = row.resolved_at or datetime.now(timezone.utc)
        else:
            row.resolved_at = None
    if "resolution_note" in fields:
        row.resolution_note = payload.resolution_note

    after = {
        "assigned_admin_id": str(row.assigned_admin_id) if row.assigned_admin_id else None,
        "status": row.status,
        "resolution_note": row.resolution_note,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }
    write_audit(
        db,
        admin_user_id=admin.id,
        action="report.update",
        entity_type="session_report",
        entity_id=row.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(row)
    return _report_item(row)


def create_moderation_action(
    db: Session,
    admin: AdminPrincipal,
    payload: ModerationCreateRequest,
) -> ModerationActionItem:
    user = (
        db.query(User)
        .filter(User.id == payload.user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None:
        raise not_found("User")
    if payload.related_report_id is not None:
        report = (
            db.query(SessionReport)
            .filter(SessionReport.id == payload.related_report_id)
            .one_or_none()
        )
        if report is None:
            raise not_found("Report")

    before = {
        "is_active": user.is_active,
        "suspended_until": (
            user.suspended_until.isoformat() if user.suspended_until else None
        ),
    }
    if payload.action == ModerationActionType.suspend:
        user.is_active = False
        user.suspended_until = payload.ends_at
    elif payload.action == ModerationActionType.ban:
        user.is_active = False
        user.suspended_until = None
    elif payload.action in {
        ModerationActionType.unsuspend,
        ModerationActionType.unban,
    }:
        user.is_active = True
        user.suspended_until = None

    now = datetime.now(timezone.utc)
    if payload.action in {
        ModerationActionType.suspend,
        ModerationActionType.ban,
        ModerationActionType.force_logout,
    }:
        (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .update({RefreshToken.revoked_at: now}, synchronize_session=False)
        )

    row = ModerationAction(
        user_id=user.id,
        admin_user_id=admin.id,
        action=payload.action,
        reason=payload.reason,
        ends_at=payload.ends_at,
        related_report_id=payload.related_report_id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="user.moderate",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={
            "is_active": user.is_active,
            "suspended_until": (
                user.suspended_until.isoformat() if user.suspended_until else None
            ),
            "moderation_action": payload.action.value,
            "moderation_action_id": str(row.id),
        },
    )
    db.commit()
    db.refresh(row)
    return _moderation_item(row)


def list_moderation_actions(
    db: Session, *, user_id: UUID, page: int
) -> ModerationActionList:
    page, page_size = clamp_page(page)
    query = db.query(ModerationAction).filter(ModerationAction.user_id == user_id)
    total = query.count()
    rows = (
        query.order_by(ModerationAction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ModerationActionList(
        items=[_moderation_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_low_ratings(db: Session, *, page: int) -> RatingList:
    page, page_size = clamp_page(page)
    query = db.query(SessionRating).filter(SessionRating.stars <= 2)
    total = query.count()
    rows = (
        query.order_by(SessionRating.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RatingList(
        items=[
            RatingItem(
                id=str(row.id),
                session_id=str(row.session_id),
                ventor_id=str(row.ventor_id),
                listener_id=str(row.listener_id),
                stars=row.stars,
                review=row.review,
                tip_amount=float(row.tip_amount) if row.tip_amount is not None else None,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_feedback(db: Session, *, page: int) -> FeedbackList:
    page, page_size = clamp_page(page)
    query = db.query(SessionListenerFeedback)
    total = query.count()
    rows = (
        query.order_by(SessionListenerFeedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return FeedbackList(
        items=[
            FeedbackItem(
                id=str(row.id),
                session_id=str(row.session_id),
                listener_id=str(row.listener_id),
                ventor_id=str(row.ventor_id),
                stars=row.stars,
                felt_heard=row.felt_heard,
                talk_again=row.talk_again,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
