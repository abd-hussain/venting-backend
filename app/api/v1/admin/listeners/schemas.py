"""Admin listener review schemas — A22–A27."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ListenerQueueItem(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    country: str | None = None
    profile_status: str
    submitted_at: datetime


class ListenerReviewDetail(ListenerQueueItem):
    phone_e164: str | None = None
    date_of_birth: date | None = None
    city: str | None = None
    gender: str | None = None
    about_me: str | None = None
    bio: str | None = None
    voice_intro_url: str | None = None
    voice_intro_seconds: int | None = None
    is_verified: bool
    rate_per_minute: float
    rating: float
    rating_count: int
    session_count: int
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None
    languages: list[str] = Field(default_factory=list)
    comfort_areas: list[str] = Field(default_factory=list)
    life_experiences: list[dict[str, Any]] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class IdentityVerificationDetail(BaseModel):
    id: str
    listener_id: str
    document_front_url: str
    document_back_url: str | None = None
    selfie_url: str
    status: str
    reviewer_note: str | None = None
    reviewed_by_admin_id: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class RejectListenerRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    needs_more_info: bool = False


class IdentityDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"
    needs_more_info = "needs_more_info"


class IdentityDecisionRequest(BaseModel):
    decision: IdentityDecision
    note: str | None = Field(default=None, max_length=2000)


class ListenerReviewResponse(BaseModel):
    id: str
    profile_status: str
    is_verified: bool
    reviewed_at: datetime | None = None

