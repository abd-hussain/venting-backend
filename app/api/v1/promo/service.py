"""Promo validation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import forbidden, not_found, validation_error
from app.models.auth import User
from app.models.enums import UserRole
from app.models.profiles import ListenerProfile
from app.models.promo import PromoCode


class ValidatePromoRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    listener_id: str
    duration_minutes: int = Field(ge=1, le=240)
    subtotal: float = Field(ge=0)


class ValidatePromoResponse(BaseModel):
    valid: bool
    discount_amount: float = 0
    label: str | None = None
    percent_off: int | None = None
    fixed_amount: float | None = None


def validate_promo(
    db: Session,
    user: User,
    payload: ValidatePromoRequest,
) -> ValidatePromoResponse:
    if user.role != UserRole.ventor:
        raise forbidden()

    try:
        listener_id = UUID(payload.listener_id)
    except ValueError as exc:
        raise validation_error("Invalid listener_id") from exc

    if db.get(ListenerProfile, listener_id) is None:
        raise not_found("Listener")

    code = payload.code.strip().upper()
    promo = (
        db.query(PromoCode)
        .filter(PromoCode.code == code)
        .one_or_none()
    )
    if promo is None or not promo.is_active:
        return ValidatePromoResponse(valid=False, discount_amount=0, label="Invalid code")

    now = datetime.now(timezone.utc)
    if promo.valid_from is not None and now < promo.valid_from:
        return ValidatePromoResponse(valid=False, discount_amount=0, label="Code not yet active")
    if promo.valid_to is not None and now > promo.valid_to:
        return ValidatePromoResponse(valid=False, discount_amount=0, label="Code expired")
    if (
        promo.max_redemptions is not None
        and (promo.redemption_count or 0) >= promo.max_redemptions
    ):
        return ValidatePromoResponse(valid=False, discount_amount=0, label="Code fully redeemed")

    subtotal = Decimal(str(payload.subtotal)).quantize(Decimal("0.01"))
    discount = Decimal("0")
    if promo.percent_off:
        discount += (subtotal * Decimal(promo.percent_off) / Decimal(100)).quantize(
            Decimal("0.01")
        )
    if promo.fixed_amount is not None:
        discount += Decimal(promo.fixed_amount)
    discount = min(discount, subtotal)

    parts: list[str] = []
    if promo.percent_off:
        parts.append(f"{promo.percent_off}% off")
    if promo.fixed_amount is not None:
        parts.append(f"${float(promo.fixed_amount):.2f} off")
    label = " · ".join(parts) if parts else promo.code

    return ValidatePromoResponse(
        valid=True,
        discount_amount=float(discount),
        label=label,
        percent_off=promo.percent_off,
        fixed_amount=float(promo.fixed_amount) if promo.fixed_amount is not None else None,
    )
