"""Listener step-based registration (#22a–#22j)."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.v1.listeners.schemas import (
    AvailabilityPayload,
    ListenerRegisterAboutRequest,
    ListenerRegisterAvailabilityRequest,
    ListenerRegisterBoundariesRequest,
    ListenerRegisterComfortAreasRequest,
    ListenerRegisterCompleteRequest,
    ListenerRegisterExperiencesRequest,
    ListenerRegisterProgressResponse,
    ListenerRegisterSaved,
    ListenerRegisterVoiceIntroRequest,
    ListenerSavedAbout,
    ListenerSavedAvailability,
    ListenerSavedBoundaries,
    ListenerSavedComfortAreas,
    ListenerSavedExperiences,
    ListenerSavedIdentity,
    ListenerSavedProfile,
    ListenerSavedVoiceIntro,
    ProfileStatusOut,
    RegisterListenerResponse,
)
from app.api.v1.listeners.service import (
    AUDIO_SUFFIXES,
    IMAGE_SUFFIXES,
    _apply_availability,
    _boundary_custom_text,
    _catalog_experience_ids,
    _comfort_custom_text,
    _custom_experience_labels,
    _load_tag_ids,
    _parse_date,
    _replace_listener_experiences,
    _replace_tags,
    _require_text,
    _save_upload,
    _static_url,
    _utc_now,
    _validate_family_role_ids,
    _validate_relationship_status,
    get_availability_payload,
)
from app.core.config import Settings
from app.core.errors import conflict, forbidden, validation_error
from app.models.auth import User
from app.models.earnings import ListenerWallet
from app.models.enums import ProfileStatus, SetupStepStatus, UserRole
from app.models.profiles import ListenerIdentityVerification, ListenerProfile
from app.models.settings import (
    ListenerNotificationPreferences as ListenerNotificationPreferencesRow,
)
from app.models.settings import ListenerPrivacySettings as ListenerPrivacySettingsRow
from app.services.push_tokens import upsert_push_token
from app.services.registration_progress import (
    LISTENER_REGISTER_STEPS,
    completed_steps,
    ensure_registration_open,
    mark_step_done,
    next_step_for,
    require_steps_done,
)


def _get_profile(db: Session, user_id) -> ListenerProfile | None:
    return db.get(ListenerProfile, user_id)


def _latest_identity(db: Session, listener_id) -> ListenerIdentityVerification | None:
    return (
        db.query(ListenerIdentityVerification)
        .filter(ListenerIdentityVerification.listener_id == listener_id)
        .order_by(ListenerIdentityVerification.created_at.desc())
        .first()
    )


def get_register_progress(db: Session, user: User) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()

    profile = _get_profile(db, user.id)
    done = completed_steps(user)
    if user.registration_complete:
        next_step = None
    else:
        next_step = user.registration_next_step or next_step_for(user, LISTENER_REGISTER_STEPS)

    saved = ListenerRegisterSaved()
    if profile is not None:
        if "profile" in done:
            saved.profile = ListenerSavedProfile(
                full_name=profile.full_name,
                phone=profile.phone_e164 or "",
                phone_country=profile.phone_country_iso or "",
                avatar_url=profile.avatar_url,
            )
        if "identity" in done:
            identity = _latest_identity(db, user.id)
            saved.identity = ListenerSavedIdentity(
                identity_document_url=identity.identity_document_url if identity else None,
                selfie_url=identity.selfie_url if identity else None,
            )
        if "about" in done and profile.date_of_birth is not None:
            tags = _load_tag_ids(db, user.id)
            saved.about = ListenerSavedAbout(
                date_of_birth=profile.date_of_birth.isoformat(),
                country_iso=profile.country_iso or "",
                city=profile.city or "",
                language_ids=tags["languages"],
            )
        if "experiences" in done:
            saved.experiences = ListenerSavedExperiences(
                life_experience_ids=_catalog_experience_ids(db, user.id),
                relationship_status=profile.relationship_status,
                family_role_ids=list(profile.family_role_ids or []),
                custom_experiences=_custom_experience_labels(db, user.id),
            )
        if "comfort-areas" in done:
            tags = _load_tag_ids(db, user.id)
            saved.comfort_areas = ListenerSavedComfortAreas(
                comfort_area_ids=tags["comfort"],
                custom_comfort_area_text=_comfort_custom_text(db, user.id),
            )
        if "boundaries" in done:
            tags = _load_tag_ids(db, user.id)
            saved.boundaries = ListenerSavedBoundaries(
                boundary_ids=tags["boundaries"],
                custom_boundary_text=_boundary_custom_text(db, user.id),
            )
        if "voice-intro" in done:
            saved.voice_intro = ListenerSavedVoiceIntro(
                voice_intro_url=profile.voice_intro_url,
                voice_intro_seconds=profile.voice_intro_seconds,
            )
        if "availability" in done:
            availability = get_availability_payload(db, user.id)
            saved.availability = ListenerSavedAvailability(
                accept_instant_calls=availability.accept_instant_calls,
                session_minutes=availability.session_length_minutes,
                availability=availability,
            )

    return ListenerRegisterProgressResponse(
        registration_complete=user.registration_complete,
        profile_status=(
            ProfileStatusOut(profile.profile_status.value) if profile is not None else None
        ),
        next_step=next_step,
        completed_steps=done,
        saved=saved,
    )


async def save_register_profile_step(
    db: Session,
    user: User,
    *,
    full_name: str,
    phone: str | None,
    phone_country: str | None,
    avatar: UploadFile | None,
    settings: Settings,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    name = full_name.strip()
    if not name or len(name) > 120:
        raise validation_error(
            "full_name must be 1–120 characters",
            ar="الاسم يجب أن يكون بين 1 و 120 حرفًا",
        )
    phone_value = _require_text(phone, field="phone")
    phone_country_value = _require_text(phone_country, field="phone_country")

    profile = _get_profile(db, user.id)
    avatar_url = profile.avatar_url if profile else None
    if avatar is not None and avatar.filename:
        avatar_url = await _save_upload(
            avatar,
            dest_dir=_static_url(settings, "uploads", "avatars"),
            filename=str(user.id),
            allowed=IMAGE_SUFFIXES,
            max_bytes=5 * 1024 * 1024,
        )
    elif avatar_url is None:
        raise validation_error("avatar is required", ar="صورة الملف الشخصي مطلوبة")

    if profile is None:
        profile = ListenerProfile(
            user_id=user.id,
            full_name=name,
            phone_e164=phone_value,
            phone_country_iso=phone_country_value,
            avatar_url=avatar_url,
            time_zone_id="UTC",
            profile_status=ProfileStatus.incomplete,
            setup_identity_status=SetupStepStatus.locked,
            setup_profile_status=SetupStepStatus.in_progress,
            setup_availability_status=SetupStepStatus.locked,
            setup_training_status=SetupStepStatus.locked,
            setup_tutorial_status=SetupStepStatus.locked,
        )
        db.add(profile)
    else:
        profile.full_name = name
        profile.phone_e164 = phone_value
        profile.phone_country_iso = phone_country_value
        profile.avatar_url = avatar_url

    mark_step_done(user, "profile", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


async def save_register_identity_step(
    db: Session,
    user: User,
    *,
    identity_document: UploadFile | None,
    selfie: UploadFile | None,
    settings: Settings,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    existing = _latest_identity(db, user.id)
    identity_url = existing.identity_document_url if existing else None
    selfie_url = existing.selfie_url if existing else None

    if identity_document is not None and identity_document.filename:
        identity_url = await _save_upload(
            identity_document,
            dest_dir=_static_url(settings, "uploads", "identity", str(user.id)),
            filename="identity_document",
            allowed=IMAGE_SUFFIXES,
            max_bytes=10 * 1024 * 1024,
        )
    if selfie is not None and selfie.filename:
        selfie_url = await _save_upload(
            selfie,
            dest_dir=_static_url(settings, "uploads", "identity", str(user.id)),
            filename="selfie",
            allowed=IMAGE_SUFFIXES,
            max_bytes=10 * 1024 * 1024,
        )

    if not identity_url:
        raise validation_error(
            "identity_document is required",
            ar="صورة وثيقة الهوية مطلوبة",
        )
    if not selfie_url:
        raise validation_error("selfie is required", ar="صورة السيلفي مطلوبة")

    row = ListenerIdentityVerification(
        listener_id=user.id,
        identity_document_url=identity_url,
        selfie_url=selfie_url,
        status=ProfileStatus.incomplete,
    )
    db.add(row)
    profile.setup_identity_status = SetupStepStatus.in_progress
    mark_step_done(user, "identity", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_about_step(
    db: Session,
    user: User,
    payload: ListenerRegisterAboutRequest,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    dob = _parse_date(payload.date_of_birth)
    if dob is None:
        raise validation_error(
            "date_of_birth is required (YYYY-MM-DD)",
            ar="تاريخ الميلاد مطلوب",
        )
    city_value = _require_text(payload.city, field="city")
    country_iso_value = _require_text(payload.country_iso, field="country_iso").upper()
    language_ids = payload.language_ids
    if not language_ids:
        raise validation_error("language_ids is required", ar="language_ids مطلوب")

    profile.date_of_birth = dob
    profile.country_iso = country_iso_value
    profile.city = city_value
    _replace_tags(db, listener_id=user.id, language_ids=language_ids)
    profile.setup_profile_status = SetupStepStatus.done
    mark_step_done(user, "about", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_experiences_step(
    db: Session,
    user: User,
    payload: ListenerRegisterExperiencesRequest,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    life_experience_ids = payload.life_experience_ids
    custom_experiences = [label.strip() for label in payload.custom_experiences if label.strip()]
    profile.relationship_status = _validate_relationship_status(payload.relationship_status)
    profile.family_role_ids = _validate_family_role_ids(payload.family_role_ids)
    _replace_listener_experiences(
        db,
        user.id,
        life_experience_ids=life_experience_ids,
        custom_experiences=custom_experiences,
    )

    mark_step_done(user, "experiences", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_comfort_areas_step(
    db: Session,
    user: User,
    payload: ListenerRegisterComfortAreasRequest,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    _replace_tags(
        db,
        listener_id=user.id,
        comfort_area_ids=payload.comfort_area_ids,
        custom_comfort_area_text=payload.custom_comfort_area_text,
    )
    mark_step_done(user, "comfort-areas", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_boundaries_step(
    db: Session,
    user: User,
    payload: ListenerRegisterBoundariesRequest,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    _replace_tags(
        db,
        listener_id=user.id,
        boundary_ids=payload.boundary_ids,
        custom_boundary_text=payload.custom_boundary_text,
    )
    mark_step_done(user, "boundaries", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


async def save_register_voice_intro_step(
    db: Session,
    user: User,
    *,
    payload: ListenerRegisterVoiceIntroRequest,
    voice_intro: UploadFile | None,
    settings: Settings,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    voice_url = profile.voice_intro_url
    if voice_intro is not None and voice_intro.filename:
        voice_url = await _save_upload(
            voice_intro,
            dest_dir=_static_url(settings, "uploads", "voice"),
            filename=str(user.id),
            allowed=AUDIO_SUFFIXES,
            max_bytes=20 * 1024 * 1024,
        )
    if not voice_url:
        raise validation_error("voice_intro is required", ar="التسجيل الصوتي مطلوب")

    profile.voice_intro_url = voice_url
    profile.voice_intro_seconds = payload.voice_intro_seconds
    mark_step_done(user, "voice-intro", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def save_register_availability_step(
    db: Session,
    user: User,
    payload: ListenerRegisterAvailabilityRequest,
) -> ListenerRegisterProgressResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    ensure_registration_open(user)

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete the profile step first",
            ar="أكمل خطوة الملف الشخصي أولًا",
        )

    availability = payload.availability
    if not availability.days:
        raise validation_error(
            "availability.days must include at least one day",
            ar="يجب تضمين يوم واحد على الأقل في التوفر",
        )

    _apply_availability(
        db,
        user.id,
        availability,
        accept_instant_calls=payload.accept_instant_calls,
        session_minutes=payload.session_minutes,
    )
    profile.setup_availability_status = SetupStepStatus.done
    mark_step_done(user, "availability", LISTENER_REGISTER_STEPS)
    db.commit()
    return get_register_progress(db, user)


def complete_register(
    db: Session,
    user: User,
    payload: ListenerRegisterCompleteRequest,
) -> RegisterListenerResponse:
    if user.role != UserRole.listener:
        raise forbidden()

    profile = _get_profile(db, user.id)
    if profile is None:
        raise validation_error(
            "Complete registration steps before finishing",
            ar="أكمل خطوات التسجيل قبل الإنهاء",
        )

    if user.registration_complete:
        raise conflict(
            "Listener profile already registered",
            ar="ملف المستمع موجود بالفعل",
        )

    require_steps_done(
        user,
        (
            "profile",
            "identity",
            "about",
            "experiences",
            "comfort-areas",
            "boundaries",
            "voice-intro",
            "availability",
        ),
        steps=LISTENER_REGISTER_STEPS,
    )

    identity = _latest_identity(db, user.id)
    if identity is None:
        raise validation_error(
            "Identity documents are required",
            ar="مستندات الهوية مطلوبة",
        )

    push_enabled = bool((payload.fcm_token or "").strip())
    if db.get(ListenerPrivacySettingsRow, user.id) is None:
        db.add(ListenerPrivacySettingsRow(listener_id=user.id))
    notif = db.get(ListenerNotificationPreferencesRow, user.id)
    if notif is None:
        db.add(
            ListenerNotificationPreferencesRow(
                listener_id=user.id,
                push_enabled=push_enabled,
                email_enabled=push_enabled,
            )
        )
    else:
        notif.push_enabled = push_enabled
        notif.email_enabled = push_enabled
    if db.get(ListenerWallet, user.id) is None:
        db.add(ListenerWallet(listener_id=user.id))

    identity.status = ProfileStatus.under_review
    profile.profile_status = ProfileStatus.under_review
    profile.agreed_to_terms_at = _utc_now()
    upsert_push_token(db, user.id, payload.fcm_token)
    mark_step_done(user, "notifications", LISTENER_REGISTER_STEPS)
    user.registration_complete = True
    db.commit()

    return RegisterListenerResponse(
        listener_id=str(user.id),
        profile_status=ProfileStatusOut.under_review,
    )
