"""Earnings & payouts for listeners."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import not_found, validation_error
from app.core.pagination import clamp_page
from app.models.earnings import ListenerWallet, Payout, PayoutMethod, WalletLedgerEntry
from app.models.enums import LedgerEntryType, PayoutMethodType, PayoutStatus, SessionStatus
from app.models.profiles import ListenerProfile
from app.models.sessions import Session as VentingSession
from pydantic import BaseModel, Field

TIER_TABLE = [
    {"id": "starter", "min_sessions": 0, "min_rating": 0.0, "hourly_rate": 15.0},
    {"id": "rising", "min_sessions": 10, "min_rating": 4.2, "hourly_rate": 20.0},
    {"id": "trusted", "min_sessions": 25, "min_rating": 4.4, "hourly_rate": 25.0},
    {"id": "expert", "min_sessions": 50, "min_rating": 4.6, "hourly_rate": 32.0},
    {"id": "elite", "min_sessions": 100, "min_rating": 4.7, "hourly_rate": 40.0},
]


class TierInfo(BaseModel):
    id: str
    min_sessions: int | None = None
    min_rating: float | None = None
    hourly_rate: float


class CurrentTier(BaseModel):
    id: str
    hourly_rate: float


class EarningsSummary(BaseModel):
    total_earnings: float
    trend_percent: float
    sessions: int
    hours: float
    rating: float
    current_tier: CurrentTier
    tiers: list[TierInfo]


class ChartPoint(BaseModel):
    label: str
    amount: float


class EarningsChart(BaseModel):
    points: list[ChartPoint]


class PayoutBalances(BaseModel):
    available: float
    pending: float
    lifetime: float


class PayoutMethodItem(BaseModel):
    id: str
    type: str
    account_holder_name: str | None = None
    bank_name: str | None = None
    iban_or_account: str | None = None
    swift_code: str | None = None
    paypal_email: str | None = None
    label: str


class PayoutMethodsResponse(BaseModel):
    default_method: PayoutMethodItem | None = None
    methods: list[PayoutMethodItem]


class UpsertPayoutMethodRequest(BaseModel):
    type: str = "bank"
    account_holder_name: str | None = None
    bank_name: str | None = None
    iban_or_account_number: str | None = None
    iban_or_account: str | None = None
    swift_code: str | None = None
    paypal_email: str | None = None
    label: str | None = None
    is_default: bool = True


class PayoutItem(BaseModel):
    id: str
    amount: float
    date: str
    status: str
    method_label: str
    reference: str | None = None


class PayoutsResponse(BaseModel):
    items: list[PayoutItem]
    total: int = 0
    page: int = 1
    page_size: int = 20


class CreatePayoutRequest(BaseModel):
    amount: float = Field(gt=0)
    payout_method_id: str


def _wallet(db: Session, listener_id: UUID) -> ListenerWallet:
    wallet = db.get(ListenerWallet, listener_id)
    if wallet is None:
        wallet = ListenerWallet(listener_id=listener_id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def _method_item(row: PayoutMethod) -> PayoutMethodItem:
    return PayoutMethodItem(
        id=str(row.id),
        type=row.type.value,
        account_holder_name=row.account_holder_name,
        bank_name=row.bank_name,
        iban_or_account=row.iban_or_account,
        swift_code=row.swift_code,
        paypal_email=row.paypal_email,
        label=row.label,
    )


def get_earnings_summary(db: Session, profile: ListenerProfile) -> EarningsSummary:
    wallet = _wallet(db, profile.user_id)
    completed = (
        db.query(VentingSession)
        .filter(
            VentingSession.listener_id == profile.user_id,
            VentingSession.status == SessionStatus.completed,
        )
        .all()
    )
    sessions = len(completed)
    minutes = sum((s.actual_duration_seconds or s.duration_minutes * 60) / 60 for s in completed)
    tier_id = profile.current_tier.value if profile.current_tier else "starter"
    hourly = next((t["hourly_rate"] for t in TIER_TABLE if t["id"] == tier_id), 15.0)
    return EarningsSummary(
        total_earnings=float(wallet.lifetime_earned or 0),
        trend_percent=0.0,
        sessions=sessions,
        hours=round(minutes / 60, 2),
        rating=float(profile.rating_avg or 0),
        current_tier=CurrentTier(id=tier_id, hourly_rate=hourly),
        tiers=[TierInfo(**t) for t in TIER_TABLE],
    )


def get_earnings_chart(
    db: Session,
    profile: ListenerProfile,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> EarningsChart:
    today = datetime.now(timezone.utc).date()
    start = from_date or (today - timedelta(days=6))
    end = to_date or today
    if end < start:
        start, end = end, start
    points: list[ChartPoint] = []
    day = start
    while day <= end:
        day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        amount = (
            db.query(func.coalesce(func.sum(WalletLedgerEntry.amount), 0))
            .filter(
                WalletLedgerEntry.listener_id == profile.user_id,
                WalletLedgerEntry.type == LedgerEntryType.session_earning,
                WalletLedgerEntry.created_at >= day_start,
                WalletLedgerEntry.created_at < day_end,
            )
            .scalar()
        )
        points.append(ChartPoint(label=day.isoformat(), amount=float(amount or 0)))
        day += timedelta(days=1)
    return EarningsChart(points=points)


def get_payout_balances(db: Session, profile: ListenerProfile) -> PayoutBalances:
    wallet = _wallet(db, profile.user_id)
    return PayoutBalances(
        available=float(wallet.available_balance or 0),
        pending=float(wallet.pending_balance or 0),
        lifetime=float(wallet.lifetime_earned or 0),
    )


def list_payout_methods(db: Session, profile: ListenerProfile) -> PayoutMethodsResponse:
    rows = (
        db.query(PayoutMethod)
        .filter(
            PayoutMethod.listener_id == profile.user_id,
            PayoutMethod.deleted_at.is_(None),
        )
        .order_by(PayoutMethod.is_default.desc(), PayoutMethod.created_at.desc())
        .all()
    )
    methods = [_method_item(r) for r in rows]
    default = next((m for m, r in zip(methods, rows) if r.is_default), methods[0] if methods else None)
    return PayoutMethodsResponse(default_method=default, methods=methods)


def upsert_payout_method(
    db: Session,
    profile: ListenerProfile,
    payload: UpsertPayoutMethodRequest,
) -> PayoutMethodItem:
    try:
        method_type = PayoutMethodType(payload.type)
    except ValueError as exc:
        raise validation_error("type must be bank or paypal") from exc

    iban = payload.iban_or_account or payload.iban_or_account_number
    if method_type == PayoutMethodType.bank:
        if not payload.account_holder_name or not payload.bank_name or not iban:
            raise validation_error("Bank methods require account_holder_name, bank_name, iban")
        label = payload.label or f"{payload.bank_name} • {iban[-4:]}"
    else:
        if not payload.paypal_email:
            raise validation_error("PayPal methods require paypal_email")
        label = payload.label or payload.paypal_email

    if payload.is_default:
        db.query(PayoutMethod).filter(
            PayoutMethod.listener_id == profile.user_id,
            PayoutMethod.deleted_at.is_(None),
        ).update({PayoutMethod.is_default: False}, synchronize_session=False)

    row = PayoutMethod(
        listener_id=profile.user_id,
        type=method_type,
        is_default=payload.is_default,
        account_holder_name=payload.account_holder_name,
        bank_name=payload.bank_name,
        iban_or_account=iban,
        swift_code=payload.swift_code,
        paypal_email=payload.paypal_email,
        label=label,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _method_item(row)


def list_payouts(
    db: Session,
    profile: ListenerProfile,
    *,
    page: int = 1,
    page_size: int = 20,
) -> PayoutsResponse:
    page, page_size = clamp_page(page, page_size)
    query = db.query(Payout).filter(Payout.listener_id == profile.user_id)
    total = query.with_entities(func.count(Payout.id)).scalar() or 0
    rows = (
        query.order_by(Payout.requested_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PayoutsResponse(
        items=[
            PayoutItem(
                id=str(r.id),
                amount=float(r.amount),
                date=r.requested_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                status=r.status.value,
                method_label=r.method_label,
                reference=r.reference,
            )
            for r in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def create_payout(
    db: Session,
    profile: ListenerProfile,
    payload: CreatePayoutRequest,
) -> PayoutItem:
    try:
        method_id = UUID(payload.payout_method_id)
    except ValueError as exc:
        raise validation_error("Invalid payout_method_id") from exc
    method = db.get(PayoutMethod, method_id)
    if method is None or method.listener_id != profile.user_id or method.deleted_at is not None:
        raise not_found("Payout method")

    wallet = _wallet(db, profile.user_id)
    amount = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if amount > Decimal(wallet.available_balance or 0):
        raise validation_error("Insufficient available balance")

    wallet.available_balance = Decimal(wallet.available_balance) - amount
    wallet.pending_balance = Decimal(wallet.pending_balance or 0) + amount
    payout = Payout(
        listener_id=profile.user_id,
        payout_method_id=method.id,
        amount=amount,
        status=PayoutStatus.pending,
        method_label=method.label,
    )
    db.add(payout)
    db.flush()
    db.add(
        WalletLedgerEntry(
            listener_id=profile.user_id,
            type=LedgerEntryType.payout,
            amount=-amount,
            balance_after=wallet.available_balance,
            payout_id=payout.id,
            idempotency_key=f"payout-{payout.id}",
        )
    )
    db.commit()
    db.refresh(payout)
    return PayoutItem(
        id=str(payout.id),
        amount=float(payout.amount),
        date=payout.requested_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        status=payout.status.value,
        method_label=payout.method_label,
        reference=payout.reference,
    )
