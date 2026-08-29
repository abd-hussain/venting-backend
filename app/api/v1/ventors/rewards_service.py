"""Ventor rewards & invites."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, offer_expired, validation_error
from app.models.enums import PointPurchaseStatus
from app.models.profiles import VentorProfile
from app.models.rewards import (
    InviteCode,
    InviteEvent,
    PointPackage,
    PointPurchase,
    RewardOffer,
    RewardTrade,
)
from app.services.reward_offers import is_offer_expired, offer_is_redeemable, utc_now
from pydantic import BaseModel, Field

EARN_RULES = {
    "points_per_session": 10,
    "points_per_friend_register": 50,
    "points_per_invite_first_session": 75,
    "points_per_friend_booking": 100,
}


class RewardOfferOut(BaseModel):
    id: str
    kind: str
    points_cost: int
    percent_off: int | None = None
    free_minutes: int | None = None
    audience: dict
    is_welcome_gift: bool
    expires_at: str | None = None


class RewardsResponse(BaseModel):
    points: int
    completed_sessions: int
    active_offer_id: str | None = None
    welcome_gift_claimed: bool
    offers: list[RewardOfferOut]
    earn_rules: dict


class RedeemRequest(BaseModel):
    offer_id: str


class TradeOut(BaseModel):
    id: str
    offer_id: str
    points_spent: int
    traded_at: str
    is_welcome_gift: bool | None = None


class RedeemResponse(BaseModel):
    points_remaining: int
    trade: TradeOut
    active_offer_id: str


class TradesResponse(BaseModel):
    items: list[TradeOut]


class InviteItem(BaseModel):
    id: str
    name: str
    status: str
    points_earned: int


class InvitesResponse(BaseModel):
    invite_code: str
    invite_link: str
    total_invited: int
    invite_points_earned: int
    items: list[InviteItem]


class InviteCodeResponse(BaseModel):
    invite_code: str
    invite_link: str


class PointPackageOut(BaseModel):
    id: str
    points: int
    price_usd: float
    bonus_percent: int | None = None
    sort_order: int


class PointPackagesResponse(BaseModel):
    packages: list[PointPackageOut]


class PurchasePointsRequest(BaseModel):
    package_id: str = Field(min_length=1, max_length=64)
    payment_reference: str | None = Field(default=None, max_length=128)


class PointPurchaseOut(BaseModel):
    id: str
    package_id: str
    points_added: int
    price_usd: float
    purchased_at: str


class PurchasePointsResponse(BaseModel):
    points: int
    purchase: PointPurchaseOut


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_rewards(db: Session, profile: VentorProfile) -> RewardsResponse:
    now = utc_now()
    active_id = profile.active_reward_offer_id
    offers = (
        db.query(RewardOffer)
        .filter(RewardOffer.is_active.is_(True))
        .order_by(RewardOffer.points_cost.asc())
        .all()
    )
    visible_offers = [
        offer
        for offer in offers
        if not is_offer_expired(offer, now=now) or offer.id == active_id
    ]
    welcome_claimed = (
        db.query(RewardTrade)
        .filter(
            RewardTrade.ventor_id == profile.user_id,
            RewardTrade.is_welcome_gift.is_(True),
        )
        .first()
        is not None
    )
    return RewardsResponse(
        points=profile.points_balance,
        completed_sessions=profile.completed_sessions_count,
        active_offer_id=str(profile.active_reward_offer_id)
        if profile.active_reward_offer_id
        else None,
        welcome_gift_claimed=welcome_claimed,
        offers=[
            RewardOfferOut(
                id=str(o.id),
                kind=o.kind.value,
                points_cost=o.points_cost,
                percent_off=o.percent_off,
                free_minutes=o.free_minutes,
                audience={
                    "min_tier": o.min_tier.value if o.min_tier else None,
                    "max_tier": o.max_tier.value if o.max_tier else None,
                },
                is_welcome_gift=o.is_welcome_gift,
                expires_at=_iso(o.expires_at) if o.expires_at is not None else None,
            )
            for o in visible_offers
        ],
        earn_rules=EARN_RULES,
    )


def redeem_offer(db: Session, profile: VentorProfile, payload: RedeemRequest) -> RedeemResponse:
    try:
        offer_id = UUID(payload.offer_id)
    except ValueError as exc:
        raise validation_error("Invalid offer_id") from exc
    offer = db.get(RewardOffer, offer_id)
    if offer is None or not offer.is_active:
        raise not_found("Offer")

    # Idempotent: already redeemed this offer — return latest trade.
    existing = (
        db.query(RewardTrade)
        .filter(
            RewardTrade.ventor_id == profile.user_id,
            RewardTrade.offer_id == offer.id,
        )
        .order_by(RewardTrade.traded_at.desc())
        .first()
    )
    if existing is not None:
        if profile.active_reward_offer_id != offer.id:
            profile.active_reward_offer_id = offer.id
            db.commit()
        return RedeemResponse(
            points_remaining=profile.points_balance,
            trade=TradeOut(
                id=str(existing.id),
                offer_id=str(existing.offer_id),
                points_spent=existing.points_spent,
                traded_at=_iso(existing.traded_at),
                is_welcome_gift=existing.is_welcome_gift,
            ),
            active_offer_id=str(offer.id),
        )

    if not offer_is_redeemable(offer):
        raise offer_expired()

    if offer.is_welcome_gift:
        points_spent = 0
    else:
        if profile.points_balance < offer.points_cost:
            raise validation_error("Not enough points")
        points_spent = offer.points_cost
        profile.points_balance -= points_spent

    trade = RewardTrade(
        ventor_id=profile.user_id,
        offer_id=offer.id,
        points_spent=points_spent,
        is_welcome_gift=offer.is_welcome_gift,
    )
    db.add(trade)
    profile.active_reward_offer_id = offer.id
    db.commit()
    db.refresh(trade)
    return RedeemResponse(
        points_remaining=profile.points_balance,
        trade=TradeOut(
            id=str(trade.id),
            offer_id=str(trade.offer_id),
            points_spent=trade.points_spent,
            traded_at=_iso(trade.traded_at),
            is_welcome_gift=trade.is_welcome_gift,
        ),
        active_offer_id=str(offer.id),
    )


def list_trades(db: Session, profile: VentorProfile) -> TradesResponse:
    rows = (
        db.query(RewardTrade)
        .filter(RewardTrade.ventor_id == profile.user_id)
        .order_by(RewardTrade.traded_at.desc())
        .all()
    )
    return TradesResponse(
        items=[
            TradeOut(
                id=str(r.id),
                offer_id=str(r.offer_id),
                points_spent=r.points_spent,
                traded_at=_iso(r.traded_at),
                is_welcome_gift=r.is_welcome_gift,
            )
            for r in rows
        ]
    )


def _ensure_invite(db: Session, profile: VentorProfile) -> InviteCode:
    row = db.query(InviteCode).filter(InviteCode.ventor_id == profile.user_id).one_or_none()
    if row is not None:
        return row
    code = f"{profile.nickname[:3].upper()}-{secrets.token_hex(3).upper()}"
    row = InviteCode(
        ventor_id=profile.user_id,
        code=code,
        invite_link=f"https://venting.app/invite/{code}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_invites(db: Session, profile: VentorProfile) -> InvitesResponse:
    invite = _ensure_invite(db, profile)
    events = (
        db.query(InviteEvent)
        .filter(InviteEvent.inviter_ventor_id == profile.user_id)
        .order_by(InviteEvent.created_at.desc())
        .all()
    )
    return InvitesResponse(
        invite_code=invite.code,
        invite_link=invite.invite_link,
        total_invited=len(events),
        invite_points_earned=sum(e.points_earned for e in events),
        items=[
            InviteItem(
                id=str(e.id),
                name=e.invitee_display_name,
                status=e.status.value,
                points_earned=e.points_earned,
            )
            for e in events
        ],
    )


def _purchase_public_id(row: PointPurchase) -> str:
    return f"pp_{row.id.hex[:24]}"


def list_point_packages(db: Session) -> PointPackagesResponse:
    rows = (
        db.query(PointPackage)
        .filter(PointPackage.is_active.is_(True))
        .order_by(PointPackage.sort_order.asc(), PointPackage.code.asc())
        .all()
    )
    return PointPackagesResponse(
        packages=[
            PointPackageOut(
                id=row.code,
                points=row.points,
                price_usd=float(row.price_usd),
                bonus_percent=row.bonus_percent,
                sort_order=row.sort_order,
            )
            for row in rows
        ]
    )


def purchase_points(
    db: Session,
    profile: VentorProfile,
    payload: PurchasePointsRequest,
) -> PurchasePointsResponse:
    if payload.payment_reference:
        existing = (
            db.query(PointPurchase)
            .filter(PointPurchase.payment_reference == payload.payment_reference)
            .one_or_none()
        )
        if existing is not None:
            if existing.ventor_id != profile.user_id:
                raise conflict(
                    "Duplicate payment reference",
                    en="This payment was already processed",
                    ar="تمت معالجة هذا الدفع مسبقاً",
                )
            db.refresh(profile)
            return PurchasePointsResponse(
                points=profile.points_balance,
                purchase=PointPurchaseOut(
                    id=_purchase_public_id(existing),
                    package_id=existing.package_code,
                    points_added=existing.points_added,
                    price_usd=float(existing.price_usd),
                    purchased_at=_iso(existing.purchased_at),
                ),
            )

    package = (
        db.query(PointPackage)
        .filter(
            PointPackage.code == payload.package_id,
            PointPackage.is_active.is_(True),
        )
        .one_or_none()
    )
    if package is None:
        raise not_found("Package")

    now = datetime.now(timezone.utc)
    purchase = PointPurchase(
        ventor_id=profile.user_id,
        package_id=package.id,
        package_code=package.code,
        points_added=package.points,
        price_usd=package.price_usd,
        payment_provider="sandbox",
        payment_reference=payload.payment_reference,
        status=PointPurchaseStatus.completed,
        purchased_at=now,
    )
    db.add(purchase)
    profile.points_balance += package.points
    db.commit()
    db.refresh(purchase)
    db.refresh(profile)
    return PurchasePointsResponse(
        points=profile.points_balance,
        purchase=PointPurchaseOut(
            id=_purchase_public_id(purchase),
            package_id=purchase.package_code,
            points_added=purchase.points_added,
            price_usd=float(purchase.price_usd),
            purchased_at=_iso(purchase.purchased_at),
        ),
    )


def refresh_invite_code(db: Session, profile: VentorProfile) -> InviteCodeResponse:
    invite = _ensure_invite(db, profile)
    invite.code = f"{profile.nickname[:3].upper()}-{secrets.token_hex(3).upper()}"
    invite.invite_link = f"https://venting.app/invite/{invite.code}"
    invite.refreshed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invite)
    return InviteCodeResponse(invite_code=invite.code, invite_link=invite.invite_link)
