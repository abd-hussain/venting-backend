"""Listener request/response schemas (Pydantic)."""

from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator


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
    pending = "pending"
    locked = "locked"


class SetupStepId(str, Enum):
    create_account = "create_account"
    identity_verification = "identity_verification"
    about_you = "about_you"
    experience = "experience"
    comfort_areas = "comfort_areas"
    boundaries = "boundaries"
    voice_intro = "voice_intro"
    availability = "availability"
    notifications = "notifications"
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


ALLOWED_SESSION_MINUTES = frozenset({30, 45, 60})
ALLOWED_BREAK_MINUTES = frozenset({0, 5, 10, 15, 30, 60})


class AvailabilityPayload(BaseModel):
    accept_instant_calls: bool = True
    session_minutes: list[int] = Field(default_factory=list)
    session_length_minutes: int | None = None
    break_length_minutes: int = 15
    language_ids: list[str] | None = None
    time_zone_id: str = "UTC"
    days: list[AvailabilityDay] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def legacy_session_length_minutes(cls, data: Any) -> Any:
        if isinstance(data, dict) and "session_minutes" not in data:
            legacy = data.get("session_length_minutes")
            if legacy is not None:
                data = {**data, "session_minutes": [legacy]}
        return data

    @field_validator("session_minutes")
    @classmethod
    def normalize_session_minutes(cls, values: list[int]) -> list[int]:
        seen: list[int] = []
        for value in values:
            if value not in seen:
                seen.append(value)
        return seen

    @model_validator(mode="after")
    def validate_availability(self) -> Self:
        if len(self.session_minutes) > 2:
            raise ValueError("session_minutes allows at most 2 values")
        invalid = [value for value in self.session_minutes if value not in ALLOWED_SESSION_MINUTES]
        if invalid:
            raise ValueError(
                "session_minutes must be empty or contain only 30, 45, or 60"
            )
        if self.break_length_minutes not in ALLOWED_BREAK_MINUTES:
            raise ValueError(
                "break_length_minutes must be one of 0, 5, 10, 15, 30, or 60"
            )
        return self


class RegisterListenerResponse(BaseModel):
    listener_id: str
    profile_status: ProfileStatusOut


class ListenerSavedProfile(BaseModel):
    full_name: str
    phone: str
    phone_country: str
    avatar_url: str | None = None


class ListenerSavedIdentity(BaseModel):
    identity_document_url: str | None = None
    selfie_url: str | None = None


class ListenerSavedAbout(BaseModel):
    date_of_birth: str
    country_iso: str
    city: str
    language_ids: list[str]


class ListenerSavedExperiences(BaseModel):
    life_experience_ids: list[str]
    relationship_status: str | None = None
    family_role_ids: list[str] = Field(default_factory=list)
    custom_experiences: list[str] = Field(default_factory=list)


class ListenerSavedComfortAreas(BaseModel):
    comfort_area_ids: list[str]
    custom_comfort_area_text: str | None = None


class ListenerSavedBoundaries(BaseModel):
    boundary_ids: list[str]
    custom_boundary_text: str | None = None


class ListenerSavedVoiceIntro(BaseModel):
    voice_intro_url: str | None = None
    voice_intro_seconds: int | None = None


class ListenerSavedAvailability(BaseModel):
    accept_instant_calls: bool
    session_minutes: list[int] = Field(default_factory=list)
    availability: AvailabilityPayload


class ListenerRegisterSaved(BaseModel):
    profile: ListenerSavedProfile | None = None
    identity: ListenerSavedIdentity | None = None
    about: ListenerSavedAbout | None = None
    experiences: ListenerSavedExperiences | None = None
    comfort_areas: ListenerSavedComfortAreas | None = None
    boundaries: ListenerSavedBoundaries | None = None
    voice_intro: ListenerSavedVoiceIntro | None = None
    availability: ListenerSavedAvailability | None = None


class ListenerRegisterProgressResponse(BaseModel):
    registration_complete: bool
    profile_status: ProfileStatusOut | None = None
    next_step: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    saved: ListenerRegisterSaved = Field(default_factory=ListenerRegisterSaved)


class ListenerRegisterProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str
    phone_country: str


class ListenerRegisterAboutRequest(BaseModel):
    date_of_birth: str
    country_iso: str
    city: str
    language_ids: list[str] = Field(min_length=1)


class ListenerRegisterExperiencesRequest(BaseModel):
    life_experience_ids: list[str] = Field(default_factory=list)
    relationship_status: str | None = None
    family_role_ids: list[str] = Field(default_factory=list)
    custom_experiences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_some_experience(self) -> Self:
        has_catalog = bool(self.life_experience_ids)
        has_relationship = bool((self.relationship_status or "").strip())
        has_family = bool(self.family_role_ids)
        has_custom = any(label.strip() for label in self.custom_experiences)
        if not (has_catalog or has_relationship or has_family or has_custom):
            raise ValueError(
                "At least one of life_experience_ids, relationship_status, "
                "family_role_ids, or custom_experiences is required"
            )
        return self


class ListenerRegisterComfortAreasRequest(BaseModel):
    comfort_area_ids: list[str] = Field(min_length=1)
    custom_comfort_area_text: str | None = None


class ListenerRegisterBoundariesRequest(BaseModel):
    boundary_ids: list[str] = Field(min_length=1)
    custom_boundary_text: str | None = None


class ListenerRegisterVoiceIntroRequest(BaseModel):
    voice_intro_seconds: int


class ListenerRegisterAvailabilityRequest(BaseModel):
    accept_instant_calls: bool
    session_minutes: list[int] = Field(default_factory=list)
    availability: AvailabilityPayload


class ListenerRegisterCompleteRequest(BaseModel):
    fcm_token: str | None = None


class IdentityVerificationResponse(BaseModel):
    status: IdentityStatusOut


class ListenerLifeExperiencesOut(BaseModel):
    life_experience_ids: list[str] = Field(default_factory=list)
    relationship_status: str | None = None
    family_role_ids: list[str] = Field(default_factory=list)
    custom_experiences: list[str] = Field(default_factory=list)


class ListenerComfortAreasOut(BaseModel):
    comfort_area_ids: list[str] = Field(default_factory=list)
    custom_comfort_area_text: str | None = None


class ListenerBoundariesOut(BaseModel):
    boundary_ids: list[str] = Field(default_factory=list)
    custom_boundary_text: str | None = None


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
    life_experiences: ListenerLifeExperiencesOut = Field(
        default_factory=ListenerLifeExperiencesOut
    )
    comfort_areas: ListenerComfortAreasOut = Field(default_factory=ListenerComfortAreasOut)
    boundaries: ListenerBoundariesOut = Field(default_factory=ListenerBoundariesOut)
    voice_intro_url: str | None = None
    voice_intro_seconds: int | None = None
    rating: float
    review_count: int
    session_count: int
    is_online: bool
    profile_status: ProfileStatusOut
    rate_per_minute: float
    rating_breakdown: dict[str, Any] | None = None


class ListenerProfileUpdate(BaseModel):
    phone: str | None = None
    phone_country: str | None = Field(default=None, max_length=2)
    about_me: str | None = None
    country: str | None = None
    country_iso: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=30)
    language_ids: list[str] | None = None
    life_experience_ids: list[str] | None = None
    relationship_status: str | None = None
    family_role_ids: list[str] | None = None
    custom_experiences: list[str] | None = None
    comfort_area_ids: list[str] | None = None
    custom_comfort_area_text: str | None = None
    boundary_ids: list[str] | None = None
    custom_boundary_text: str | None = None


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
    profile_visible: bool = True
    show_online_status: bool = True
    visible_in_all_countries: bool = True
    visible_countries: list[str] = Field(default_factory=list)
    allow_search_indexing: bool = True


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
