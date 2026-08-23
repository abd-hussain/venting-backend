"""Admin user directory schemas — A12–A21."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserSummary(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    registration_complete: bool
    suspended_until: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = None
    registration_complete: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "UserUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ModerationRequest(BaseModel):
    reason: str = Field(default="Administrative action", min_length=1, max_length=2000)


class SuspendRequest(ModerationRequest):
    suspended_until: datetime | None = None


class ActionResponse(BaseModel):
    ok: bool = True
    user: UserSummary


class UserDossier(UserSummary):
    profile: dict[str, Any] | None = None
    session_count: int = 0
    refresh_token_count: int = 0
    moderation_actions: list[dict[str, Any]] = Field(default_factory=list)


class VentorSummary(BaseModel):
    id: str
    email: str
    nickname: str
    avatar_url: str | None = None
    is_active: bool
    points_balance: int
    completed_sessions_count: int
    created_at: datetime


class VentorDetail(VentorSummary):
    gender: str
    quote: str | None = None
    is_anonymous: bool
    mood_streak_days: int
    last_mood_checkin_date: str | None = None


class ListenerSummary(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    is_active: bool
    is_online: bool
    is_verified: bool
    profile_status: str
    rating: float
    rating_count: int = 0
    rate_per_minute: float = 0
    session_count: int
    favorite_count: int = 0
    created_at: datetime
