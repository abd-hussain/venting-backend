"""Listener request/response schemas (Pydantic)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProfileStatusOut(str, Enum):
    incomplete = "incomplete"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class IdentityStatusOut(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SetupStepStatusOut(str, Enum):
    done = "done"
    in_progress = "in_progress"
    locked = "locked"


class SetupStepId(str, Enum):
    identity_verified = "identity_verified"
    profile_info = "profile_info"
    availability = "availability"
    training = "training"
    first_session_tutorial = "first_session_tutorial"


class DayOfWeekOut(str, Enum):
    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


class TimeSlot(BaseModel):
    start: str
    end: str


class AvailabilityDay(BaseModel):
    day: DayOfWeekOut
    slots: list[TimeSlot] = Field(default_factory=list)


class AvailabilityPayload(BaseModel):
    accept_instant_calls: bool = True
    session_length_minutes: int = 30
    break_length_minutes: int = 15
    language_ids: list[str] = Field(default_factory=list)
    time_zone_id: str = "UTC"
    days: list[AvailabilityDay] = Field(default_factory=list)


class RegisterListenerResponse(BaseModel):
    listener_id: str
    profile_status: ProfileStatusOut


class IdentityVerificationResponse(BaseModel):
    status: IdentityStatusOut


class ListenerProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str | None = None
    phone_country: str | None = None
    avatar_url: str | None = None
    about_me: str | None = None
    country: str | None = None
    country_iso: str | None = None
    city: str | None = None
    language_ids: list[str] = Field(default_factory=list)
    life_experiences: list[str] = Field(default_factory=list)
    comfort_areas: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    voice_intro_url: str | None = None
    voice_intro_seconds: int | None = None
    rating: float
    review_count: int
    session_count: int
    is_online: bool
    profile_status: ProfileStatusOut
    rate_per_minute: float


class ListenerProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    phone: str | None = None
    phone_country: str | None = Field(default=None, max_length=2)
    about_me: str | None = None
    bio: str | None = None
    country: str | None = None
    country_iso: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=30)
    language_ids: list[str] | None = None
    life_experiences: list[str] | None = None
    comfort_areas: list[str] | None = None
    boundaries: list[str] | None = None


class VoiceIntroResponse(BaseModel):
    voice_intro_url: str
    voice_intro_seconds: int | None = None


class ReviewItem(BaseModel):
    id: str
    reviewer_name: str
    rating: int
    comment: str | None = None
    created_at: str


class ReviewsResponse(BaseModel):
    rating: float
    review_count: int
    items: list[ReviewItem]
    total: int = 0
    page: int = 1
    page_size: int = 20


class ListenerPublicResponse(BaseModel):
    id: str
    name: str
    avatar_url: str | None = None
    rating: float
    review_count: int
    session_count: int
    topics: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    gender: str | None = None
    rate_per_minute: float
    bio: str | None = None
    help_with: list[str] = Field(default_factory=list)
    voice_preview_seconds: int | None = None
    is_online: bool
    is_verified: bool
    rating_breakdown: dict[str, Any] | None = None
    country: str | None = None
    city: str | None = None
    country_iso: str | None = None
    life_experiences: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    availability: AvailabilityPayload | None = None
    is_favorite: bool = False


class SetupStepItem(BaseModel):
    id: SetupStepId
    status: SetupStepStatusOut


class SetupProgressResponse(BaseModel):
    profile_approved: bool
    progress_percent: int
    steps: list[SetupStepItem]


class TutorialAckRequest(BaseModel):
    acknowledged: bool = True


class OnlineStatusRequest(BaseModel):
    is_online: bool


class OnlineStatusResponse(BaseModel):
    is_online: bool


class ImpactChartPoint(BaseModel):
    label: str
    value: float


class DashboardImpact(BaseModel):
    sessions_today: int
    minutes_today: int
    chart: list[ImpactChartPoint]


class DashboardUpcomingSession(BaseModel):
    id: str
    ventor_name: str
    when_label: str
    duration_minutes: int


class DashboardResponse(BaseModel):
    display_name: str
    setup_progress: SetupProgressResponse
    impact: DashboardImpact
    next_upcoming_session: DashboardUpcomingSession | None = None
    is_online: bool
    reminder: str | None = None


class ListenerPrivacySettings(BaseModel):
    show_online_status: bool
    show_languages: bool
    show_comfort_areas: bool
    show_experience_and_ratings: bool
    show_boundaries: bool
    visible_in_all_countries: bool
    visible_countries: list[str] | None = None
    allow_search_indexing: bool


class ListenerNotificationPreferences(BaseModel):
    push_enabled: bool
    new_session_requests: bool
    session_reminder_15_min: bool
    session_reminder_10_min: bool
    session_reminder_5_min: bool
    reviews_feedback: bool
    tips_earnings: bool
    promotions_updates: bool
    email_enabled: bool


class DaySlotsUpdate(BaseModel):
    slots: list[TimeSlot] = Field(default_factory=list)


class DayAvailabilityResponse(BaseModel):
    day: DayOfWeekOut
    slots: list[TimeSlot] = Field(default_factory=list)


class ListenerListResponse(BaseModel):
    items: list[ListenerPublicResponse]
    total: int
    page: int = 1
    page_size: int = 20
