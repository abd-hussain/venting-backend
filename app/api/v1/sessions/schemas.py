"""Sessions request/response schemas."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TimeMode(str, Enum):
    nearest = "nearest"
    scheduled = "scheduled"


class CallModeOut(str, Enum):
    voice = "voice"
    video = "video"


class BookSessionRequest(BaseModel):
    listener_id: str
    duration_minutes: int = Field(ge=5, le=120)
    time_mode: TimeMode
    scheduled_at: str | None = None
    call_mode: CallModeOut = CallModeOut.voice
    speech_language: str
    voice_change_enabled: bool = False
    promo_code: str | None = None
    reward_offer_id: str | None = None


class PaymentInfo(BaseModel):
    amount_paid: float
    currency: str = "USD"
    voice_change_fee: float
    discount_amount: float


class VentorBookedSession(BaseModel):
    id: str
    listener_id: str
    listener_name: str
    listener_avatar_url: str | None = None
    duration_minutes: int
    status: str
    call_mode: str
    speech_language: str
    amount_paid: float
    voice_change_enabled: bool
    scheduled_at: str | None = None
    refunded_to_balance: float | None = None
    payment: PaymentInfo | None = None


class VentorSessionsResponse(BaseModel):
    items: list[VentorBookedSession]
    total: int = 0
    page: int = 1
    page_size: int = 20


class CancelSessionRequest(BaseModel):
    reason: str | None = None


class CancelSessionResponse(BaseModel):
    session: VentorBookedSession
    refunded_to_balance: float


class ListenerSessionItem(BaseModel):
    id: str
    scheduled_at: str | None = None
    duration_minutes: int
    ventor_name: str
    ventor_avatar_url: str | None = None
    message: str | None = None
    chosen_reason: str | None = None
    tags: list[str] | None = None
    speech_language: str
    is_waiting: bool = False
    can_join_now: bool = False
    is_video_call: bool
    ventor_rating: float | None = None
    status_label: str | None = None
    session_cost: float | None = None
    is_missed: bool = False
    history_outcome: str | None = None


class ListenerSessionsResponse(BaseModel):
    items: list[ListenerSessionItem]
    total: int = 0
    page: int = 1
    page_size: int = 20


class SessionStatsResponse(BaseModel):
    accepted_count: int
    declined_count: int
    missed_count: int


class SessionRequestItem(BaseModel):
    id: str
    ventor_name: str
    ventor_avatar_url: str | None = None
    message: str | None = None
    chosen_reason: str | None = None
    scheduled_at: str | None = None
    duration_minutes: int
    tags: list[str] | None = None
    received_at: str
    speech_language: str
    is_video_call: bool
    ventor_rating: float | None = None


class SessionRequestsResponse(BaseModel):
    items: list[SessionRequestItem]


class AcceptRequestResponse(BaseModel):
    session_id: str | None = None
    status: str


class DeclineRequestBody(BaseModel):
    reason: str | None = None


class OkResponse(BaseModel):
    ok: bool = True


class JoinCallResponse(BaseModel):
    call_token: str
    channel_id: str
    expires_at: str
    ice_servers: list[dict[str, Any]] | None = None


class EndSessionRequest(BaseModel):
    ended_by: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class EndSessionResponse(BaseModel):
    session_id: str
    status: str = "completed"


class ReportPayload(BaseModel):
    reason: str
    details: str | None = None


class RatingRequest(BaseModel):
    stars: int = Field(ge=1, le=5)
    review: str | None = None
    tip_amount: Literal[2, 5, 10] | None = None
    report: ReportPayload | None = None


class RatingResponse(BaseModel):
    ok: bool = True
    tip_charged: float | None = None


class FeedbackRequest(BaseModel):
    stars: int = Field(ge=1, le=5)
    felt_heard: bool
    talk_again: bool


class ReportRequest(BaseModel):
    reason: str
    details: str | None = None
    reported_role: str


class ReportResponse(BaseModel):
    ok: bool = True
    report_id: str
