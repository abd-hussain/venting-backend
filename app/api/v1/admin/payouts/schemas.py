from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.pagination import Paginated
from app.models.enums import LedgerEntryType, PayoutMethodType, PayoutStatus


class PayoutMethodResponse(BaseModel):
    id: str
    type: PayoutMethodType
    label: str
    account_holder_name: str | None = None
    bank_name: str | None = None
    iban_or_account: str | None = None
    swift_code: str | None = None
    paypal_email: str | None = None


class PayoutResponse(BaseModel):
    id: str
    listener_id: str
    amount: Decimal
    status: PayoutStatus
    method_label: str
    reference: str | None = None
    requested_at: datetime
    processed_at: datetime | None = None
    failure_reason: str | None = None
    reviewed_by_admin_id: str | None = None


class PayoutDetailResponse(PayoutResponse):
    method: PayoutMethodResponse


class PayoutListResponse(Paginated[PayoutResponse]):
    pass


class ApprovePayoutRequest(BaseModel):
    reference: str | None = Field(default=None, max_length=64)


class RejectPayoutRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class WalletLedgerEntryResponse(BaseModel):
    id: str
    type: LedgerEntryType
    amount: Decimal
    balance_after: Decimal
    session_id: str | None = None
    payout_id: str | None = None
    idempotency_key: str
    note: str | None = None
    created_at: datetime


class WalletResponse(BaseModel):
    listener_id: str
    available_balance: Decimal
    pending_balance: Decimal
    lifetime_earned: Decimal
    ledger: Paginated[WalletLedgerEntryResponse]


class AdjustWalletRequest(BaseModel):
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    note: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=64)

    @field_validator("amount")
    @classmethod
    def amount_must_be_nonzero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount must not be zero")
        return value


class WalletAdjustmentResponse(BaseModel):
    wallet: WalletResponse
    entry: WalletLedgerEntryResponse


class EarningsTiersResponse(BaseModel):
    tiers: dict[str, dict[str, int | float]]
