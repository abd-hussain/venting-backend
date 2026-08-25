"""Ventor request/response schemas (Pydantic)."""

from enum import Enum

from pydantic import BaseModel, Field


class Gender(str, Enum):
    male = "male"
    female = "female"
    prefer_not_to_say = "prefer_not_to_say"


class Mood(str, Enum):
    great = "great"
    okay = "okay"
    anxious = "anxious"
    sad = "sad"
    angry = "angry"


class VentorRegisterRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    gender: Gender
    language_ids: list[str] = Field(min_length=1)
    interest_ids: list[str] = Field(min_length=1)
    other_interest_text: str | None = None
    avatar_preset_index: int | None = None


class VentorStats(BaseModel):
    sessions_count: int
    points: int
    streak_days: int


class VentorProfileResponse(BaseModel):
    id: str
    nickname: str
    email: str
    avatar_url: str | None = None
    gender: Gender
    quote: str | None = None
    is_anonymous: bool
    stats: VentorStats
    language_ids: list[str]
    interest_ids: list[str]


class OkResponse(BaseModel):
    ok: bool = True


class MoodStreak(BaseModel):
    current_days: int
    reward_unlocked: bool | None = None


class MoodCheckinResponse(BaseModel):
    id: str
    mood: Mood
    note: str | None = None
    at: str
    streak: MoodStreak


class MoodJourneyPoint(BaseModel):
    day_index: int
    mood: float | None = None


class MoodJourneyResponse(BaseModel):
    points: list[MoodJourneyPoint]


class FavoriteListenerItem(BaseModel):
    id: str
    name: str
    rating: float
    avatar_url: str | None = None


class FavoritesResponse(BaseModel):
    items: list[FavoriteListenerItem]


class AchievementItem(BaseModel):
    id: str
    title_key: str
    subtitle_key: str
    description_key: str
    unlocked: bool
    unlocked_at: str | None = None


class AchievementsResponse(BaseModel):
    items: list[AchievementItem]


class PrivacySettings(BaseModel):
    show_mood_journey: bool
    show_achievements: bool
    show_stats: bool
    show_favorite_listeners: bool
    allow_listener_discovery: bool


class NotificationPreferences(BaseModel):
    push_enabled: bool
    session_reminder_30_min: bool
    session_reminder_15_min: bool
    session_reminder_10_min: bool
    session_reminder_5_min: bool
    rewards_updates: bool
    promotions_updates: bool
    email_enabled: bool


class HomeStreak(BaseModel):
    current_days: int
    target_days: int = 7
    reward_offer_id: str | None = None
    discount_percent: float | None = None


class HomeSessionItem(BaseModel):
    id: str
    listener_name: str
    listener_avatar_url: str | None = None
    when_label: str
    duration_minutes: int
    is_favorite: bool


class HomeResponse(BaseModel):
    display_name: str
    mood_checkin_today: Mood | None = None
    streak: HomeStreak
    upcoming_session: HomeSessionItem | None = None
    recent_sessions: list[HomeSessionItem] = Field(default_factory=list)


class MoodCheckinRequest(BaseModel):
    mood: Mood
    note: str | None = Field(default=None, max_length=1000)
