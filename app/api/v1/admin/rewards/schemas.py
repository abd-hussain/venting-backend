from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.core.pagination import Paginated
from app.models.enums import EarningsTier, RewardOfferKind


class RewardOfferResponse(BaseModel):
    id: str
    code: str
    kind: RewardOfferKind
    points_cost: int
    percent_off: int | None = None
    free_minutes: int | None = None
    min_tier: EarningsTier | None = None
    max_tier: EarningsTier | None = None
    is_welcome_gift: bool
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime


class RewardOfferList(Paginated[RewardOfferResponse]):
    pass


class RewardOfferCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    kind: RewardOfferKind
    points_cost: int = Field(ge=0)
    percent_off: int | None = Field(default=None, ge=1, le=100)
    free_minutes: int | None = Field(default=None, ge=1)
    min_tier: EarningsTier | None = None
    max_tier: EarningsTier | None = None
    is_welcome_gift: bool = False
    is_active: bool = True
    expires_at: datetime | None = None


class RewardOfferUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    kind: RewardOfferKind | None = None
    points_cost: int | None = Field(default=None, ge=0)
    percent_off: int | None = Field(default=None, ge=1, le=100)
    free_minutes: int | None = Field(default=None, ge=1)
    min_tier: EarningsTier | None = None
    max_tier: EarningsTier | None = None
    is_welcome_gift: bool | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_change(self) -> "RewardOfferUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class RewardTradeResponse(BaseModel):
    id: str
    ventor_id: str
    offer_id: str
    points_spent: int
    is_welcome_gift: bool
    traded_at: datetime


class RewardTradeList(Paginated[RewardTradeResponse]):
    pass


class PromoCodeResponse(BaseModel):
    id: str
    code: str
    percent_off: int | None = None
    fixed_amount: Decimal | None = None
    max_redemptions: int | None = None
    redemption_count: int
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool
    created_at: datetime


class PromoCodeList(Paginated[PromoCodeResponse]):
    pass


class PromoCodeCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    percent_off: int | None = Field(default=None, ge=1, le=100)
    fixed_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    max_redemptions: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_discount_and_dates(self) -> "PromoCodeCreateRequest":
        if self.percent_off is None and self.fixed_amount is None:
            raise ValueError("percent_off or fixed_amount is required")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


class PromoCodeUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    percent_off: int | None = Field(default=None, ge=1, le=100)
    fixed_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    max_redemptions: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change_and_validate_dates(self) -> "PromoCodeUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


class PromoRedemptionResponse(BaseModel):
    id: str
    promo_code_id: str
    ventor_id: str
    session_id: str | None = None
    discount_amount: Decimal
    created_at: datetime


class PromoRedemptionList(Paginated[PromoRedemptionResponse]):
    pass


class PointPackageResponse(BaseModel):
    id: str
    code: str
    points: int
    price_usd: Decimal
    bonus_percent: int | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PointPackageList(Paginated[PointPackageResponse]):
    pass


class PointPackageCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    points: int = Field(ge=1)
    price_usd: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    bonus_percent: int | None = Field(default=None, ge=1, le=100)
    sort_order: int = 0
    is_active: bool = True


class PointPackageUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    points: int | None = Field(default=None, ge=1)
    price_usd: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    bonus_percent: int | None = Field(default=None, ge=1, le=100)
    sort_order: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "PointPackageUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self
