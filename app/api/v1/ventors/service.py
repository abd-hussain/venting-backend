"""Ventor business logic."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.ventors.schemas import (
    AchievementItem,
    AchievementsResponse,
    FavoriteListenerItem,
    FavoritesResponse,
    Gender,
    HomeResponse,
    HomeSessionItem,
    HomeStreak,
    Mood,
    MoodCheckinRequest,
    MoodCheckinResponse,
    MoodJourneyPoint,
    MoodJourneyResponse,
    MoodStreak,
    NotificationPreferences,
    OkResponse,
    PrivacySettings,
    VentorProfileResponse,
    VentorStats,
)
from app.core.config import Settings
from app.core.errors import conflict, forbidden, not_found, validation_error
from app.models.auth import User
from app.models.enums import Gender as GenderEnum
from app.models.enums import MoodKind, SessionStatus, UserRole
from app.models.lookups import ComfortArea, VentorInterest, VentorLanguage
from app.api.v1.catalogs.service import assert_active_languages
from app.models.profiles import ListenerProfile, VentorProfile
from app.models.rewards import RewardOffer
from app.models.sessions import Session as VentingSession
from app.models.settings import VentorNotificationPreferences, VentorPrivacySettings
from app.services.reward_offers import is_offer_expired
from app.models.ventor_wellness import (
    Achievement,
    MoodCheckin,
    VentorAchievement,
    VentorFavorite,
)

MOOD_JOURNEY_SCORE: dict[MoodKind, float] = {
    MoodKind.sad: 0.0,
    MoodKind.angry: 0.25,
    MoodKind.anxious: 0.5,
    MoodKind.okay: 0.75,
    MoodKind.great: 1.0,
}

STREAK_TARGET_DAYS = 7
WELCOME_OFFER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AVATAR_PRESET_COUNT = 12


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Prefer portable hour formatting (%-I is POSIX-only).
def _fmt_clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    ampm = "AM" if moment.hour < 12 else "PM"
    return f"{hour}:{moment.minute:02d} {ampm}"


def _when_label(moment: datetime | None, *, upcoming: bool) -> str:
    if moment is None:
        return "Soon" if upcoming else "Recently"
    moment = _as_utc(moment)
    now = datetime.now(timezone.utc)
    local_date = moment.date()
    today = now.date()
    if upcoming:
        clock = _fmt_clock(moment)
        if local_date == today:
            return f"Today {clock}"
        if local_date == today + timedelta(days=1):
            return f"Tomorrow {clock}"
        return f"{moment.strftime('%b')} {moment.day} · {clock}"
    delta = today - local_date
    if delta.days <= 0:
        return "Today"
    if delta.days == 1:
        return "Yesterday"
    if delta.days < 7:
        return f"{delta.days} days ago"
    return f"{moment.strftime('%b')} {moment.day}"


def _interest_ids(db: Session, ventor_id: UUID) -> list[str]:
    rows = (
        db.query(VentorInterest.comfort_area_id)
        .filter(VentorInterest.ventor_id == ventor_id)
        .order_by(VentorInterest.comfort_area_id)
        .all()
    )
    return [row[0] for row in rows]


def _language_ids(db: Session, ventor_id: UUID) -> list[str]:
    rows = (
        db.query(VentorLanguage.language_id)
        .filter(VentorLanguage.ventor_id == ventor_id)
        .order_by(VentorLanguage.language_id)
        .all()
    )
    return [row[0] for row in rows]


def _profile_response(
    db: Session,
    user: User,
    profile: VentorProfile,
) -> VentorProfileResponse:
    return VentorProfileResponse(
        id=str(user.id),
        nickname=profile.nickname,
        email=user.email,
        avatar_url=profile.avatar_url,
        gender=Gender(profile.gender.value),
        quote=profile.quote,
        is_anonymous=profile.is_anonymous,
        stats=VentorStats(
            sessions_count=profile.completed_sessions_count,
            points=profile.points_balance,
            streak_days=profile.mood_streak_days,
        ),
        language_ids=_language_ids(db, profile.user_id),
        interest_ids=_interest_ids(db, profile.user_id),
    )


def _parse_id_list(raw: str | list[str] | None, *, field: str) -> list[str]:
    if isinstance(raw, list):
        parsed = raw
    else:
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raise validation_error(
                f"{field} is required",
                ar=f"يجب تحديد {field}",
            )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise validation_error(
                f"{field} must be a JSON array of strings",
                ar=f"يجب أن تكون {field} مصفوفة JSON",
            ) from exc
    if not isinstance(parsed, list) or not parsed or not all(isinstance(i, str) for i in parsed):
        raise validation_error(
            f"{field} must be a non-empty JSON array of strings",
            ar=f"يجب أن تكون {field} قائمة غير فارغة من النصوص",
        )
    seen: set[str] = set()
    result: list[str] = []
    for item in parsed:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _parse_interest_ids(raw: str | list[str] | None) -> list[str]:
    return _parse_id_list(raw, field="interest_ids")


def _parse_language_ids(raw: str | list[str] | None) -> list[str]:
    return _parse_id_list(raw, field="language_ids")


def _validate_interest_ids(
    db: Session,
    interest_ids: list[str],
    *,
    other_interest_text: str | None = None,
) -> dict[str, ComfortArea]:
    rows = (
        db.query(ComfortArea)
        .filter(
            ComfortArea.id.in_(interest_ids),
            ComfortArea.is_active.is_(True),
            or_(
                ComfortArea.audience == "ventor",
                ComfortArea.audience == "all",
            ),
        )
        .all()
    )
    found = {row.id: row for row in rows}
    missing = [i for i in interest_ids if i not in found]
    if missing:
        raise validation_error(
            f"Unknown interest_ids: {', '.join(missing)}",
            ar="مجالات اهتمام غير معروفة",
        )

    custom_required = [row for row in rows if row.allows_custom_text]
    if custom_required:
        text = (other_interest_text or "").strip()
        if len(text) < 2:
            raise validation_error(
                "other_interest_text is required (min 2 characters) when selecting Other",
                ar="يجب إدخال نص الاهتمام الآخر (حرفان على الأقل)",
            )
    return found


async def _save_avatar(
    *,
    upload: UploadFile | None,
    preset_index: int | None,
    user_id: UUID,
    settings: Settings,
) -> str | None:
    if upload is not None and upload.filename:
        suffix = Path(upload.filename).suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            raise validation_error(
                "Avatar must be jpg, png, webp, or gif",
                ar="يجب أن تكون صورة الملف الشخصي بصيغة jpg أو png أو webp أو gif",
            )
        dest_dir = Path(settings.upload_dir) / "avatars"
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{user_id}{suffix}"
        dest = dest_dir / filename
        content = await upload.read()
        if not content:
            raise validation_error("Avatar file is empty", ar="ملف الصورة فارغ")
        if len(content) > 5 * 1024 * 1024:
            raise validation_error(
                "Avatar must be 5MB or smaller",
                ar="يجب ألا يتجاوز حجم الصورة 5 ميجابايت",
            )
        dest.write_bytes(content)
        return f"/static/{settings.upload_subdir}/avatars/{filename}"

    if preset_index is not None:
        if preset_index < 0 or preset_index >= AVATAR_PRESET_COUNT:
            raise validation_error(
                f"avatar_preset_index must be between 0 and {AVATAR_PRESET_COUNT - 1}",
                ar="رقم الصورة الجاهزة غير صالح",
            )
        return f"/static/avatars/presets/{preset_index}.png"

    return None


async def register_ventor(
    db: Session,
    user: User,
    *,
    nickname: str,
    gender: Gender,
    language_ids_raw: str | list[str],
    interest_ids_raw: str | list[str],
    other_interest_text: str | None,
    avatar: UploadFile | None,
    avatar_preset_index: int | None,
    settings: Settings,
) -> VentorProfileResponse:
    if user.role != UserRole.ventor:
        raise forbidden()

    existing = (
        db.query(VentorProfile)
        .filter(VentorProfile.user_id == user.id)
        .one_or_none()
    )
    if existing is not None:
        raise conflict(
            "Ventor profile already exists",
            ar="ملف الـ ventor موجود بالفعل",
        )

    nickname = nickname.strip()
    if not nickname or len(nickname) > 20:
        raise validation_error(
            "nickname must be 1–20 characters",
            ar="يجب أن يكون اللقب بين 1 و 20 حرفًا",
        )

    language_ids = _parse_language_ids(language_ids_raw)
    assert_active_languages(db, language_ids)

    interest_ids = _parse_interest_ids(interest_ids_raw)
    interest_rows = _validate_interest_ids(
        db,
        interest_ids,
        other_interest_text=other_interest_text,
    )
    custom_text = (other_interest_text or "").strip() or None

    has_upload = avatar is not None and bool(avatar.filename)
    if has_upload and avatar_preset_index is not None:
        raise validation_error(
            "Provide either avatar file or avatar_preset_index, not both",
            ar="قدّم ملف صورة أو رقم صورة جاهزة فقط",
        )

    # Spec: either file, preset, or neither (default preset 0).
    preset = avatar_preset_index if has_upload else (
        avatar_preset_index if avatar_preset_index is not None else 0
    )
    avatar_url = await _save_avatar(
        upload=avatar if has_upload else None,
        preset_index=None if has_upload else preset,
        user_id=user.id,
        settings=settings,
    )
    if avatar_url is None:
        raise validation_error(
            "Could not resolve avatar",
            ar="تعذر تعيين صورة الملف الشخصي",
        )

    welcome = db.get(RewardOffer, WELCOME_OFFER_ID)
    profile = VentorProfile(
        user_id=user.id,
        nickname=nickname,
        gender=GenderEnum(gender.value),
        avatar_url=avatar_url,
        is_anonymous=True,
        active_reward_offer_id=welcome.id if welcome is not None else None,
    )
    db.add(profile)
    db.flush()
    for language_id in language_ids:
        db.add(VentorLanguage(ventor_id=user.id, language_id=language_id))
    for interest_id in interest_ids:
        row = interest_rows[interest_id]
        db.add(
            VentorInterest(
                ventor_id=user.id,
                comfort_area_id=interest_id,
                custom_text=custom_text if row.allows_custom_text else None,
            )
        )
    db.add(VentorPrivacySettings(ventor_id=user.id))
    db.add(VentorNotificationPreferences(ventor_id=user.id))
    user.registration_complete = True
    db.commit()
    db.refresh(profile)
    return _profile_response(db, user, profile)


def get_ventor_profile(db: Session, user: User, profile: VentorProfile) -> VentorProfileResponse:
    return _profile_response(db, user, profile)


async def update_ventor_profile(
    db: Session,
    user: User,
    profile: VentorProfile,
    *,
    nickname: str | None,
    quote: str | None,
    avatar: UploadFile | None,
    settings: Settings,
) -> VentorProfileResponse:
    if nickname is not None:
        nickname = nickname.strip()
        if not nickname or len(nickname) > 20:
            raise validation_error(
                "nickname must be 1–20 characters",
                ar="يجب أن يكون اللقب بين 1 و 20 حرفًا",
            )
        profile.nickname = nickname

    if quote is not None:
        quote = quote.strip()
        if len(quote) > 280:
            raise validation_error(
                "quote must be at most 280 characters",
                ar="يجب ألا يتجاوز الاقتباس 280 حرفًا",
            )
        profile.quote = quote or None

    if avatar is not None and avatar.filename:
        profile.avatar_url = await _save_avatar(
            upload=avatar,
            preset_index=None,
            user_id=user.id,
            settings=settings,
        )

    db.commit()
    db.refresh(profile)
    return _profile_response(db, user, profile)


def get_home(db: Session, user: User, profile: VentorProfile) -> HomeResponse:
    today = _utc_today()
    today_checkin = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.ventor_id == profile.user_id, MoodCheckin.checkin_date == today)
        .one_or_none()
    )

    reward_offer_id: str | None = None
    discount_percent: float | None = None
    if profile.active_reward_offer_id is not None:
        offer = db.get(RewardOffer, profile.active_reward_offer_id)
        if offer is not None and offer.is_active and not is_offer_expired(offer):
            reward_offer_id = str(offer.id)
            if offer.percent_off is not None:
                discount_percent = float(offer.percent_off)

    favorite_ids = {
        row.listener_id
        for row in db.query(VentorFavorite)
        .filter(VentorFavorite.ventor_id == profile.user_id)
        .all()
    }

    upcoming_row = (
        db.query(VentingSession, ListenerProfile)
        .join(ListenerProfile, ListenerProfile.user_id == VentingSession.listener_id)
        .filter(
            VentingSession.ventor_id == profile.user_id,
            VentingSession.status.in_([SessionStatus.upcoming, SessionStatus.live]),
        )
        .order_by(VentingSession.scheduled_at.asc().nullslast())
        .first()
    )
    upcoming_session = None
    if upcoming_row is not None:
        session, listener = upcoming_row
        when = session.scheduled_at or session.started_at
        upcoming_session = HomeSessionItem(
            id=str(session.id),
            listener_name=listener.full_name,
            listener_avatar_url=listener.avatar_url,
            when_label=_when_label(when, upcoming=True),
            duration_minutes=session.duration_minutes,
            is_favorite=session.listener_id in favorite_ids,
        )

    recent_rows = (
        db.query(VentingSession, ListenerProfile)
        .join(ListenerProfile, ListenerProfile.user_id == VentingSession.listener_id)
        .filter(
            VentingSession.ventor_id == profile.user_id,
            VentingSession.status == SessionStatus.completed,
        )
        .order_by(VentingSession.ended_at.desc().nullslast(), VentingSession.scheduled_at.desc().nullslast())
        .limit(5)
        .all()
    )
    recent_sessions = [
        HomeSessionItem(
            id=str(session.id),
            listener_name=listener.full_name,
            listener_avatar_url=listener.avatar_url,
            when_label=_when_label(session.ended_at or session.scheduled_at, upcoming=False),
            duration_minutes=session.duration_minutes,
            is_favorite=session.listener_id in favorite_ids,
        )
        for session, listener in recent_rows
    ]

    return HomeResponse(
        display_name=profile.nickname,
        mood_checkin_today=Mood(today_checkin.mood.value) if today_checkin else None,
        streak=HomeStreak(
            current_days=profile.mood_streak_days,
            target_days=STREAK_TARGET_DAYS,
            reward_offer_id=reward_offer_id,
            discount_percent=discount_percent,
        ),
        upcoming_session=upcoming_session,
        recent_sessions=recent_sessions,
    )


def create_mood_checkin(
    db: Session,
    profile: VentorProfile,
    payload: MoodCheckinRequest,
) -> MoodCheckinResponse:
    today = _utc_today()
    existing = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.ventor_id == profile.user_id, MoodCheckin.checkin_date == today)
        .one_or_none()
    )
    if existing is not None:
        raise conflict(
            "Mood already checked in today",
            ar="تم تسجيل الحالة المزاجية اليوم بالفعل",
        )

    yesterday = today - timedelta(days=1)
    if profile.last_mood_checkin_date == yesterday:
        profile.mood_streak_days += 1
    elif profile.last_mood_checkin_date == today:
        pass
    else:
        profile.mood_streak_days = 1

    profile.last_mood_checkin_date = today
    reward_unlocked = profile.mood_streak_days >= STREAK_TARGET_DAYS

    checkin = MoodCheckin(
        ventor_id=profile.user_id,
        mood=MoodKind(payload.mood.value),
        note=payload.note,
        checkin_date=today,
        checked_in_at=datetime.now(timezone.utc),
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return MoodCheckinResponse(
        id=str(checkin.id),
        mood=payload.mood,
        note=checkin.note,
        at=_as_utc(checkin.checked_in_at).isoformat().replace("+00:00", "Z"),
        streak=MoodStreak(
            current_days=profile.mood_streak_days,
            reward_unlocked=reward_unlocked if reward_unlocked else None,
        ),
    )


def get_mood_journey(
    db: Session,
    profile: VentorProfile,
    *,
    days: int = 7,
) -> MoodJourneyResponse:
    days = max(1, min(days, 90))
    today = _utc_today()
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(MoodCheckin)
        .filter(
            MoodCheckin.ventor_id == profile.user_id,
            MoodCheckin.checkin_date >= start,
            MoodCheckin.checkin_date <= today,
        )
        .all()
    )
    by_date = {row.checkin_date: row.mood for row in rows}
    points: list[MoodJourneyPoint] = []
    for index in range(days):
        day = start + timedelta(days=index)
        mood = by_date.get(day)
        points.append(
            MoodJourneyPoint(
                day_index=index,
                mood=MOOD_JOURNEY_SCORE[mood] if mood is not None else None,
            )
        )
    return MoodJourneyResponse(points=points)


def list_favorites(db: Session, profile: VentorProfile) -> FavoritesResponse:
    rows = (
        db.query(VentorFavorite, ListenerProfile)
        .join(ListenerProfile, ListenerProfile.user_id == VentorFavorite.listener_id)
        .filter(VentorFavorite.ventor_id == profile.user_id)
        .order_by(VentorFavorite.created_at.desc())
        .all()
    )
    items = [
        FavoriteListenerItem(
            id=str(listener.user_id),
            name=listener.full_name,
            rating=float(listener.rating_avg or 0),
            avatar_url=listener.avatar_url,
        )
        for _, listener in rows
    ]
    return FavoritesResponse(items=items)


def add_favorite(db: Session, profile: VentorProfile, listener_id: UUID) -> OkResponse:
    listener = db.get(ListenerProfile, listener_id)
    if listener is None:
        raise not_found("Listener")

    existing = (
        db.query(VentorFavorite)
        .filter(
            VentorFavorite.ventor_id == profile.user_id,
            VentorFavorite.listener_id == listener_id,
        )
        .one_or_none()
    )
    if existing is None:
        db.add(VentorFavorite(ventor_id=profile.user_id, listener_id=listener_id))
        db.commit()
    return OkResponse(ok=True)


def remove_favorite(db: Session, profile: VentorProfile, listener_id: UUID) -> OkResponse:
    existing = (
        db.query(VentorFavorite)
        .filter(
            VentorFavorite.ventor_id == profile.user_id,
            VentorFavorite.listener_id == listener_id,
        )
        .one_or_none()
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
    return OkResponse(ok=True)


def list_achievements(db: Session, profile: VentorProfile) -> AchievementsResponse:
    unlocked = {
        row.achievement_id: row.unlocked_at
        for row in db.query(VentorAchievement)
        .filter(VentorAchievement.ventor_id == profile.user_id)
        .all()
    }
    catalog = (
        db.query(Achievement)
        .filter(Achievement.is_active.is_(True))
        .order_by(Achievement.sort_order.asc(), Achievement.id.asc())
        .all()
    )
    items = [
        AchievementItem(
            id=item.id,
            title_key=item.title_key,
            subtitle_key=item.subtitle_key,
            description_key=item.description_key,
            unlocked=item.id in unlocked,
            unlocked_at=(
                _as_utc(unlocked[item.id]).isoformat().replace("+00:00", "Z")
                if item.id in unlocked
                else None
            ),
        )
        for item in catalog
    ]
    return AchievementsResponse(items=items)


def _privacy_response(row: VentorPrivacySettings) -> PrivacySettings:
    return PrivacySettings(
        show_mood_journey=row.show_mood_journey,
        show_achievements=row.show_achievements,
        show_stats=row.show_stats,
        show_favorite_listeners=row.show_favorite_listeners,
        allow_listener_discovery=row.allow_listener_discovery,
    )


def get_privacy(db: Session, profile: VentorProfile) -> PrivacySettings:
    row = db.get(VentorPrivacySettings, profile.user_id)
    if row is None:
        row = VentorPrivacySettings(ventor_id=profile.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _privacy_response(row)


def update_privacy(
    db: Session,
    profile: VentorProfile,
    payload: PrivacySettings,
) -> PrivacySettings:
    row = db.get(VentorPrivacySettings, profile.user_id)
    if row is None:
        row = VentorPrivacySettings(ventor_id=profile.user_id)
        db.add(row)
    row.show_mood_journey = payload.show_mood_journey
    row.show_achievements = payload.show_achievements
    row.show_stats = payload.show_stats
    row.show_favorite_listeners = payload.show_favorite_listeners
    row.allow_listener_discovery = payload.allow_listener_discovery
    db.commit()
    db.refresh(row)
    return _privacy_response(row)


def _notif_response(row: VentorNotificationPreferences) -> NotificationPreferences:
    return NotificationPreferences(
        push_enabled=row.push_enabled,
        session_reminder_30_min=row.session_reminder_30_min,
        session_reminder_15_min=row.session_reminder_15_min,
        session_reminder_10_min=row.session_reminder_10_min,
        session_reminder_5_min=row.session_reminder_5_min,
        rewards_updates=row.rewards_updates,
        promotions_updates=row.promotions_updates,
        email_enabled=row.email_enabled,
    )


def get_notification_preferences(
    db: Session,
    profile: VentorProfile,
) -> NotificationPreferences:
    row = db.get(VentorNotificationPreferences, profile.user_id)
    if row is None:
        row = VentorNotificationPreferences(ventor_id=profile.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _notif_response(row)


def update_notification_preferences(
    db: Session,
    profile: VentorProfile,
    payload: NotificationPreferences,
) -> NotificationPreferences:
    row = db.get(VentorNotificationPreferences, profile.user_id)
    if row is None:
        row = VentorNotificationPreferences(ventor_id=profile.user_id)
        db.add(row)
    row.push_enabled = payload.push_enabled
    row.session_reminder_30_min = payload.session_reminder_30_min
    row.session_reminder_15_min = payload.session_reminder_15_min
    row.session_reminder_10_min = payload.session_reminder_10_min
    row.session_reminder_5_min = payload.session_reminder_5_min
    row.rewards_updates = payload.rewards_updates
    row.promotions_updates = payload.promotions_updates
    row.email_enabled = payload.email_enabled
    db.commit()
    db.refresh(row)
    return _notif_response(row)
