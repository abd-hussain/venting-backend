"""Sessions business logic — booking, join, feedback."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from jose import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.listeners.discovery import list_listeners
from app.api.v1.catalogs.service import assert_active_language
from app.api.v1.sessions.schemas import (
    AcceptRequestResponse,
    BookSessionRequest,
    CancelSessionRequest,
    CancelSessionResponse,
    EndSessionRequest,
    EndSessionResponse,
    FeedbackRequest,
    InstantMatchRequest,
    InstantMatchResponse,
    JoinCallResponse,
    ListenerSessionItem,
    ListenerSessionsResponse,
    OkResponse,
    PaymentInfo,
    RatingRequest,
    RatingResponse,
    ReportRequest,
    ReportResponse,
    SessionRequestItem,
    SessionRequestsResponse,
    SessionStatsResponse,
    VentorBookedSession,
    VentorSessionsResponse,
)
from app.core.config import Settings
from app.core.errors import conflict, forbidden, not_found, offer_expired, validation_error
from app.core.pagination import clamp_page
from app.models.auth import User
from app.models.availability import ListenerAvailabilitySlot
from app.models.enums import (
    CallMode,
    DayOfWeek,
    PaymentStatus,
    ReportReason,
    ReportedRole,
    SessionRequestStatus,
    SessionStatus,
    SessionTimeMode,
    UserRole,
)
from app.models.profiles import ListenerProfile, VentorProfile
from app.models.promo import PromoCode, PromoRedemption
from app.models.rewards import RewardOffer
from app.services.reward_offers import is_offer_expired
from app.models.sessions import (
    Session as VentingSession,
)
from app.models.sessions import (
    SessionListenerFeedback,
    SessionPayment,
    SessionRating,
    SessionReport,
    SessionRequest,
)

VOICE_CHANGE_FEE = Decimal("1.00")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_scheduled_at(raw: str | None) -> datetime | None:
    if raw is None or not raw.strip():
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise validation_error("scheduled_at must be ISO-8601") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _payment_for(db: Session, session_id: UUID) -> SessionPayment | None:
    return (
        db.query(SessionPayment)
        .filter(SessionPayment.session_id == session_id)
        .one_or_none()
    )


_WEEKDAY_TO_DAY: dict[int, DayOfWeek] = {
    0: DayOfWeek.mon,
    1: DayOfWeek.tue,
    2: DayOfWeek.wed,
    3: DayOfWeek.thu,
    4: DayOfWeek.fri,
    5: DayOfWeek.sat,
    6: DayOfWeek.sun,
}


def _resolve_nearest_slot(db: Session, listener_id: UUID) -> datetime | None:
    slots = (
        db.query(ListenerAvailabilitySlot)
        .filter(ListenerAvailabilitySlot.listener_id == listener_id)
        .all()
    )
    if not slots:
        return None
    slots_by_day: dict[DayOfWeek, list[ListenerAvailabilitySlot]] = {}
    for slot in slots:
        slots_by_day.setdefault(slot.day, []).append(slot)

    now = _utc_now()
    for offset in range(8):
        day_date = now.date() + timedelta(days=offset)
        day_enum = _WEEKDAY_TO_DAY[day_date.weekday()]
        for slot in sorted(slots_by_day.get(day_enum, []), key=lambda row: row.start_time):
            candidate = datetime.combine(day_date, slot.start_time, tzinfo=timezone.utc)
            if candidate > now:
                return candidate
    return None


def _ventor_avg_rating(db: Session, ventor_id: UUID) -> float | None:
    value = (
        db.query(func.avg(SessionListenerFeedback.stars))
        .filter(SessionListenerFeedback.ventor_id == ventor_id)
        .scalar()
    )
    if value is None:
        return None
    return round(float(value), 1)


def _booked_session(
    db: Session,
    session: VentingSession,
    *,
    include_payment: bool = False,
) -> VentorBookedSession:
    listener = db.get(ListenerProfile, session.listener_id)
    payment = _payment_for(db, session.id)
    amount = float(payment.amount_paid) if payment else 0.0
    refunded = float(payment.refunded_amount) if payment and payment.refunded_amount else None
    payload = VentorBookedSession(
        id=str(session.id),
        listener_id=str(session.listener_id),
        listener_name=listener.full_name if listener else "Listener",
        listener_avatar_url=listener.avatar_url if listener else None,
        duration_minutes=session.duration_minutes,
        status=session.status.value,
        call_mode=session.call_mode.value,
        speech_language=session.speech_language,
        amount_paid=amount,
        voice_change_enabled=session.voice_change_enabled,
        scheduled_at=_iso(session.scheduled_at),
        is_instant=session.is_instant,
        refunded_to_balance=refunded if refunded else None,
    )
    if include_payment and payment is not None:
        payload.payment = PaymentInfo(
            amount_paid=float(payment.amount_paid),
            currency=payment.currency,
            voice_change_fee=float(payment.voice_change_fee),
            discount_amount=float(payment.discount_amount),
        )
    return payload


def _quote_price(
    listener: ListenerProfile,
    *,
    duration_minutes: int,
    voice_change_enabled: bool,
    promo: PromoCode | None,
    offer: RewardOffer | None,
) -> tuple[Decimal, Decimal, Decimal]:
    base = Decimal(listener.rate_per_minute) * Decimal(duration_minutes)
    voice_fee = VOICE_CHANGE_FEE if voice_change_enabled else Decimal("0")
    discount = Decimal("0")
    if promo is not None:
        if promo.percent_off:
            discount += (base * Decimal(promo.percent_off) / Decimal(100)).quantize(Decimal("0.01"))
        if promo.fixed_amount:
            discount += Decimal(promo.fixed_amount)
    if offer is not None and offer.percent_off:
        discount += (base * Decimal(offer.percent_off) / Decimal(100)).quantize(Decimal("0.01"))
    if offer is not None and offer.free_minutes:
        free_value = Decimal(listener.rate_per_minute) * Decimal(min(offer.free_minutes, duration_minutes))
        discount += free_value
    discount = min(discount, base)
    amount = (base + voice_fee - discount).quantize(Decimal("0.01"))
    if amount < 0:
        amount = Decimal("0")
    return amount, voice_fee, discount


def instant_match(
    db: Session,
    ventor: User,
    payload: InstantMatchRequest,
) -> InstantMatchResponse:
    if ventor.role != UserRole.ventor:
        raise forbidden()
    result = list_listeners(
        db,
        ventor,
        topic=payload.topic,
        languages=payload.language,
        online_only=True,
        page=1,
        page_size=20,
    )
    if not result.items:
        result = list_listeners(
            db,
            ventor,
            topic=payload.topic,
            languages=payload.language,
            page=1,
            page_size=20,
        )
    if not result.items:
        raise not_found("Listener")
    pick = secrets.choice(result.items)
    duration = payload.duration_minutes or 30
    return InstantMatchResponse(
        listener=pick.model_dump(mode="json"),
        suggested_duration_minutes=duration,
    )


def book_session(
    db: Session,
    ventor: User,
    payload: BookSessionRequest,
) -> VentorBookedSession:
    if ventor.role != UserRole.ventor:
        raise forbidden()
    ventor_profile = db.get(VentorProfile, ventor.id)
    if ventor_profile is None:
        raise forbidden()

    try:
        listener_id = UUID(payload.listener_id)
    except ValueError as exc:
        raise validation_error("Invalid listener_id") from exc

    listener = db.get(ListenerProfile, listener_id)
    if listener is None:
        raise not_found("Listener")

    assert_active_language(db, payload.speech_language)

    scheduled_at = _parse_scheduled_at(payload.scheduled_at)
    if payload.time_mode == SessionTimeMode.scheduled and scheduled_at is None:
        raise validation_error("scheduled_at is required for scheduled sessions")
    if payload.time_mode == SessionTimeMode.nearest:
        scheduled_at = _resolve_nearest_slot(db, listener_id)
        if scheduled_at is None:
            raise validation_error(
                "No availability found for nearest booking",
                ar="لا يوجد موعد متاح للحجز الأقرب",
            )

    promo = None
    if payload.promo_code:
        promo = (
            db.query(PromoCode)
            .filter(PromoCode.code == payload.promo_code.strip().upper(), PromoCode.is_active.is_(True))
            .one_or_none()
        )
        if promo is None:
            raise validation_error("Invalid promo code")

    offer = None
    if payload.reward_offer_id:
        try:
            offer = db.get(RewardOffer, UUID(payload.reward_offer_id))
        except ValueError as exc:
            raise validation_error("Invalid reward_offer_id") from exc
        if offer is None or not offer.is_active:
            raise validation_error("Invalid reward offer")
        if is_offer_expired(offer):
            raise offer_expired()

    amount, voice_fee, discount = _quote_price(
        listener,
        duration_minutes=payload.duration_minutes,
        voice_change_enabled=payload.voice_change_enabled,
        promo=promo,
        offer=offer,
    )

    is_instant = payload.time_mode == SessionTimeMode.instant
    request = SessionRequest(
        ventor_id=ventor.id,
        listener_id=listener_id,
        status=SessionRequestStatus.pending if is_instant else SessionRequestStatus.accepted,
        duration_minutes=payload.duration_minutes,
        time_mode=SessionTimeMode(payload.time_mode.value),
        scheduled_at=scheduled_at or (_utc_now() if is_instant else None),
        call_mode=CallMode(payload.call_mode.value),
        speech_language=payload.speech_language,
        voice_change_enabled=payload.voice_change_enabled,
        is_instant=is_instant,
        promo_code_id=promo.id if promo else None,
        reward_offer_id=offer.id if offer else None,
        quoted_amount=amount,
    )
    db.add(request)
    db.flush()

    if is_instant:
        db.commit()
        db.refresh(request)
        return VentorBookedSession(
            id=str(request.id),
            listener_id=str(listener_id),
            listener_name=listener.full_name,
            listener_avatar_url=listener.avatar_url,
            duration_minutes=payload.duration_minutes,
            status="pending",
            call_mode=payload.call_mode.value,
            speech_language=payload.speech_language,
            amount_paid=float(amount),
            voice_change_enabled=payload.voice_change_enabled,
            scheduled_at=_iso(request.scheduled_at),
            is_instant=True,
            payment=PaymentInfo(
                amount_paid=float(amount),
                voice_change_fee=float(voice_fee),
                discount_amount=float(discount),
            ),
        )

    session = VentingSession(
        request_id=request.id,
        ventor_id=ventor.id,
        listener_id=listener_id,
        status=SessionStatus.upcoming,
        duration_minutes=payload.duration_minutes,
        time_mode=SessionTimeMode(payload.time_mode.value),
        scheduled_at=scheduled_at or _utc_now(),
        started_at=None,
        call_mode=CallMode(payload.call_mode.value),
        speech_language=payload.speech_language,
        voice_change_enabled=payload.voice_change_enabled,
        is_instant=payload.time_mode == SessionTimeMode.instant,
        call_channel_id=f"venting-{secrets.token_hex(8)}",
    )
    db.add(session)
    db.flush()
    request.session_id = session.id

    payment = SessionPayment(
        session_id=session.id,
        session_price=(amount - voice_fee + discount),
        voice_change_fee=voice_fee,
        discount_amount=discount,
        amount_paid=amount,
        status=PaymentStatus.paid,
        promo_code_id=promo.id if promo else None,
        reward_offer_id=offer.id if offer else None,
    )
    db.add(payment)
    if promo is not None:
        promo.redemption_count = (promo.redemption_count or 0) + 1
        db.add(
            PromoRedemption(
                promo_code_id=promo.id,
                ventor_id=ventor.id,
                session_id=session.id,
                discount_amount=discount,
            )
        )
    if offer is not None and ventor_profile.active_reward_offer_id == offer.id:
        ventor_profile.active_reward_offer_id = None

    db.commit()
    db.refresh(session)
    return _booked_session(db, session, include_payment=True)


def list_ventor_sessions(
    db: Session,
    ventor: User,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> VentorSessionsResponse:
    page, page_size = clamp_page(page, page_size)
    query = db.query(VentingSession).filter(VentingSession.ventor_id == ventor.id)
    if status:
        try:
            query = query.filter(VentingSession.status == SessionStatus(status))
        except ValueError as exc:
            raise validation_error("Invalid status") from exc
    total = query.with_entities(func.count(VentingSession.id)).scalar() or 0
    rows = (
        query.order_by(VentingSession.scheduled_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return VentorSessionsResponse(
        items=[_booked_session(db, row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_ventor_session(db: Session, ventor: User, session_id: UUID) -> VentorBookedSession:
    session = db.get(VentingSession, session_id)
    if session is None or session.ventor_id != ventor.id:
        raise not_found("Session")
    return _booked_session(db, session, include_payment=True)


def cancel_ventor_session(
    db: Session,
    ventor: User,
    session_id: UUID,
    payload: CancelSessionRequest | None = None,
) -> CancelSessionResponse:
    session = db.get(VentingSession, session_id)
    if session is None or session.ventor_id != ventor.id:
        raise not_found("Session")

    payment = _payment_for(db, session.id)

    # Idempotent: already cancelled → return current refund state.
    if session.status == SessionStatus.cancelled:
        refunded = float(payment.refunded_amount or payment.amount_paid) if payment else 0.0
        booked = _booked_session(db, session)
        booked.refunded_to_balance = refunded
        return CancelSessionResponse(session=booked, refunded_to_balance=refunded)

    if session.status not in {SessionStatus.upcoming, SessionStatus.live}:
        raise conflict("Session cannot be cancelled")

    refunded = float(payment.amount_paid) if payment else 0.0
    if payment is not None:
        payment.refunded_amount = payment.amount_paid
        payment.status = PaymentStatus.refunded

    session.status = SessionStatus.cancelled
    session.cancelled_at = _utc_now()
    if payload and payload.reason:
        session.cancel_reason = payload.reason
    db.commit()
    db.refresh(session)
    booked = _booked_session(db, session)
    booked.refunded_to_balance = refunded
    return CancelSessionResponse(session=booked, refunded_to_balance=refunded)


def list_listener_sessions(
    db: Session,
    listener: User,
    *,
    filter_name: str = "upcoming",
    page: int = 1,
    page_size: int = 20,
) -> ListenerSessionsResponse:
    page, page_size = clamp_page(page, page_size)
    query = db.query(VentingSession).filter(VentingSession.listener_id == listener.id)
    if filter_name == "upcoming":
        query = query.filter(
            VentingSession.status.in_([SessionStatus.upcoming, SessionStatus.live])
        )
    elif filter_name == "missed":
        query = query.filter(VentingSession.status == SessionStatus.missed)
    else:
        query = query.filter(
            VentingSession.status.in_(
                [SessionStatus.completed, SessionStatus.cancelled, SessionStatus.missed]
            )
        )
    total = query.with_entities(func.count(VentingSession.id)).scalar() or 0
    rows = (
        query.order_by(VentingSession.scheduled_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items: list[ListenerSessionItem] = []
    now = _utc_now()
    for session in rows:
        ventor = db.get(VentorProfile, session.ventor_id)
        payment = _payment_for(db, session.id)
        can_join = session.status in {SessionStatus.upcoming, SessionStatus.live}
        if session.scheduled_at and session.status == SessionStatus.upcoming:
            can_join = abs((session.scheduled_at - now).total_seconds()) <= 15 * 60
        items.append(
            ListenerSessionItem(
                id=str(session.id),
                scheduled_at=_iso(session.scheduled_at),
                duration_minutes=session.duration_minutes,
                ventor_name=ventor.nickname if ventor else "Ventor",
                ventor_avatar_url=ventor.avatar_url if ventor else None,
                message=session.message,
                chosen_reason=session.chosen_reason,
                tags=list(session.tags) if session.tags else None,
                speech_language=session.speech_language,
                is_waiting=session.status == SessionStatus.upcoming,
                can_join_now=can_join and session.status != SessionStatus.cancelled,
                is_instant=session.is_instant,
                is_video_call=session.call_mode == CallMode.video,
                ventor_rating=_ventor_avg_rating(db, session.ventor_id),
                status_label=session.status.value,
                session_cost=float(payment.amount_paid) if payment else None,
                is_missed=session.status == SessionStatus.missed,
                history_outcome=session.listener_history_outcome,
            )
        )
    return ListenerSessionsResponse(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )


def session_stats(db: Session, listener: User) -> SessionStatsResponse:
    accepted = (
        db.query(func.count(SessionRequest.id))
        .filter(
            SessionRequest.listener_id == listener.id,
            SessionRequest.status == SessionRequestStatus.accepted,
        )
        .scalar()
        or 0
    )
    declined = (
        db.query(func.count(SessionRequest.id))
        .filter(
            SessionRequest.listener_id == listener.id,
            SessionRequest.status == SessionRequestStatus.declined,
        )
        .scalar()
        or 0
    )
    missed = (
        db.query(func.count(VentingSession.id))
        .filter(
            VentingSession.listener_id == listener.id,
            VentingSession.status == SessionStatus.missed,
        )
        .scalar()
        or 0
    )
    return SessionStatsResponse(
        accepted_count=int(accepted),
        declined_count=int(declined),
        missed_count=int(missed),
    )


def list_session_requests(db: Session, listener: User) -> SessionRequestsResponse:
    rows = (
        db.query(SessionRequest)
        .filter(
            SessionRequest.listener_id == listener.id,
            SessionRequest.status == SessionRequestStatus.pending,
        )
        .order_by(SessionRequest.created_at.desc())
        .all()
    )
    items: list[SessionRequestItem] = []
    for req in rows:
        ventor = db.get(VentorProfile, req.ventor_id)
        items.append(
            SessionRequestItem(
                id=str(req.id),
                ventor_name=ventor.nickname if ventor else "Ventor",
                ventor_avatar_url=ventor.avatar_url if ventor else None,
                message=req.message,
                chosen_reason=req.chosen_reason,
                scheduled_at=_iso(req.scheduled_at),
                duration_minutes=req.duration_minutes,
                tags=list(req.tags) if req.tags else None,
                received_at=_iso(req.created_at) or _iso(_utc_now()) or "",
                speech_language=req.speech_language,
                is_instant=req.is_instant,
                is_video_call=req.call_mode == CallMode.video,
                ventor_rating=_ventor_avg_rating(db, session.ventor_id),
            )
        )
    return SessionRequestsResponse(items=items)


def accept_session_request(
    db: Session,
    listener: User,
    request_id: UUID,
) -> AcceptRequestResponse:
    if listener.role != UserRole.listener:
        raise forbidden()
    req = db.get(SessionRequest, request_id)
    if req is None:
        raise not_found("Session request")

    # Idempotent: already accepted by this listener.
    if (
        req.status == SessionRequestStatus.accepted
        and req.listener_id == listener.id
        and req.session_id is not None
    ):
        return AcceptRequestResponse(session_id=str(req.session_id), status="accepted")

    if req.is_instant:
        if req.status != SessionRequestStatus.pending:
            return AcceptRequestResponse(session_id=None, status="already_taken")
        if req.listener_id is not None and req.listener_id != listener.id:
            return AcceptRequestResponse(session_id=None, status="already_taken")
        req.listener_id = listener.id
    elif req.listener_id != listener.id:
        raise forbidden()
    if req.status != SessionRequestStatus.pending:
        return AcceptRequestResponse(session_id=None, status="already_taken")

    req.status = SessionRequestStatus.accepted
    session = VentingSession(
        request_id=req.id,
        ventor_id=req.ventor_id,
        listener_id=listener.id,
        status=SessionStatus.live if req.is_instant else SessionStatus.upcoming,
        duration_minutes=req.duration_minutes,
        time_mode=req.time_mode,
        scheduled_at=req.scheduled_at or _utc_now(),
        started_at=_utc_now() if req.is_instant else None,
        call_mode=req.call_mode,
        speech_language=req.speech_language,
        voice_change_enabled=req.voice_change_enabled,
        is_instant=req.is_instant,
        message=req.message,
        chosen_reason=req.chosen_reason,
        tags=req.tags,
        call_channel_id=f"venting-{secrets.token_hex(8)}",
    )
    db.add(session)
    db.flush()
    req.session_id = session.id
    db.add(
        SessionPayment(
            session_id=session.id,
            session_price=req.quoted_amount,
            amount_paid=req.quoted_amount,
            status=PaymentStatus.paid,
            promo_code_id=req.promo_code_id,
            reward_offer_id=req.reward_offer_id,
        )
    )
    if req.promo_code_id is not None:
        promo = db.get(PromoCode, req.promo_code_id)
        if promo is not None:
            promo.redemption_count = (promo.redemption_count or 0) + 1
            db.add(
                PromoRedemption(
                    promo_code_id=promo.id,
                    ventor_id=req.ventor_id,
                    session_id=session.id,
                    discount_amount=Decimal("0"),
                )
            )
    if req.reward_offer_id is not None:
        ventor_profile = db.get(VentorProfile, req.ventor_id)
        if (
            ventor_profile is not None
            and ventor_profile.active_reward_offer_id == req.reward_offer_id
        ):
            ventor_profile.active_reward_offer_id = None
    db.commit()
    return AcceptRequestResponse(session_id=str(session.id), status="accepted")


def decline_session_request(
    db: Session,
    listener: User,
    request_id: UUID,
    reason: str | None = None,
) -> OkResponse:
    if listener.role != UserRole.listener:
        raise forbidden()
    req = db.get(SessionRequest, request_id)
    if req is None or (req.listener_id and req.listener_id != listener.id):
        raise not_found("Session request")
    # Idempotent: already declined.
    if req.status == SessionRequestStatus.declined:
        return OkResponse(ok=True)
    if req.status != SessionRequestStatus.pending:
        raise conflict("Request is not pending")
    req.status = SessionRequestStatus.declined
    if reason:
        req.message = (req.message or "") + f"\n[declined: {reason}]"
    db.commit()
    return OkResponse(ok=True)


def join_session(
    db: Session,
    user: User,
    session_id: UUID,
    settings: Settings,
) -> JoinCallResponse:
    session = db.get(VentingSession, session_id)
    if session is None:
        raise not_found("Session")
    if user.id not in {session.ventor_id, session.listener_id}:
        raise forbidden()
    if session.status not in {SessionStatus.upcoming, SessionStatus.live}:
        raise conflict("Session is not joinable")
    if session.status == SessionStatus.upcoming:
        session.status = SessionStatus.live
        session.started_at = session.started_at or _utc_now()
    if not session.call_channel_id:
        session.call_channel_id = f"venting-{secrets.token_hex(8)}"
    expires = _utc_now() + timedelta(hours=2)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "sid": str(session.id),
            "channel": session.call_channel_id,
            "type": "call",
            "exp": expires,
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    db.commit()
    return JoinCallResponse(
        call_token=token,
        channel_id=session.call_channel_id,
        expires_at=_iso(expires) or "",
        ice_servers=[{"urls": ["stun:stun.l.google.com:19302"]}],
    )


def end_session(
    db: Session,
    user: User,
    session_id: UUID,
    payload: EndSessionRequest | None = None,
) -> EndSessionResponse:
    session = db.get(VentingSession, session_id)
    if session is None:
        raise not_found("Session")
    if user.id not in {session.ventor_id, session.listener_id}:
        raise forbidden()
    # Idempotent: already completed.
    if session.status == SessionStatus.completed:
        return EndSessionResponse(session_id=str(session.id), status="completed")
    session.status = SessionStatus.completed
    session.ended_at = _utc_now()
    if payload and payload.duration_seconds is not None:
        session.actual_duration_seconds = payload.duration_seconds
    if payload and payload.ended_by:
        session.ended_by = payload.ended_by
    listener = db.get(ListenerProfile, session.listener_id)
    if listener is not None:
        listener.session_count = (listener.session_count or 0) + 1
    ventor = db.get(VentorProfile, session.ventor_id)
    if ventor is not None:
        ventor.completed_sessions_count = (ventor.completed_sessions_count or 0) + 1
        ventor.points_balance = (ventor.points_balance or 0) + 10
    db.commit()
    return EndSessionResponse(session_id=str(session.id), status="completed")


def rate_session(
    db: Session,
    ventor: User,
    session_id: UUID,
    payload: RatingRequest,
) -> RatingResponse:
    session = db.get(VentingSession, session_id)
    if session is None or session.ventor_id != ventor.id:
        raise not_found("Session")
    existing = (
        db.query(SessionRating).filter(SessionRating.session_id == session_id).one_or_none()
    )
    if existing is not None:
        raise conflict("Session already rated")

    tip = None
    if payload.tip_amount is not None:
        if payload.tip_amount not in {2, 5, 10}:
            raise validation_error("tip_amount must be 2, 5, or 10")
        tip = Decimal(str(payload.tip_amount))

    rating = SessionRating(
        session_id=session_id,
        ventor_id=ventor.id,
        listener_id=session.listener_id,
        stars=payload.stars,
        review=payload.review,
        tip_amount=tip,
    )
    db.add(rating)

    listener = db.get(ListenerProfile, session.listener_id)
    if listener is not None:
        total = (listener.rating_avg or 0) * (listener.rating_count or 0) + payload.stars
        listener.rating_count = (listener.rating_count or 0) + 1
        listener.rating_avg = Decimal(total) / Decimal(listener.rating_count)

    if tip is not None:
        payment = _payment_for(db, session_id)
        if payment is not None:
            payment.tip_amount = tip
            payment.amount_paid = Decimal(payment.amount_paid) + tip

    if payload.report is not None:
        try:
            reason = ReportReason(payload.report.reason)
        except ValueError as exc:
            raise validation_error("Invalid report reason") from exc
        db.add(
            SessionReport(
                session_id=session_id,
                reporter_user_id=ventor.id,
                reported_role=ReportedRole.listener,
                reason=reason,
                details=payload.report.details,
            )
        )

    db.commit()
    return RatingResponse(ok=True, tip_charged=float(tip) if tip is not None else None)


def submit_feedback(
    db: Session,
    listener: User,
    session_id: UUID,
    payload: FeedbackRequest,
) -> OkResponse:
    session = db.get(VentingSession, session_id)
    if session is None or session.listener_id != listener.id:
        raise not_found("Session")
    existing = (
        db.query(SessionListenerFeedback)
        .filter(SessionListenerFeedback.session_id == session_id)
        .one_or_none()
    )
    if existing is not None:
        raise conflict("Feedback already submitted")
    db.add(
        SessionListenerFeedback(
            session_id=session_id,
            listener_id=listener.id,
            ventor_id=session.ventor_id,
            stars=payload.stars,
            felt_heard=payload.felt_heard,
            talk_again=payload.talk_again,
        )
    )
    db.commit()
    return OkResponse(ok=True)


def report_session(
    db: Session,
    user: User,
    session_id: UUID,
    payload: ReportRequest,
) -> ReportResponse:
    session = db.get(VentingSession, session_id)
    if session is None:
        raise not_found("Session")
    if user.id not in {session.ventor_id, session.listener_id}:
        raise forbidden()
    try:
        reason = ReportReason(payload.reason)
        role = ReportedRole(payload.reported_role)
    except ValueError as exc:
        raise validation_error("Invalid reason or reported_role") from exc
    report = SessionReport(
        session_id=session_id,
        reporter_user_id=user.id,
        reported_role=role,
        reason=reason,
        details=payload.details,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportResponse(ok=True, report_id=str(report.id))
