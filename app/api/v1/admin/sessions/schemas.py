"""Request and response models for admin session operations."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.pagination import Paginated


class SessionItem(BaseModel):
    id: str
    request_id: str | None
    ventor_id: str
    listener_id: str
    status: str
    duration_minutes: int
    actual_duration_seconds: int | None
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    amount_paid: float | None = None
    currency: str | None = None


class SessionList(Paginated[SessionItem]):
    pass


class PaymentDetail(BaseModel):
    id: str
    status: str
    currency: str
    session_price: float
    voice_change_fee: float
    discount_amount: float
    tip_amount: float
    amount_paid: float
    refunded_amount: float
    provider: str | None
    provider_payment_id: str | None


class SessionRatingDetail(BaseModel):
    stars: int
    review: str | None
    tip_amount: float | None
    created_at: datetime


class ListenerFeedbackDetail(BaseModel):
    stars: int
    felt_heard: bool
    talk_again: bool
    created_at: datetime


class SessionDetail(SessionItem):
    time_mode: str
    call_mode: str
    speech_language: str
    voice_change_enabled: bool
    message: str | None
    chosen_reason: str | None
    tags: list[str] | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    payment: PaymentDetail | None
    rating: SessionRatingDetail | None
    listener_feedback: ListenerFeedbackDetail | None


class CancelSessionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class RefundSessionRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)


class SessionActionResponse(BaseModel):
    id: str
    status: str
    refunded_amount: float | None = None


class SessionRequestItem(BaseModel):
    id: str
    ventor_id: str
    listener_id: str | None
    session_id: str | None
    status: str
    duration_minutes: int
    scheduled_at: datetime | None
    quoted_amount: float
    expires_at: datetime | None
    created_at: datetime


class SessionRequestList(Paginated[SessionRequestItem]):
    pass


class TimelineEvent(BaseModel):
    key: str
    at: datetime


class SessionTimeline(BaseModel):
    session_id: str
    items: list[TimelineEvent]
