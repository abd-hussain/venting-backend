"""Ventor step-based registration (#8a–#8e)."""

from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.v1.ventors.schemas import (
    Gender,
    VentorRegisterCompleteRequest,
    VentorRegisterInterestsRequest,
    VentorRegisterLanguagesRequest,
    VentorRegisterProfileRequest,
    VentorRegisterProgressResponse,
    VentorRegisterSaved,
    VentorSavedInterests,
    VentorSavedLanguages,
    VentorSavedProfile,
    VentorProfileResponse,
)
from app.api.v1.ventors.service import (
    AVATAR_PRESET_COUNT,
    WELCOME_OFFER_ID,
    _interest_ids,
    _language_ids,
    _parse_interest_ids,
    _parse_language_ids,
    _profile_response,
    _save_avatar,
    _validate_interest_ids,
)
from app.core.config import Settings
from app.core.errors import conflict, forbidden, validation_error
from app.models.auth import User
from app.models.enums import Gender as GenderEnum
from app.models.enums import UserRole
from app.models.lookups import VentorInterest, VentorLanguage
from app.models.profiles import VentorProfile
from app.models.rewards import RewardOffer
from app.models.settings import VentorNotificationPreferences, VentorPrivacySettings
from app.services.push_tokens import upsert_push_token
from app.services.registration_progress import (
    VENTOR_REGISTER_STEPS,
    avatar_preset_from_url,
    completed_steps,
    ensure_registration_open,
    mark_step_done,
    next_step_for,
    require_steps_done,
)


def _get_profile(db: Session, user_id: uuid.UUID) -> VentorProfile | None:
    return db.query(VentorProfile).filter(VentorProfile.user_id == user_id).one_or_none()


def _other_interest_text(db: Session, ventor_id: uuid.UUID) -> str | None:
    row = (
        db.query(VentorInterest.custom_text)
        .filter(
            VentorInterest.ventor_id == ventor_id,
            VentorInterest.custom_text.isnot(None),
        )
        .first()
    )
    return row[0] if row else None


def _replace_languages(db: Session, ventor_id: uuid.UUID, language_ids: list[str]) -> None:
    db.query(VentorLanguage).filter(VentorLanguage.ventor_id == ventor_id).delete()
    for language_id in language_ids:
        db.add(VentorLanguage(ventor_id=ventor_id, language_id=language_id))


def _replace_interests(
    db: Session,
    ventor_id: uuid.UUID,
    interest_ids: list[str],
    interest_rows: dict,
    custom_text: str | None,
) -> None:
    db.query(VentorInterest).filter(VentorInterest.ventor_id == ventor_id).delete()
    for interest_id in interest_ids:
        row = interest_rows[interest_id]
        db.add(
            VentorInterest(
                ventor_id=ventor_id,
                comfort_area_id=interest_id,
                custom_text=custom_text if row.allows_custom_text else None,
            )
        )


def get_register_progress(db: Session, user: User) -> VentorRegisterProgressResponse:
    if user.role != UserRole.ventor:
        raise forbidden()

    profile = _get_profile(db, user.id)
    done = completed_steps(user)
    if user.registration_complete:
        next_step = None
    else:
        next_step = user.registration_next_step or next_step_for(user, VENTOR_REGISTER_STEPS)

    saved = VentorRegisterSaved()
    if profile is not None and "profile" in done:
        saved.profile = VentorSavedProfile(
            nickname=profile.nickname,
            gender=Gender(profile.gender.value),
            avatar_url=profile.avatar_url,
            avatar_preset_index=avatar_preset_from_url(profile.avatar_url),
        )
    if profile is not None and "languages" in done:
        saved.languages = VentorSavedLanguages(language_ids=_language_ids(db, profile.user_id))
    if profile is not None and "interests" in done:
        saved.interests = VentorSavedInterests(
            interest_ids=_interest_ids(db, profile.user_id),
            other_interest_text=_other_interest_text(db, profile.user_id),
        )

    return VentorRegisterProgressResponse(
        registration_complete=user.registration_complete,
        next_step=next_step,
        completed_steps=done,
        saved=saved,
    )


async def save_register_profile_step(
    db: Session,
    user: User,
    *,
    payload: VentorRegisterProfileRequest,
    avatar: UploadFile | None,
    settings: Settings,
) -> VentorRegisterProgressResponse:
    if user.role != UserRole.ventor:
        raise forbidden()
    ensure_registration_open(user)

    nickname = payload.nickname.strip()
    if not nickname or len(nickname) > 20:
        raise validation_error(
            "nickname must be 1–20 characters",
            ar="يجب أن يكون اللقب بين 1 و 20 حرفًا",
        )

    has_upload = avatar is not None and bool(avatar.filename)
    if has_upload and payload.avatar_preset_index is not None:
        raise validation_error(
            "Provide either avatar file or avatar_preset_index, not both",
            ar="قدّم ملف صورة أو رقم صورة جاهزة فقط",
        )

    preset = payload.avatar_preset_index
    if preset is not None and (preset < 0 or preset >= AVATAR_PRESET_COUNT):
        raise validation_error(
            f"avatar_preset_index must be between 0 and {AVATAR_PRESET_COUNT - 1}",
            ar="رقم الصورة الجاهزة غير صالح",
        )

    profile = _get_profile(db, user.id)
    avatar_url = profile.avatar_url if profile else None
    if has_upload or preset is not None:
        avatar_url = await _save_avatar(
            upload=avatar if has_upload else None,
            preset_index=preset if not has_upload else None,
            user_id=user.id,
            settings=settings,
        )
    elif avatar_url is None:
        avatar_url = await _save_avatar(
            upload=None,
            preset_index=0,
            user_id=user.id,
            settings=settings,
        )
    if profile is None:
        welcome = db.get(RewardOffer, WELCOME_OFFER_ID)
        profile = VentorProfile(
            user_id=user.id,
            nickname=nickname,
            gender=GenderEnum(payload.gender.value),
            avatar_url=avatar_url,
            is_anonymous=True,
            active_reward_offer_id=welcome.id if welcome is not None else None,
        )
        db.add(profile)
    else:
        profile.nickname = nickname
        profile.gender = GenderEnum(payload.gender.value)
        if avatar_url is not None:
            profile.avatar_url = avatar_url

    mark_step_done(user, "profile", VENTOR_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_languages_step(
    db: Session,
    user: User,
    payload: VentorRegisterLanguagesRequest,
) -> VentorRegisterProgressResponse:
    if user.role != UserRole.ventor:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    language_ids = _parse_language_ids(payload.language_ids)
    from app.api.v1.catalogs.service import assert_active_languages

    assert_active_languages(db, language_ids)
    _replace_languages(db, user.id, language_ids)
    mark_step_done(user, "languages", VENTOR_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_interests_step(
    db: Session,
    user: User,
    payload: VentorRegisterInterestsRequest,
) -> VentorRegisterProgressResponse:
    if user.role != UserRole.ventor:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    interest_ids = _parse_interest_ids(payload.interest_ids)
    interest_rows = _validate_interest_ids(
        db,
        interest_ids,
        other_interest_text=payload.other_interest_text,
    )
    custom_text = (payload.other_interest_text or "").strip() or None
    _replace_interests(db, user.id, interest_ids, interest_rows, custom_text)
    mark_step_done(user, "interests", VENTOR_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def complete_register(
    db: Session,
    user: User,
    payload: VentorRegisterCompleteRequest,
) -> VentorProfileResponse:
    if user.role != UserRole.ventor:
        raise forbidden()

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete registration steps before finishing",
            ar="أكمل خطوات التسجيل قبل الإنهاء",
        )

    if user.registration_complete:
        raise conflict(
            "Ventor profile already registered",
            ar="ملف الـ ventor موجود بالفعل",
        )

    require_steps_done(
        user,
        ("profile", "languages", "interests"),
        steps=VENTOR_REGISTER_STEPS,
    )

    if db.get(VentorPrivacySettings, user.id) is None:
        db.add(VentorPrivacySettings(ventor_id=user.id))
    notif = db.get(VentorNotificationPreferences, user.id)
    if notif is None:
        db.add(
            VentorNotificationPreferences(
                ventor_id=user.id,
                push_enabled=payload.notifications_enabled,
            )
        )
    else:
        notif.push_enabled = payload.notifications_enabled

    upsert_push_token(db, user.id, payload.fcm_token)
    mark_step_done(user, "notifications", VENTOR_REGISTER_STEPS)
    user.registration_complete = True
    from app.services.inbox_notifications import send_book_first_session_ventor

    send_book_first_session_ventor(db, user)
    db.commit()
    db.refresh(profile)
    return _profile_response(db, user, profile)
