"""Database-backed admin dashboard statistics."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.v1.admin.stats.schemas import (
    Granularity,
    ListenerStats,
    NamedCount,
    OverviewStats,
    RevenueBucket,
    RevenueStats,
    SessionsBucket,
    SessionsStats,
    UsersBucket,
    UsersStats,
    WellnessStats,
)
from app.core.errors import validation_error
from app.models.auth import User
from app.models.enums import PaymentStatus, ProfileStatus, SessionStatus
from app.models.profiles import ListenerProfile
from app.models.sessions import Session as VentingSession
from app.models.sessions import SessionPayment, SessionReport
from app.models.ventor_wellness import MoodCheckin


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _range(
    from_date: date | None,
    to_date: date | None,
) -> tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    start_date = from_date or today - timedelta(days=29)
    end_date = to_date or today
    if start_date > end_date:
        raise validation_error("'from' must be on or before 'to'")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


def get_overview(db: Session) -> OverviewStats:
    today = datetime.now(timezone.utc).date()
    day_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    users = (
        db.query(func.count(User.id))
        .filter(User.deleted_at.is_(None))
        .scalar()
        or 0
    )
    sessions_today = (
        db.query(func.count(VentingSession.id))
        .filter(
            VentingSession.scheduled_at >= day_start,
            VentingSession.scheduled_at < day_end,
        )
        .scalar()
        or 0
    )
    gmv = (
        db.query(func.coalesce(func.sum(SessionPayment.amount_paid), 0))
        .filter(SessionPayment.status == PaymentStatus.paid)
        .scalar()
        or 0
    )
    pending_reviews = (
        db.query(func.count(ListenerProfile.user_id))
        .filter(ListenerProfile.profile_status == ProfileStatus.under_review)
        .scalar()
        or 0
    )
    open_reports = (
        db.query(func.count(SessionReport.id))
        .filter(SessionReport.status == "open")
        .scalar()
        or 0
    )
    return OverviewStats(
        users=int(users),
        sessions_today=int(sessions_today),
        gmv=float(gmv),
        pending_reviews=int(pending_reviews),
        open_reports=int(open_reports),
    )


def get_users_stats(
    db: Session,
    *,
    from_date: date | None,
    to_date: date | None,
    granularity: Granularity,
) -> UsersStats:
    start, end = _range(from_date, to_date)
    period = func.date_trunc(granularity, User.created_at)
    rows = (
        db.query(
            period.label("period"),
            User.role,
            func.count(User.id).label("count"),
        )
        .filter(User.created_at >= start, User.created_at < end)
        .group_by(period, User.role)
        .order_by(period)
        .all()
    )
    buckets: dict[datetime, dict[str, int]] = {}
    for row in rows:
        bucket = buckets.setdefault(row.period, {"ventor": 0, "listener": 0})
        bucket[_value(row.role)] = int(row.count)
    items = [
        UsersBucket(
            period=key,
            ventors=counts["ventor"],
            listeners=counts["listener"],
            total=counts["ventor"] + counts["listener"],
        )
        for key, counts in buckets.items()
    ]
    now = datetime.now(timezone.utc)
    active = (
        db.query(func.count(User.id))
        .filter(
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            (User.suspended_until.is_(None) | (User.suspended_until <= now)),
        )
        .scalar()
        or 0
    )
    suspended = (
        db.query(func.count(User.id))
        .filter(
            User.deleted_at.is_(None),
            ((User.is_active.is_(False)) | (User.suspended_until > now)),
        )
        .scalar()
        or 0
    )
    return UsersStats(items=items, active=int(active), suspended=int(suspended))


def get_sessions_stats(
    db: Session,
    *,
    from_date: date | None,
    to_date: date | None,
    granularity: Granularity,
) -> SessionsStats:
    start, end = _range(from_date, to_date)
    period = func.date_trunc(granularity, VentingSession.created_at)
    rows = (
        db.query(
            period.label("period"),
            VentingSession.status,
            func.count(VentingSession.id).label("count"),
        )
        .filter(VentingSession.created_at >= start, VentingSession.created_at < end)
        .group_by(period, VentingSession.status)
        .order_by(period)
        .all()
    )
    statuses = [status.value for status in SessionStatus]
    buckets: dict[datetime, dict[str, int]] = {}
    for row in rows:
        bucket = buckets.setdefault(row.period, {status: 0 for status in statuses})
        bucket[_value(row.status)] = int(row.count)
    return SessionsStats(
        items=[
            SessionsBucket(
                period=key,
                total=sum(counts.values()),
                **counts,
            )
            for key, counts in buckets.items()
        ]
    )


def get_revenue_stats(
    db: Session,
    *,
    from_date: date | None,
    to_date: date | None,
    granularity: Granularity,
) -> RevenueStats:
    start, end = _range(from_date, to_date)
    period = func.date_trunc(granularity, SessionPayment.created_at)
    payment_amount = case(
        (
            SessionPayment.status.in_([PaymentStatus.paid, PaymentStatus.refunded]),
            SessionPayment.amount_paid,
        ),
        else_=0,
    )
    rows = (
        db.query(
            period.label("period"),
            func.coalesce(func.sum(payment_amount), 0).label("payments"),
            func.coalesce(func.sum(SessionPayment.tip_amount), 0).label("tips"),
            func.coalesce(func.sum(SessionPayment.refunded_amount), 0).label("refunds"),
            func.coalesce(func.sum(SessionPayment.discount_amount), 0).label("discounts"),
        )
        .filter(SessionPayment.created_at >= start, SessionPayment.created_at < end)
        .group_by(period)
        .order_by(period)
        .all()
    )
    items = [
        RevenueBucket(
            period=row.period,
            payments=float(row.payments),
            tips=float(row.tips),
            refunds=float(row.refunds),
            discounts=float(row.discounts),
        )
        for row in rows
    ]
    return RevenueStats(
        items=items,
        payments=sum(item.payments for item in items),
        tips=sum(item.tips for item in items),
        refunds=sum(item.refunds for item in items),
        discounts=sum(item.discounts for item in items),
    )


def get_listener_stats(db: Session) -> ListenerStats:
    online = (
        db.query(func.count(ListenerProfile.user_id))
        .filter(ListenerProfile.is_online.is_(True))
        .scalar()
        or 0
    )
    tier_rows = (
        db.query(ListenerProfile.current_tier, func.count(ListenerProfile.user_id))
        .group_by(ListenerProfile.current_tier)
        .order_by(ListenerProfile.current_tier)
        .all()
    )
    country_name = func.coalesce(ListenerProfile.country_iso, "unknown")
    country_rows = (
        db.query(country_name.label("country"), func.count(ListenerProfile.user_id))
        .group_by(country_name)
        .order_by(func.count(ListenerProfile.user_id).desc())
        .all()
    )
    status_rows = (
        db.query(ListenerProfile.profile_status, func.count(ListenerProfile.user_id))
        .group_by(ListenerProfile.profile_status)
        .order_by(ListenerProfile.profile_status)
        .all()
    )
    return ListenerStats(
        online=int(online),
        by_tier=[NamedCount(name=_value(name), count=int(count)) for name, count in tier_rows],
        by_country=[NamedCount(name=name, count=int(count)) for name, count in country_rows],
        approval_funnel=[
            NamedCount(name=_value(name), count=int(count)) for name, count in status_rows
        ],
    )


def get_wellness_stats(
    db: Session,
    *,
    from_date: date | None,
    to_date: date | None,
) -> WellnessStats:
    start, end = _range(from_date, to_date)
    rows = (
        db.query(MoodCheckin.mood, func.count(MoodCheckin.id))
        .filter(MoodCheckin.checked_in_at >= start, MoodCheckin.checked_in_at < end)
        .group_by(MoodCheckin.mood)
        .order_by(MoodCheckin.mood)
        .all()
    )
    distribution = [
        NamedCount(name=_value(mood), count=int(count)) for mood, count in rows
    ]
    return WellnessStats(
        total=sum(item.count for item in distribution),
        distribution=distribution,
    )
