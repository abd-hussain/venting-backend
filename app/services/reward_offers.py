"""Reward offer expiration — UTC comparisons and redeemability checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.errors import validation_error
from app.models.rewards import RewardOffer


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_expires_at(
    value: datetime | None,
    *,
    reject_past: bool = False,
) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        normalized = value.replace(tzinfo=timezone.utc)
    else:
        normalized = value.astimezone(timezone.utc)
    if reject_past and normalized <= utc_now() - timedelta(minutes=1):
        raise validation_error(
            "expires_at must be in the future",
            en="expires_at must be in the future",
            ar="يجب أن يكون تاريخ انتهاء العرض في المستقبل",
        )
    return normalized


def is_offer_expired(offer: RewardOffer, *, now: datetime | None = None) -> bool:
    if offer.expires_at is None:
        return False
    current = now or utc_now()
    expires_at = offer.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= current


def offer_is_redeemable(offer: RewardOffer, *, now: datetime | None = None) -> bool:
    return offer.is_active and not is_offer_expired(offer, now=now)
