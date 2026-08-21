"""Admin session search, detail, cancellation, and refund operations."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.sessions.schemas import (
    ListenerFeedbackDetail,
    PaymentDetail,
    SessionActionResponse,
    SessionDetail,
    SessionItem,
    SessionList,
    SessionRatingDetail,
    SessionRequestItem,
    SessionRequestList,
    SessionTimeline,
    TimelineEvent,
)
from app.core.errors import not_found, validation_error
from app.core.pagination import clamp_page
from app.models.enums import PaymentStatus, SessionRequestStatus, SessionStatus
from app.models.sessions import Session as VentingSession
from app.models.sessions import (
    SessionListenerFeedback,
    SessionPayment,
    SessionRating,
    SessionRequest,
)


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _date_range(
    from_date: date | None,
    to_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    if from_date and to_date and from_date > to_date:
        raise validation_error("'from' must be on or before 'to'")
    start = (
        datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        if from_date
        else None
    )
    end = (
        datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if to_date
        else None
    )
    return start, end


def _session_item(
    row: VentingSession,
    payment: SessionPayment | None = None,
) -> SessionItem:
    return SessionItem(
        id=str(row.id),
        request_id=str(row.request_id) if row.request_id else None,
        ventor_id=str(row.ventor_id),
        listener_id=str(row.listener_id),
        status=_value(row.status),
        duration_minutes=row.duration_minutes,
        actual_duration_seconds=row.actual_duration_seconds,
        scheduled_at=row.scheduled_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        created_at=row.created_at,
        amount_paid=float(payment.amount_paid) if payment else None,
        currency=payment.currency if payment else None,
    )


def list_sessions(
    db: Session,
    *,
    status: str | None,
    ventor_id: UUID | None,
    listener_id: UUID | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> SessionList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(VentingSession, SessionPayment).outerjoin(
        SessionPayment,
        SessionPayment.session_id == VentingSession.id,
    )
    if status:
        try:
            parsed_status = SessionStatus(status)
        except ValueError:
            raise validation_error("Invalid session status") from None
        query = query.filter(VentingSession.status == parsed_status)
    if ventor_id:
        query = query.filter(VentingSession.ventor_id == ventor_id)
    if listener_id:
        query = query.filter(VentingSession.listener_id == listener_id)
    start, end = _date_range(from_date, to_date)
    session_date = func.coalesce(VentingSession.scheduled_at, VentingSession.created_at)
    if start:
        query = query.filter(session_date >= start)
    if end:
        query = query.filter(session_date < end)
    total = query.count()
    rows = (
        query.order_by(session_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SessionList(
        items=[_session_item(session, payment) for session, payment in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_session(db: Session, session_id: UUID) -> SessionDetail:
    session = (
        db.query(VentingSession)
        .filter(VentingSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise not_found("Session")
    payment = (
        db.query(SessionPayment)
        .filter(SessionPayment.session_id == session_id)
        .one_or_none()
    )
    rating = (
        db.query(SessionRating)
        .filter(SessionRating.session_id == session_id)
        .one_or_none()
    )
    listener_feedback = (
        db.query(SessionListenerFeedback)
        .filter(SessionListenerFeedback.session_id == session_id)
        .one_or_none()
    )
    base = _session_item(session, payment).model_dump()
    return SessionDetail(
        **base,
        time_mode=_value(session.time_mode),
        call_mode=_value(session.call_mode),
        speech_language=session.speech_language,
        voice_change_enabled=session.voice_change_enabled,
        is_instant=session.is_instant,
        message=session.message,
        chosen_reason=session.chosen_reason,
        tags=session.tags,
        cancelled_at=session.cancelled_at,
        cancel_reason=session.cancel_reason,
        payment=(
            PaymentDetail(
                id=str(payment.id),
                status=_value(payment.status),
                currency=payment.currency,
                session_price=float(payment.session_price),
                voice_change_fee=float(payment.voice_change_fee),
                discount_amount=float(payment.discount_amount),
                tip_amount=float(payment.tip_amount),
                amount_paid=float(payment.amount_paid),
                refunded_amount=float(payment.refunded_amount),
                provider=payment.provider,
                provider_payment_id=payment.provider_payment_id,
            )
            if payment
            else None
        ),
        rating=(
            SessionRatingDetail(
                stars=rating.stars,
                review=rating.review,
                tip_amount=float(rating.tip_amount) if rating.tip_amount is not None else None,
                created_at=rating.created_at,
            )
            if rating
            else None
        ),
        listener_feedback=(
            ListenerFeedbackDetail(
                stars=listener_feedback.stars,
                felt_heard=listener_feedback.felt_heard,
                talk_again=listener_feedback.talk_again,
                created_at=listener_feedback.created_at,
            )
            if listener_feedback
            else None
        ),
    )


def cancel_session(
    db: Session,
    admin: AdminPrincipal,
    session_id: UUID,
    *,
    reason: str | None,
) -> SessionActionResponse:
    session = (
        db.query(VentingSession)
        .filter(VentingSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise not_found("Session")
    if session.status == SessionStatus.cancelled:
        return SessionActionResponse(id=str(session.id), status="cancelled")
    if session.status == SessionStatus.completed:
        raise validation_error("Completed sessions cannot be cancelled")
    before = {"status": _value(session.status), "cancel_reason": session.cancel_reason}
    session.status = SessionStatus.cancelled
    session.cancelled_at = datetime.now(timezone.utc)
    session.cancel_reason = reason or "Cancelled by admin"
    write_audit(
        db,
        admin_user_id=admin.id,
        action="session.cancel",
        entity_type="session",
        entity_id=session.id,
        before=before,
        after={"status": "cancelled", "cancel_reason": session.cancel_reason},
    )
    db.commit()
    return SessionActionResponse(id=str(session.id), status="cancelled")


def refund_session(
    db: Session,
    admin: AdminPrincipal,
    session_id: UUID,
    *,
    amount: float | None,
) -> SessionActionResponse:
    session = (
        db.query(VentingSession)
        .filter(VentingSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise not_found("Session")
    payment = (
        db.query(SessionPayment)
        .filter(SessionPayment.session_id == session_id)
        .one_or_none()
    )
    if payment is None:
        raise not_found("Session payment")
    if payment.status == PaymentStatus.refunded:
        return SessionActionResponse(
            id=str(session.id),
            status="refunded",
            refunded_amount=float(payment.refunded_amount),
        )
    if payment.status != PaymentStatus.paid:
        raise validation_error("Only paid sessions can be refunded")
    current = Decimal(payment.refunded_amount or 0)
    refundable = Decimal(payment.amount_paid) - current
    refund_amount = (
        Decimal(str(amount)).quantize(Decimal("0.01"))
        if amount is not None
        else refundable
    )
    if refund_amount <= 0:
        raise validation_error("Refund amount must be greater than zero")
    if refund_amount > refundable:
        raise validation_error("Refund amount exceeds the refundable balance")
    before = {
        "status": _value(payment.status),
        "refunded_amount": float(current),
    }
    payment.refunded_amount = current + refund_amount
    payment.status = PaymentStatus.refunded
    write_audit(
        db,
        admin_user_id=admin.id,
        action="session.refund",
        entity_type="session",
        entity_id=session.id,
        before=before,
        after={
            "status": "refunded",
            "refunded_amount": float(payment.refunded_amount),
        },
    )
    db.commit()
    return SessionActionResponse(
        id=str(session.id),
        status="refunded",
        refunded_amount=float(payment.refunded_amount),
    )


def list_session_requests(
    db: Session,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> SessionRequestList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(SessionRequest)
    if status:
        try:
            parsed_status = SessionRequestStatus(status)
        except ValueError:
            raise validation_error("Invalid session request status") from None
        query = query.filter(SessionRequest.status == parsed_status)
    total = query.count()
    rows = (
        query.order_by(SessionRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SessionRequestList(
        items=[
            SessionRequestItem(
                id=str(row.id),
                ventor_id=str(row.ventor_id),
                listener_id=str(row.listener_id) if row.listener_id else None,
                session_id=str(row.session_id) if row.session_id else None,
                status=_value(row.status),
                duration_minutes=row.duration_minutes,
                scheduled_at=row.scheduled_at,
                is_instant=row.is_instant,
                quoted_amount=float(row.quoted_amount),
                expires_at=row.expires_at,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_session_timeline(db: Session, session_id: UUID) -> SessionTimeline:
    session = (
        db.query(VentingSession)
        .filter(VentingSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise not_found("Session")
    candidates = [
        ("created", session.created_at),
        ("scheduled", session.scheduled_at),
        ("started", session.started_at),
        ("ended", session.ended_at),
        ("cancelled", session.cancelled_at),
    ]
    items = [
        TimelineEvent(key=key, at=event_at)
        for key, event_at in candidates
        if event_at is not None
    ]
    items.sort(key=lambda item: item.at)
    return SessionTimeline(session_id=str(session.id), items=items)
