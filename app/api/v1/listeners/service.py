"""Listener business logic."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.listeners.schemas import (
    AvailabilityDay,
    AvailabilityPayload,
    DashboardImpact,
    DashboardResponse,
    DashboardUpcomingSession,
    DayAvailabilityResponse,
    DayOfWeekOut,
    IdentityStatusOut,
    IdentityVerificationResponse,
    ImpactChartPoint,
    ListenerNotificationPreferences,
    ListenerPrivacySettings,
    ListenerProfileResponse,
    ListenerProfileUpdate,
    ListenerPublicResponse,
    OnlineStatusResponse,
    ProfileStatusOut,
    RegisterListenerResponse,
    ReviewItem,
    ReviewsResponse,
    SetupProgressResponse,
    SetupStepId,
    SetupStepItem,
    SetupStepStatusOut,
    TimeSlot,
    TutorialAckRequest,
    VoiceIntroResponse,
)
from app.core.config import Settings
from app.core.errors import conflict, forbidden, not_found, validation_error
from app.models.auth import User
from app.models.availability import ListenerAvailabilitySettings, ListenerAvailabilitySlot
from app.models.earnings import ListenerWallet
from app.models.enums import (
    DayOfWeek,
    ProfileStatus,
    SessionStatus,
    SetupStepStatus,
    UserRole,
)
from app.models.lookups import (
    Boundary,
    ComfortArea,
    Language,
    LifeExperience,
    ListenerBoundary,
    ListenerComfortArea,
    ListenerLanguage,
    ListenerLifeExperience,
)
from app.models.profiles import (
    ListenerIdentityVerification,
    ListenerProfile,
    VentorProfile,
)
from app.models.sessions import Session as VentingSession
from app.models.sessions import SessionRating
from app.models.settings import (
    ListenerNotificationPreferences as ListenerNotificationPreferencesRow,
)
from app.models.settings import ListenerPrivacySettings as ListenerPrivacySettingsRow
from app.models.ventor_wellness import VentorFavorite

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
AUDIO_SUFFIXES = {".m4a", ".aac", ".mp3", ".wav", ".caf"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_today() -> date:
    return _utc_now().date()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _parse_json_list(raw: str | None, *, field: str, allow_empty: bool = False) -> list[str]:
    if raw is None or not str(raw).strip():
        if allow_empty:
            return []
        raise validation_error(f"{field} is required", ar=f"{field} مطلوب")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise validation_error(
            f"{field} must be a JSON array of strings",
            ar=f"{field} يجب أن يكون مصفوفة JSON",
        ) from exc
    if not isinstance(parsed, list) or not all(isinstance(i, str) for i in parsed):
        raise validation_error(
            f"{field} must be a JSON array of strings",
            ar=f"{field} يجب أن يكون مصفوفة JSON من النصوص",
        )
    if not parsed and not allow_empty:
        raise validation_error(f"{field} must not be empty", ar=f"{field} لا يمكن أن يكون فارغًا")
    seen: set[str] = set()
    out: list[str] = []
    for item in parsed:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_availability(raw: str | None) -> AvailabilityPayload:
    if raw is None or not str(raw).strip():
        return AvailabilityPayload()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise validation_error(
            "availability must be a JSON object",
            ar="يجب أن تكون التوفر كائن JSON",
        ) from exc
    try:
        return AvailabilityPayload.model_validate(data)
    except Exception as exc:
        raise validation_error(
            "Invalid availability payload",
            ar="بيانات التوفر غير صالحة",
        ) from exc


def _parse_bool(raw: str | bool | None, *, field: str, default: bool | None = None) -> bool:
    if raw is None:
        if default is not None:
            return default
        raise validation_error(f"{field} is required", ar=f"{field} مطلوب")
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise validation_error(f"{field} must be a boolean", ar=f"{field} يجب أن يكون قيمة منطقية")


def _parse_date(raw: str | None) -> date | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError as exc:
        raise validation_error(
            "date_of_birth must be YYYY-MM-DD",
            ar="تاريخ الميلاد يجب أن يكون بالصيغة YYYY-MM-DD",
        ) from exc


def _parse_time(value: str) -> time:
    try:
        parts = value.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return time(hour=hour, minute=minute)
    except (ValueError, IndexError) as exc:
        raise validation_error(
            f"Invalid time '{value}' (use HH:MM)",
            ar="وقت غير صالح",
        ) from exc


def _fmt_time(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


async def _save_upload(
    upload: UploadFile,
    *,
    dest_dir: Path,
    filename: str,
    allowed: set[str],
    max_bytes: int,
) -> str:
    suffix = Path(upload.filename or "").suffix.lower() or next(iter(allowed))
    if suffix not in allowed:
        raise validation_error(
            f"Unsupported file type {suffix}",
            ar="نوع الملف غير مدعوم",
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{filename}{suffix}"
    content = await upload.read()
    if not content:
        raise validation_error("Uploaded file is empty", ar="الملف المرفوع فارغ")
    if len(content) > max_bytes:
        raise validation_error("Uploaded file is too large", ar="الملف المرفوع كبير جدًا")
    dest.write_bytes(content)
    return "/" + dest.as_posix().lstrip("./")


def _static_url(settings: Settings, *parts: str) -> Path:
    return Path(settings.static_dir).joinpath(*parts)


def _validate_ids(db: Session, model, ids: list[str], *, field: str) -> None:
    if not ids:
        return
    found = {row.id for row in db.query(model).filter(model.id.in_(ids), model.is_active.is_(True)).all()}
    missing = [i for i in ids if i not in found]
    if missing:
        raise validation_error(
            f"Unknown {field}: {', '.join(missing)}",
            ar=f"{field} غير معروف",
        )


def _replace_tags(
    db: Session,
    *,
    listener_id: UUID,
    language_ids: list[str] | None = None,
    comfort_area_ids: list[str] | None = None,
    life_experience_ids: list[str] | None = None,
    boundary_ids: list[str] | None = None,
) -> None:
    if language_ids is not None:
        _validate_ids(db, Language, language_ids, field="language_ids")
        db.query(ListenerLanguage).filter(ListenerLanguage.listener_id == listener_id).delete()
        for lang_id in language_ids:
            db.add(ListenerLanguage(listener_id=listener_id, language_id=lang_id))
    if comfort_area_ids is not None:
        _validate_ids(db, ComfortArea, comfort_area_ids, field="comfort_area_ids")
        db.query(ListenerComfortArea).filter(ListenerComfortArea.listener_id == listener_id).delete()
        for area_id in comfort_area_ids:
            db.add(ListenerComfortArea(listener_id=listener_id, comfort_area_id=area_id))
    if life_experience_ids is not None:
        _validate_ids(db, LifeExperience, life_experience_ids, field="life_experience_ids")
        db.query(ListenerLifeExperience).filter(
            ListenerLifeExperience.listener_id == listener_id,
            ListenerLifeExperience.custom_label.is_(None),
        ).delete(synchronize_session=False)
        for exp_id in life_experience_ids:
            db.add(
                ListenerLifeExperience(listener_id=listener_id, life_experience_id=exp_id)
            )
    if boundary_ids is not None:
        _validate_ids(db, Boundary, boundary_ids, field="boundary_ids")
        db.query(ListenerBoundary).filter(ListenerBoundary.listener_id == listener_id).delete()
        for boundary_id in boundary_ids:
            db.add(ListenerBoundary(listener_id=listener_id, boundary_id=boundary_id))


def _apply_availability(
    db: Session,
    listener_id: UUID,
    availability: AvailabilityPayload,
    *,
    accept_instant_calls: bool | None = None,
    session_minutes: int | None = None,
) -> None:
    accept = (
        accept_instant_calls
        if accept_instant_calls is not None
        else availability.accept_instant_calls
    )
    session_length = (
        session_minutes
        if session_minutes is not None
        else availability.session_length_minutes
    )
    settings_row = db.get(ListenerAvailabilitySettings, listener_id)
    if settings_row is None:
        settings_row = ListenerAvailabilitySettings(
            listener_id=listener_id,
            accept_instant_calls=accept,
            session_length_minutes=session_length,
            break_length_minutes=availability.break_length_minutes,
            time_zone_id=availability.time_zone_id or "UTC",
        )
        db.add(settings_row)
    else:
        settings_row.accept_instant_calls = accept
        settings_row.session_length_minutes = session_length
        settings_row.break_length_minutes = availability.break_length_minutes
        settings_row.time_zone_id = availability.time_zone_id or settings_row.time_zone_id

    profile = db.get(ListenerProfile, listener_id)
    if profile is not None:
        profile.accept_instant_calls = accept
        profile.session_length_minutes = session_length
        profile.break_length_minutes = availability.break_length_minutes
        profile.time_zone_id = availability.time_zone_id or profile.time_zone_id

    db.query(ListenerAvailabilitySlot).filter(
        ListenerAvailabilitySlot.listener_id == listener_id
    ).delete()
    for day in availability.days:
        for slot in day.slots:
            start = _parse_time(slot.start)
            end = _parse_time(slot.end)
            if end <= start:
                raise validation_error(
                    f"Slot end must be after start for {day.day.value}",
                    ar="يجب أن يكون وقت النهاية بعد البداية",
                )
            db.add(
                ListenerAvailabilitySlot(
                    listener_id=listener_id,
                    day=DayOfWeek(day.day.value),
                    start_time=start,
                    end_time=end,
                )
            )

    if availability.language_ids:
        _replace_tags(db, listener_id=listener_id, language_ids=availability.language_ids)


def _load_tag_ids(db: Session, listener_id: UUID) -> dict[str, list[str]]:
    languages = [
        r.language_id
        for r in db.query(ListenerLanguage)
        .filter(ListenerLanguage.listener_id == listener_id)
        .order_by(ListenerLanguage.language_id)
        .all()
    ]
    comfort = [
        r.comfort_area_id
        for r in db.query(ListenerComfortArea)
        .filter(ListenerComfortArea.listener_id == listener_id)
        .order_by(ListenerComfortArea.comfort_area_id)
        .all()
    ]
    experiences = [
        r.life_experience_id
        for r in db.query(ListenerLifeExperience)
        .filter(ListenerLifeExperience.listener_id == listener_id)
        .order_by(ListenerLifeExperience.life_experience_id)
        .all()
    ]
    boundaries = [
        r.boundary_id
        for r in db.query(ListenerBoundary)
        .filter(ListenerBoundary.listener_id == listener_id)
        .order_by(ListenerBoundary.boundary_id)
        .all()
    ]
    return {
        "languages": languages,
        "comfort": comfort,
        "experiences": experiences,
        "boundaries": boundaries,
    }


def get_availability_payload(db: Session, listener_id: UUID) -> AvailabilityPayload:
    settings_row = db.get(ListenerAvailabilitySettings, listener_id)
    profile = db.get(ListenerProfile, listener_id)
    tags = _load_tag_ids(db, listener_id)
    slots = (
        db.query(ListenerAvailabilitySlot)
        .filter(ListenerAvailabilitySlot.listener_id == listener_id)
        .order_by(ListenerAvailabilitySlot.day, ListenerAvailabilitySlot.start_time)
        .all()
    )
    by_day: dict[str, list[TimeSlot]] = {d.value: [] for d in DayOfWeekOut}
    for slot in slots:
        by_day[slot.day.value].append(
            TimeSlot(start=_fmt_time(slot.start_time), end=_fmt_time(slot.end_time))
        )
    days = [
        AvailabilityDay(day=DayOfWeekOut(day), slots=by_day[day])
        for day in by_day
        if by_day[day]
    ]
    return AvailabilityPayload(
        accept_instant_calls=(
            settings_row.accept_instant_calls
            if settings_row
            else bool(profile.accept_instant_calls if profile else True)
        ),
        session_length_minutes=(
            settings_row.session_length_minutes
            if settings_row
            else (profile.session_length_minutes if profile else 30)
        ),
        break_length_minutes=(
            settings_row.break_length_minutes
            if settings_row
            else (profile.break_length_minutes if profile else 15)
        ),
        language_ids=tags["languages"],
        time_zone_id=(
            settings_row.time_zone_id
            if settings_row
            else (profile.time_zone_id if profile else "UTC")
        ),
        days=days,
    )


def _profile_response(db: Session, user: User, profile: ListenerProfile) -> ListenerProfileResponse:
    tags = _load_tag_ids(db, profile.user_id)
    return ListenerProfileResponse(
        id=str(profile.user_id),
        full_name=profile.full_name,
        email=user.email,
        phone=profile.phone_e164,
        phone_country=profile.phone_country_iso,
        avatar_url=profile.avatar_url,
        about_me=profile.about_me,
        country=profile.country,
        country_iso=profile.country_iso,
        city=profile.city,
        language_ids=tags["languages"],
        life_experiences=tags["experiences"],
        comfort_areas=tags["comfort"],
        boundaries=tags["boundaries"],
        voice_intro_url=profile.voice_intro_url,
        voice_intro_seconds=profile.voice_intro_seconds,
        rating=float(profile.rating_avg or 0),
        review_count=profile.rating_count,
        session_count=profile.session_count,
        is_online=profile.is_online,
        profile_status=ProfileStatusOut(profile.profile_status.value),
        rate_per_minute=float(profile.rate_per_minute or 0),
    )


def _map_identity_status(status: ProfileStatus) -> IdentityStatusOut:
    if status == ProfileStatus.approved:
        return IdentityStatusOut.approved
    if status == ProfileStatus.rejected:
        return IdentityStatusOut.rejected
    return IdentityStatusOut.pending


def _setup_progress(profile: ListenerProfile) -> SetupProgressResponse:
    steps = [
        SetupStepItem(
            id=SetupStepId.identity_verified,
            status=SetupStepStatusOut(profile.setup_identity_status.value),
        ),
        SetupStepItem(
            id=SetupStepId.profile_info,
            status=SetupStepStatusOut(profile.setup_profile_status.value),
        ),
        SetupStepItem(
            id=SetupStepId.availability,
            status=SetupStepStatusOut(profile.setup_availability_status.value),
        ),
        SetupStepItem(
            id=SetupStepId.training,
            status=SetupStepStatusOut(profile.setup_training_status.value),
        ),
        SetupStepItem(
            id=SetupStepId.first_session_tutorial,
            status=SetupStepStatusOut(profile.setup_tutorial_status.value),
        ),
    ]
    done = sum(1 for step in steps if step.status == SetupStepStatusOut.done)
    return SetupProgressResponse(
        profile_approved=profile.profile_status == ProfileStatus.approved,
        progress_percent=int(round((done / len(steps)) * 100)),
        steps=steps,
    )


def _when_label(moment: datetime | None) -> str:
    if moment is None:
        return "Soon"
    moment = _as_utc(moment)
    today = _utc_today()
    local_date = moment.date()
    hour = moment.hour % 12 or 12
    ampm = "AM" if moment.hour < 12 else "PM"
    clock = f"{hour}:{moment.minute:02d} {ampm}"
    if local_date == today:
        return f"Today {clock}"
    if local_date == today + timedelta(days=1):
        return f"Tomorrow {clock}"
    return f"{moment.strftime('%b')} {moment.day} · {clock}"


async def register_listener(
    db: Session,
    user: User,
    *,
    settings: Settings,
    full_name: str,
    phone: str | None,
    phone_country: str | None,
    agreed_to_terms: str | bool,
    date_of_birth: str | None,
    country_iso: str | None,
    city: str | None,
    language_ids_raw: str | None,
    life_experience_ids_raw: str | None,
    custom_experiences_raw: str | None,
    comfort_area_ids_raw: str | None,
    boundary_ids_raw: str | None,
    availability_raw: str | None,
    accept_instant_calls: str | bool | None,
    session_minutes: int | None,
    notifications_enabled: str | bool | None,
    avatar: UploadFile | None,
    identity_document_front: UploadFile | None,
    identity_document_back: UploadFile | None,
    selfie: UploadFile | None,
    voice_intro: UploadFile | None,
    voice_intro_seconds: int | None,
) -> RegisterListenerResponse:
    if user.role != UserRole.listener:
        raise forbidden()
    if db.get(ListenerProfile, user.id) is not None:
        raise conflict(
            "Listener profile already exists",
            ar="ملف المستمع موجود بالفعل",
        )
    if not _parse_bool(agreed_to_terms, field="agreed_to_terms"):
        raise validation_error(
            "agreed_to_terms must be true",
            ar="يجب الموافقة على الشروط",
        )

    full_name = full_name.strip()
    if not full_name or len(full_name) > 120:
        raise validation_error(
            "full_name must be 1–120 characters",
            ar="الاسم يجب أن يكون بين 1 و 120 حرفًا",
        )

    language_ids = _parse_json_list(language_ids_raw, field="language_ids")
    life_experience_ids = _parse_json_list(
        life_experience_ids_raw, field="life_experience_ids", allow_empty=True
    )
    custom_experiences = _parse_json_list(
        custom_experiences_raw, field="custom_experiences", allow_empty=True
    )
    comfort_area_ids = _parse_json_list(comfort_area_ids_raw, field="comfort_area_ids")
    boundary_ids = _parse_json_list(boundary_ids_raw, field="boundary_ids", allow_empty=True)
    availability = _parse_availability(availability_raw)
    accept_instant = _parse_bool(
        accept_instant_calls, field="accept_instant_calls", default=True
    )
    notif_enabled = _parse_bool(
        notifications_enabled, field="notifications_enabled", default=True
    )
    dob = _parse_date(date_of_birth)

    avatar_url = None
    if avatar is not None and avatar.filename:
        avatar_url = await _save_upload(
            avatar,
            dest_dir=_static_url(settings, "uploads", "avatars"),
            filename=str(user.id),
            allowed=IMAGE_SUFFIXES,
            max_bytes=5 * 1024 * 1024,
        )

    if identity_document_front is None or not identity_document_front.filename:
        raise validation_error(
            "identity_document_front is required",
            ar="صورة الوجه الأمامي للمستند مطلوبة",
        )
    if selfie is None or not selfie.filename:
        raise validation_error("selfie is required", ar="صورة السيلفي مطلوبة")

    front_url = await _save_upload(
        identity_document_front,
        dest_dir=_static_url(settings, "uploads", "identity", str(user.id)),
        filename="document_front",
        allowed=IMAGE_SUFFIXES,
        max_bytes=10 * 1024 * 1024,
    )
    back_url = None
    if identity_document_back is not None and identity_document_back.filename:
        back_url = await _save_upload(
            identity_document_back,
            dest_dir=_static_url(settings, "uploads", "identity", str(user.id)),
            filename="document_back",
            allowed=IMAGE_SUFFIXES,
            max_bytes=10 * 1024 * 1024,
        )
    selfie_url = await _save_upload(
        selfie,
        dest_dir=_static_url(settings, "uploads", "identity", str(user.id)),
        filename="selfie",
        allowed=IMAGE_SUFFIXES,
        max_bytes=10 * 1024 * 1024,
    )

    voice_url = None
    if voice_intro is not None and voice_intro.filename:
        voice_url = await _save_upload(
            voice_intro,
            dest_dir=_static_url(settings, "uploads", "voice"),
            filename=str(user.id),
            allowed=AUDIO_SUFFIXES,
            max_bytes=20 * 1024 * 1024,
        )

    tz = availability.time_zone_id or "UTC"
    session_length = session_minutes or availability.session_length_minutes or 30

    profile = ListenerProfile(
        user_id=user.id,
        full_name=full_name,
        phone_e164=phone.strip() if phone else None,
        phone_country_iso=phone_country.strip().upper() if phone_country else None,
        avatar_url=avatar_url,
        date_of_birth=dob,
        country_iso=country_iso.strip().upper() if country_iso else None,
        city=city.strip() if city else None,
        voice_intro_url=voice_url,
        voice_intro_seconds=voice_intro_seconds,
        profile_status=ProfileStatus.under_review,
        accept_instant_calls=accept_instant,
        session_length_minutes=session_length,
        break_length_minutes=availability.break_length_minutes,
        time_zone_id=tz,
        setup_identity_status=SetupStepStatus.in_progress,
        setup_profile_status=SetupStepStatus.done,
        setup_availability_status=SetupStepStatus.done if availability.days else SetupStepStatus.in_progress,
        setup_training_status=SetupStepStatus.locked,
        setup_tutorial_status=SetupStepStatus.locked,
        agreed_to_terms_at=_utc_now(),
    )
    db.add(profile)
    db.flush()

    db.add(
        ListenerIdentityVerification(
            listener_id=user.id,
            document_front_url=front_url,
            document_back_url=back_url,
            selfie_url=selfie_url,
            status=ProfileStatus.under_review,
        )
    )
    _replace_tags(
        db,
        listener_id=user.id,
        language_ids=language_ids or availability.language_ids,
        comfort_area_ids=comfort_area_ids,
        life_experience_ids=life_experience_ids,
        boundary_ids=boundary_ids,
    )
    for index, label in enumerate(custom_experiences):
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40] or "custom"
        exp_id = f"custom_{user.id.hex[:8]}_{index}_{slug}"[:64]
        if db.get(LifeExperience, exp_id) is None:
            db.add(
                LifeExperience(
                    id=exp_id,
                    name_en=label[:120],
                    name_ar=label[:120],
                    is_active=True,
                )
            )
            db.flush()
        db.add(
            ListenerLifeExperience(
                listener_id=user.id,
                life_experience_id=exp_id,
                custom_label=label[:120],
            )
        )

    _apply_availability(
        db,
        user.id,
        availability,
        accept_instant_calls=accept_instant,
        session_minutes=session_length,
    )
    db.add(ListenerPrivacySettingsRow(listener_id=user.id))
    db.add(
        ListenerNotificationPreferencesRow(
            listener_id=user.id,
            push_enabled=notif_enabled,
            email_enabled=notif_enabled,
        )
    )
    db.add(ListenerWallet(listener_id=user.id))
    user.registration_complete = True
    db.commit()

    return RegisterListenerResponse(
        listener_id=str(user.id),
        profile_status=ProfileStatusOut.under_review,
    )


async def submit_identity_verification(
    db: Session,
    profile: ListenerProfile,
    *,
    settings: Settings,
    document_front: UploadFile,
    document_back: UploadFile | None,
    selfie: UploadFile,
) -> IdentityVerificationResponse:
    if document_front.filename is None:
        raise validation_error("document_front is required", ar="صورة المستند مطلوبة")
    if selfie.filename is None:
        raise validation_error("selfie is required", ar="صورة السيلفي مطلوبة")

    front_url = await _save_upload(
        document_front,
        dest_dir=_static_url(settings, "uploads", "identity", str(profile.user_id)),
        filename="document_front",
        allowed=IMAGE_SUFFIXES,
        max_bytes=10 * 1024 * 1024,
    )
    back_url = None
    if document_back is not None and document_back.filename:
        back_url = await _save_upload(
            document_back,
            dest_dir=_static_url(settings, "uploads", "identity", str(profile.user_id)),
            filename="document_back",
            allowed=IMAGE_SUFFIXES,
            max_bytes=10 * 1024 * 1024,
        )
    selfie_url = await _save_upload(
        selfie,
        dest_dir=_static_url(settings, "uploads", "identity", str(profile.user_id)),
        filename="selfie",
        allowed=IMAGE_SUFFIXES,
        max_bytes=10 * 1024 * 1024,
    )
    row = ListenerIdentityVerification(
        listener_id=profile.user_id,
        document_front_url=front_url,
        document_back_url=back_url,
        selfie_url=selfie_url,
        status=ProfileStatus.under_review,
    )
    db.add(row)
    profile.setup_identity_status = SetupStepStatus.in_progress
    if profile.profile_status == ProfileStatus.incomplete:
        profile.profile_status = ProfileStatus.under_review
    db.commit()
    return IdentityVerificationResponse(status=IdentityStatusOut.pending)


def get_listener_profile(
    db: Session, user: User, profile: ListenerProfile
) -> ListenerProfileResponse:
    return _profile_response(db, user, profile)


def update_listener_profile(
    db: Session,
    user: User,
    profile: ListenerProfile,
    payload: ListenerProfileUpdate,
) -> ListenerProfileResponse:
    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data and data["full_name"] is not None:
        name = data["full_name"].strip()
        if not name:
            raise validation_error("full_name cannot be empty", ar="الاسم لا يمكن أن يكون فارغًا")
        profile.full_name = name
    if "phone" in data:
        profile.phone_e164 = data["phone"]
    if "phone_country" in data:
        profile.phone_country_iso = (
            data["phone_country"].upper() if data["phone_country"] else None
        )
    if "about_me" in data:
        profile.about_me = data["about_me"]
    if "bio" in data:
        profile.bio = data["bio"]
    if "country" in data:
        profile.country = data["country"]
    if "country_iso" in data:
        profile.country_iso = (
            data["country_iso"].upper() if data["country_iso"] else None
        )
    if "city" in data:
        profile.city = data["city"]

    _replace_tags(
        db,
        listener_id=profile.user_id,
        language_ids=data.get("language_ids"),
        life_experience_ids=data.get("life_experiences"),
        comfort_area_ids=data.get("comfort_areas"),
        boundary_ids=data.get("boundaries"),
    )
    db.commit()
    db.refresh(profile)
    return _profile_response(db, user, profile)


async def upload_voice_intro(
    db: Session,
    profile: ListenerProfile,
    *,
    settings: Settings,
    audio: UploadFile,
    duration_seconds: int | None,
) -> VoiceIntroResponse:
    if audio.filename is None:
        raise validation_error("audio is required", ar="ملف الصوت مطلوب")
    url = await _save_upload(
        audio,
        dest_dir=_static_url(settings, "uploads", "voice"),
        filename=str(profile.user_id),
        allowed=AUDIO_SUFFIXES,
        max_bytes=20 * 1024 * 1024,
    )
    profile.voice_intro_url = url
    if duration_seconds is not None:
        profile.voice_intro_seconds = duration_seconds
    db.commit()
    db.refresh(profile)
    return VoiceIntroResponse(
        voice_intro_url=profile.voice_intro_url or url,
        voice_intro_seconds=profile.voice_intro_seconds,
    )


def list_reviews(
    db: Session,
    profile: ListenerProfile,
    *,
    page: int = 1,
    page_size: int = 20,
) -> ReviewsResponse:
    from app.core.pagination import clamp_page

    page, page_size = clamp_page(page, page_size)
    query = (
        db.query(SessionRating, VentorProfile)
        .outerjoin(VentorProfile, VentorProfile.user_id == SessionRating.ventor_id)
        .filter(SessionRating.listener_id == profile.user_id)
    )
    total = query.with_entities(func.count(SessionRating.id)).scalar() or 0
    rows = (
        query.order_by(SessionRating.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        ReviewItem(
            id=str(rating.id),
            reviewer_name=ventor.nickname if ventor is not None else "Ventor",
            rating=rating.stars,
            comment=rating.review,
            created_at=_iso(rating.created_at),
        )
        for rating, ventor in rows
    ]
    return ReviewsResponse(
        rating=float(profile.rating_avg or 0),
        review_count=profile.rating_count,
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_public_listener(
    db: Session,
    listener_id: UUID,
    *,
    viewer: User,
) -> ListenerPublicResponse:
    profile = db.get(ListenerProfile, listener_id)
    if profile is None or profile.profile_status == ProfileStatus.incomplete:
        raise not_found("Listener")

    tags = _load_tag_ids(db, listener_id)
    is_favorite = False
    if viewer.role == UserRole.ventor:
        is_favorite = (
            db.query(VentorFavorite)
            .filter(
                VentorFavorite.ventor_id == viewer.id,
                VentorFavorite.listener_id == listener_id,
            )
            .first()
            is not None
        )

    return ListenerPublicResponse(
        id=str(profile.user_id),
        name=profile.full_name,
        avatar_url=profile.avatar_url,
        rating=float(profile.rating_avg or 0),
        review_count=profile.rating_count,
        session_count=profile.session_count,
        topics=tags["comfort"],
        languages=tags["languages"],
        gender=profile.gender.value if profile.gender else None,
        rate_per_minute=float(profile.rate_per_minute or 0),
        bio=profile.bio or profile.about_me,
        help_with=tags["comfort"],
        voice_preview_seconds=profile.voice_intro_seconds,
        is_online=profile.is_online,
        is_verified=profile.is_verified,
        rating_breakdown=profile.rating_breakdown,
        country=profile.country,
        city=profile.city,
        country_iso=profile.country_iso,
        life_experiences=tags["experiences"],
        boundaries=tags["boundaries"],
        availability=get_availability_payload(db, listener_id),
        is_favorite=is_favorite,
    )


def get_setup_progress(profile: ListenerProfile) -> SetupProgressResponse:
    return _setup_progress(profile)


def acknowledge_tutorial(
    db: Session,
    profile: ListenerProfile,
    payload: TutorialAckRequest,
) -> SetupProgressResponse:
    if not payload.acknowledged:
        raise validation_error(
            "acknowledged must be true",
            ar="يجب تأكيد الإقرار",
        )
    profile.setup_tutorial_status = SetupStepStatus.done
    profile.first_session_tutorial_acked_at = _utc_now()
    db.commit()
    db.refresh(profile)
    return _setup_progress(profile)


def set_online_status(
    db: Session,
    profile: ListenerProfile,
    *,
    is_online: bool,
) -> OnlineStatusResponse:
    profile.is_online = is_online
    db.commit()
    return OnlineStatusResponse(is_online=profile.is_online)


def get_dashboard(db: Session, profile: ListenerProfile) -> DashboardResponse:
    today = _utc_today()
    start_today = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end_today = start_today + timedelta(days=1)

    today_sessions = (
        db.query(VentingSession)
        .filter(
            VentingSession.listener_id == profile.user_id,
            VentingSession.status == SessionStatus.completed,
            VentingSession.ended_at >= start_today,
            VentingSession.ended_at < end_today,
        )
        .all()
    )
    sessions_today = len(today_sessions)
    minutes_today = sum(
        (s.actual_duration_seconds or s.duration_minutes * 60) // 60 for s in today_sessions
    )

    chart: list[ImpactChartPoint] = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        count = (
            db.query(func.count(VentingSession.id))
            .filter(
                VentingSession.listener_id == profile.user_id,
                VentingSession.status == SessionStatus.completed,
                VentingSession.ended_at >= day_start,
                VentingSession.ended_at < day_end,
            )
            .scalar()
            or 0
        )
        chart.append(ImpactChartPoint(label=day.strftime("%a"), value=float(count)))

    upcoming = (
        db.query(VentingSession, VentorProfile)
        .outerjoin(VentorProfile, VentorProfile.user_id == VentingSession.ventor_id)
        .filter(
            VentingSession.listener_id == profile.user_id,
            VentingSession.status.in_([SessionStatus.upcoming, SessionStatus.live]),
        )
        .order_by(VentingSession.scheduled_at.asc().nullslast())
        .first()
    )
    next_session = None
    if upcoming is not None:
        session, ventor = upcoming
        next_session = DashboardUpcomingSession(
            id=str(session.id),
            ventor_name=ventor.nickname if ventor else "Ventor",
            when_label=_when_label(session.scheduled_at or session.started_at),
            duration_minutes=session.duration_minutes,
        )

    reminder = None
    progress = _setup_progress(profile)
    if not progress.profile_approved:
        reminder = "Your profile is under review"
    elif any(step.status != SetupStepStatusOut.done for step in progress.steps):
        reminder = "Finish setup to unlock more sessions"

    return DashboardResponse(
        display_name=profile.full_name,
        setup_progress=progress,
        impact=DashboardImpact(
            sessions_today=sessions_today,
            minutes_today=minutes_today,
            chart=chart,
        ),
        next_upcoming_session=next_session,
        is_online=profile.is_online,
        reminder=reminder,
    )


def get_privacy(db: Session, profile: ListenerProfile) -> ListenerPrivacySettings:
    row = db.get(ListenerPrivacySettingsRow, profile.user_id)
    if row is None:
        row = ListenerPrivacySettingsRow(listener_id=profile.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return ListenerPrivacySettings(
        show_online_status=row.show_online_status,
        show_languages=row.show_languages,
        show_comfort_areas=row.show_comfort_areas,
        show_experience_and_ratings=row.show_experience_and_ratings,
        show_boundaries=row.show_boundaries,
        visible_in_all_countries=row.visible_in_all_countries,
        visible_countries=list(row.visible_countries) if row.visible_countries else None,
        allow_search_indexing=row.allow_search_indexing,
    )


def update_privacy(
    db: Session,
    profile: ListenerProfile,
    payload: ListenerPrivacySettings,
) -> ListenerPrivacySettings:
    row = db.get(ListenerPrivacySettingsRow, profile.user_id)
    if row is None:
        row = ListenerPrivacySettingsRow(listener_id=profile.user_id)
        db.add(row)
    row.show_online_status = payload.show_online_status
    row.show_languages = payload.show_languages
    row.show_comfort_areas = payload.show_comfort_areas
    row.show_experience_and_ratings = payload.show_experience_and_ratings
    row.show_boundaries = payload.show_boundaries
    row.visible_in_all_countries = payload.visible_in_all_countries
    row.visible_countries = payload.visible_countries
    row.allow_search_indexing = payload.allow_search_indexing
    db.commit()
    db.refresh(row)
    return get_privacy(db, profile)


def get_notification_preferences(
    db: Session,
    profile: ListenerProfile,
) -> ListenerNotificationPreferences:
    row = db.get(ListenerNotificationPreferencesRow, profile.user_id)
    if row is None:
        row = ListenerNotificationPreferencesRow(listener_id=profile.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return ListenerNotificationPreferences(
        push_enabled=row.push_enabled,
        new_session_requests=row.new_session_requests,
        session_reminder_15_min=row.session_reminder_15_min,
        session_reminder_10_min=row.session_reminder_10_min,
        session_reminder_5_min=row.session_reminder_5_min,
        reviews_feedback=row.reviews_feedback,
        tips_earnings=row.tips_earnings,
        promotions_updates=row.promotions_updates,
        email_enabled=row.email_enabled,
    )


def update_notification_preferences(
    db: Session,
    profile: ListenerProfile,
    payload: ListenerNotificationPreferences,
) -> ListenerNotificationPreferences:
    row = db.get(ListenerNotificationPreferencesRow, profile.user_id)
    if row is None:
        row = ListenerNotificationPreferencesRow(listener_id=profile.user_id)
        db.add(row)
    row.push_enabled = payload.push_enabled
    row.new_session_requests = payload.new_session_requests
    row.session_reminder_15_min = payload.session_reminder_15_min
    row.session_reminder_10_min = payload.session_reminder_10_min
    row.session_reminder_5_min = payload.session_reminder_5_min
    row.reviews_feedback = payload.reviews_feedback
    row.tips_earnings = payload.tips_earnings
    row.promotions_updates = payload.promotions_updates
    row.email_enabled = payload.email_enabled
    db.commit()
    db.refresh(row)
    return get_notification_preferences(db, profile)


def get_availability(db: Session, profile: ListenerProfile) -> AvailabilityPayload:
    return get_availability_payload(db, profile.user_id)


def put_availability(
    db: Session,
    profile: ListenerProfile,
    payload: AvailabilityPayload,
) -> AvailabilityPayload:
    _apply_availability(db, profile.user_id, payload)
    profile.setup_availability_status = SetupStepStatus.done
    db.commit()
    return get_availability_payload(db, profile.user_id)


def put_availability_day(
    db: Session,
    profile: ListenerProfile,
    day: DayOfWeekOut,
    slots: list[TimeSlot],
) -> DayAvailabilityResponse:
    db.query(ListenerAvailabilitySlot).filter(
        ListenerAvailabilitySlot.listener_id == profile.user_id,
        ListenerAvailabilitySlot.day == DayOfWeek(day.value),
    ).delete()
    for slot in slots:
        start = _parse_time(slot.start)
        end = _parse_time(slot.end)
        if end <= start:
            raise validation_error(
                "Slot end must be after start",
                ar="يجب أن يكون وقت النهاية بعد البداية",
            )
        db.add(
            ListenerAvailabilitySlot(
                listener_id=profile.user_id,
                day=DayOfWeek(day.value),
                start_time=start,
                end_time=end,
            )
        )
    profile.setup_availability_status = SetupStepStatus.done
    db.commit()
    return DayAvailabilityResponse(day=day, slots=slots)
