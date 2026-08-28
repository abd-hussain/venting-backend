from uuid import UUID

import json

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status

from app.api.v1.listeners.parse import form_json_list_raw, parse_session_minutes

from app.api.deps import (
    CurrentListener,
    CurrentListenerProfile,
    CurrentUser,
    CurrentVentor,
    DbSession,
    SettingsDep,
)
from app.api.v1.listeners.schemas import (
    AvailabilityPayload,
    DashboardResponse,
    DayAvailabilityResponse,
    DayOfWeekOut,
    DaySlotsUpdate,
    IdentityVerificationResponse,
    ListenerListResponse,
    ListenerNotificationPreferences,
    ListenerPrivacySettings,
    ListenerProfileResponse,
    ListenerProfileUpdate,
    ListenerPublicResponse,
    ListenerRegisterAboutRequest,
    ListenerRegisterAvailabilityRequest,
    ListenerRegisterBoundariesRequest,
    ListenerRegisterComfortAreasRequest,
    ListenerRegisterCompleteRequest,
    ListenerRegisterExperiencesRequest,
    ListenerRegisterProgressResponse,
    ListenerRegisterVoiceIntroRequest,
    OnlineStatusRequest,
    OnlineStatusResponse,
    RegisterListenerResponse,
    ReviewsResponse,
    SetupProgressResponse,
    TutorialAckRequest,
    VoiceIntroResponse,
)
from app.api.v1.listeners.register_service import (
    complete_register as complete_listener_register,
    get_register_progress as get_listener_register_progress,
    save_register_about_step,
    save_register_availability_step,
    save_register_boundaries_step,
    save_register_comfort_areas_step,
    save_register_experiences_step,
    save_register_identity_step,
    save_register_profile_step,
    save_register_voice_intro_step,
)
from app.api.v1.listeners.earnings_service import (
    CreatePayoutRequest,
    UpsertPayoutMethodRequest,
)
from app.api.v1.sessions.schemas import DeclineRequestBody
from app.api.v1.listeners.service import (
    acknowledge_tutorial,
    get_dashboard,
    get_listener_profile,
    get_notification_preferences,
    get_privacy,
    get_public_listener,
    get_setup_progress,
    list_reviews,
    set_online_status,
    submit_identity_verification,
    update_listener_profile,
    update_notification_preferences,
    update_privacy,
    upload_avatar,
    upload_voice_intro,
)
from app.core.errors import validation_error
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


def _upload(form, name: str, fallback: UploadFile | None = None) -> UploadFile | None:
    value = form.get(name)
    if isinstance(value, UploadFile) and value.filename:
        return value
    if fallback is not None and fallback.filename:
        return fallback
    return None


@router.get(
    "/register/progress",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get listener registration progress (#22a)",
)
def register_progress(
    current_user: CurrentListener,
    db: DbSession,
):
    data = get_listener_register_progress(db, current_user)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/profile",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration profile step (#22b)",
)
async def register_step_profile(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
    settings: SettingsDep,
    avatar: UploadFile | None = File(None),
    full_name: str | None = Form(None),
    phone: str | None = Form(None),
    phone_country: str | None = Form(None),
):
    form = await request.form()
    data = await save_register_profile_step(
        db,
        current_user,
        full_name=str(form.get("full_name") or full_name or ""),
        phone=str(form.get("phone") or phone or "") or None,
        phone_country=str(form.get("phone_country") or phone_country or "") or None,
        avatar=_upload(form, "avatar", avatar),
        settings=settings,
    )
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/identity",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration identity step (#22c)",
)
async def register_step_identity(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
    settings: SettingsDep,
    identity_document: UploadFile | None = File(None),
    selfie: UploadFile | None = File(None),
):
    form = await request.form()
    data = await save_register_identity_step(
        db,
        current_user,
        identity_document=_upload(form, "identity_document", identity_document),
        selfie=_upload(form, "selfie", selfie),
        settings=settings,
    )
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/about",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration about step (#22d)",
)
async def register_step_about(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = ListenerRegisterAboutRequest.model_validate(await request.json())
    else:
        form = await request.form()
        body = ListenerRegisterAboutRequest(
            date_of_birth=str(form.get("date_of_birth") or ""),
            country_iso=str(form.get("country_iso") or ""),
            city=str(form.get("city") or ""),
            language_ids=json.loads(form_json_list_raw(form, "language_ids") or "[]"),
        )
    data = save_register_about_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/experiences",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration experiences step (#22e)",
)
async def register_step_experiences(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    body = ListenerRegisterExperiencesRequest.model_validate(await request.json())
    data = save_register_experiences_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/comfort-areas",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration comfort areas step (#22f)",
)
async def register_step_comfort_areas(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    body = ListenerRegisterComfortAreasRequest.model_validate(await request.json())
    data = save_register_comfort_areas_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/boundaries",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration boundaries step (#22g)",
)
async def register_step_boundaries(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    body = ListenerRegisterBoundariesRequest.model_validate(await request.json())
    data = save_register_boundaries_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/voice-intro",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration voice intro step (#22h)",
)
async def register_step_voice_intro(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
    settings: SettingsDep,
    voice_intro: UploadFile | None = File(None),
    voice_intro_seconds: str | None = Form(None),
):
    form = await request.form()
    seconds = parse_session_minutes(
        str(form.get("voice_intro_seconds") or voice_intro_seconds or "")
        or None
    )
    if seconds is None:
        raise validation_error(
            "voice_intro_seconds is required",
            ar="voice_intro_seconds مطلوب",
        )
    body = ListenerRegisterVoiceIntroRequest(voice_intro_seconds=seconds)
    data = await save_register_voice_intro_step(
        db,
        current_user,
        payload=body,
        voice_intro=_upload(form, "voice_intro", voice_intro),
        settings=settings,
    )
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/availability",
    response_model=APISuccessResponse[ListenerRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save listener registration availability step (#22i)",
)
async def register_step_availability(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    body = ListenerRegisterAvailabilityRequest.model_validate(await request.json())
    data = save_register_availability_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/register/complete",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[RegisterListenerResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Complete listener registration (#22j)",
)
async def register_complete(
    request: Request,
    current_user: CurrentListener,
    db: DbSession,
):
    body = ListenerRegisterCompleteRequest.model_validate(await request.json())
    data = complete_listener_register(db, current_user, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.post(
    "/me/identity-verification",
    response_model=APISuccessResponse[IdentityVerificationResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Resubmit identity documents after admin rejection",
)
async def identity_verification(
    profile: CurrentListenerProfile,
    db: DbSession,
    settings: SettingsDep,
    selfie: UploadFile = File(...),
    identity_document: UploadFile | None = File(
        None, description="Single government-ID photo"
    ),
    document_front: UploadFile | None = File(
        None, description="Legacy alias for identity_document"
    ),
):
    doc = identity_document or document_front
    if doc is None or not doc.filename:
        raise validation_error(
            "identity_document is required",
            ar="صورة وثيقة الهوية مطلوبة",
        )
    data = await submit_identity_verification(
        db,
        profile,
        settings=settings,
        identity_document=doc,
        selfie=selfie,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me",
    response_model=APISuccessResponse[ListenerProfileResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get current listener profile",
)
def me(current_user: CurrentUser, profile: CurrentListenerProfile, db: DbSession):
    data = get_listener_profile(db, current_user, profile)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/me",
    response_model=APISuccessResponse[ListenerProfileResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update listener profile",
)
def patch_me(
    body: ListenerProfileUpdate,
    current_user: CurrentUser,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    data = update_listener_profile(db, current_user, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/avatar",
    response_model=APISuccessResponse[ListenerProfileResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Upload listener avatar (#25b)",
)
async def avatar_upload(
    current_user: CurrentUser,
    profile: CurrentListenerProfile,
    db: DbSession,
    settings: SettingsDep,
    avatar: UploadFile = File(...),
):
    data = await upload_avatar(
        db,
        current_user,
        profile,
        settings=settings,
        avatar=avatar,
    )
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/voice-intro",
    response_model=APISuccessResponse[VoiceIntroResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Upload voice intro",
)
async def voice_intro(
    profile: CurrentListenerProfile,
    db: DbSession,
    settings: SettingsDep,
    audio: UploadFile = File(...),
    voice_intro_seconds: int | None = Form(None),
    duration_seconds: int | None = Form(None),
):
    seconds = (
        voice_intro_seconds if voice_intro_seconds is not None else duration_seconds
    )
    data = await upload_voice_intro(
        db,
        profile,
        settings=settings,
        audio=audio,
        voice_intro_seconds=seconds,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/reviews",
    response_model=APISuccessResponse[ReviewsResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="List reviews for current listener",
)
def reviews(
    profile: CurrentListenerProfile,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    data = list_reviews(db, profile, page=page, page_size=page_size)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/setup-progress",
    response_model=APISuccessResponse[SetupProgressResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Listener setup progress",
)
def setup_progress(profile: CurrentListenerProfile, db: DbSession):
    data = get_setup_progress(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/setup/first-session-tutorial",
    response_model=APISuccessResponse[SetupProgressResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Acknowledge first-session tutorial",
)
def first_session_tutorial(
    body: TutorialAckRequest,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    data = acknowledge_tutorial(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/me/online-status",
    response_model=APISuccessResponse[OnlineStatusResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Toggle listener online status",
)
def online_status(
    body: OnlineStatusRequest,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    data = set_online_status(db, profile, is_online=body.is_online)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/dashboard",
    response_model=APISuccessResponse[DashboardResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Listener dashboard aggregate",
)
def dashboard(profile: CurrentListenerProfile, db: DbSession):
    data = get_dashboard(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/privacy",
    response_model=APISuccessResponse[ListenerPrivacySettings],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get listener privacy settings",
)
def privacy_get(profile: CurrentListenerProfile, db: DbSession):
    data = get_privacy(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.put(
    "/me/privacy",
    response_model=APISuccessResponse[ListenerPrivacySettings],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update listener privacy settings",
)
def privacy_put(
    body: ListenerPrivacySettings,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    data = update_privacy(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/notification-preferences",
    response_model=APISuccessResponse[ListenerNotificationPreferences],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get listener notification preferences",
)
def notification_preferences_get(profile: CurrentListenerProfile, db: DbSession):
    data = get_notification_preferences(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.put(
    "/me/notification-preferences",
    response_model=APISuccessResponse[ListenerNotificationPreferences],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update listener notification preferences",
)
def notification_preferences_put(
    body: ListenerNotificationPreferences,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    data = update_notification_preferences(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/availability",
    response_model=APISuccessResponse[AvailabilityPayload],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get listener availability",
)
def availability_get(profile: CurrentListenerProfile, db: DbSession):
    from app.api.v1.listeners.service import get_availability

    data = get_availability(db, profile)
    return success_response(data.model_dump(mode="json", exclude_none=True))


@router.put(
    "/me/availability",
    response_model=APISuccessResponse[AvailabilityPayload],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Replace full availability",
)
def availability_put(
    body: AvailabilityPayload,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    from app.api.v1.listeners.service import put_availability

    data = put_availability(db, profile, body)
    return success_response(data.model_dump(mode="json", exclude_none=True))


@router.put(
    "/me/availability/days/{day}",
    response_model=APISuccessResponse[DayAvailabilityResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Update one day's availability slots",
)
def availability_day_put(
    day: DayOfWeekOut,
    body: DaySlotsUpdate,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    from app.api.v1.listeners.service import put_availability_day

    data = put_availability_day(db, profile, day, body.slots)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "",
    response_model=APISuccessResponse[ListenerListResponse],
    responses={401: {"model": APIErrorResponse}},
    summary="Discover / find listeners",
)
def listeners_list(
    current_user: CurrentVentor,
    db: DbSession,
    q: str | None = Query(None),
    topic: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    languages: str | None = Query(None),
    genders: str | None = Query(None),
    min_rating: float | None = Query(None),
    favorites: str = Query("any"),
    online_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.api.v1.listeners.discovery import list_listeners

    data = list_listeners(
        db,
        current_user,
        q=q,
        topic=topic,
        min_price=min_price,
        max_price=max_price,
        languages=languages,
        genders=genders,
        min_rating=min_rating,
        favorites=favorites,
        online_only=online_only,
        page=page,
        page_size=page_size,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/sessions",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Listener sessions list",
)
def listener_sessions(
    current_user: CurrentListener,
    db: DbSession,
    filter: str = Query("upcoming"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.api.v1.sessions.service import list_listener_sessions

    data = list_listener_sessions(
        db, current_user, filter_name=filter, page=page, page_size=page_size
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/session-stats",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Listener session stats",
)
def listener_session_stats(current_user: CurrentListener, db: DbSession):
    from app.api.v1.sessions.service import session_stats

    data = session_stats(db, current_user)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/session-requests",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Pending session requests",
)
def listener_session_requests(current_user: CurrentListener, db: DbSession):
    from app.api.v1.sessions.service import list_session_requests

    data = list_session_requests(db, current_user)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/session-requests/{request_id}/accept",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Accept a session request",
)
def listener_accept_request(
    request_id: UUID,
    current_user: CurrentListener,
    db: DbSession,
):
    from app.api.v1.sessions.service import accept_session_request

    data = accept_session_request(db, current_user, request_id)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/session-requests/{request_id}/decline",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Decline a session request",
)
def listener_decline_request(
    request_id: UUID,
    current_user: CurrentListener,
    db: DbSession,
    body: DeclineRequestBody | None = None,
):
    from app.api.v1.sessions.service import decline_session_request

    reason = body.reason if body else None
    data = decline_session_request(db, current_user, request_id, reason)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/earnings",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Earnings summary",
)
def earnings_summary(profile: CurrentListenerProfile, db: DbSession):
    from app.api.v1.listeners.earnings_service import get_earnings_summary

    data = get_earnings_summary(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/earnings/chart",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Earnings chart",
)
def earnings_chart(
    profile: CurrentListenerProfile,
    db: DbSession,
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    from datetime import date

    from app.api.v1.listeners.earnings_service import get_earnings_chart

    from_date = date.fromisoformat(from_) if from_ else None
    to_date = date.fromisoformat(to) if to else None
    data = get_earnings_chart(db, profile, from_date=from_date, to_date=to_date)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/payout-balances",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Payout balances",
)
def payout_balances(profile: CurrentListenerProfile, db: DbSession):
    from app.api.v1.listeners.earnings_service import get_payout_balances

    data = get_payout_balances(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/payout-methods",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="List payout methods",
)
def payout_methods_get(profile: CurrentListenerProfile, db: DbSession):
    from app.api.v1.listeners.earnings_service import list_payout_methods

    data = list_payout_methods(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.put(
    "/me/payout-methods",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 422: {"model": APIErrorResponse}},
    summary="Add/update payout method",
)
def payout_methods_put(
    body: UpsertPayoutMethodRequest,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    from app.api.v1.listeners.earnings_service import upsert_payout_method

    data = upsert_payout_method(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/payouts",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Payout history",
)
def payouts_list(
    profile: CurrentListenerProfile,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.api.v1.listeners.earnings_service import list_payouts

    data = list_payouts(db, profile, page=page, page_size=page_size)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/payouts",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 422: {"model": APIErrorResponse}},
    summary="Request a payout",
)
def payouts_create(
    body: CreatePayoutRequest,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    from app.api.v1.listeners.earnings_service import create_payout

    data = create_payout(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/notifications",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="List notifications",
)
def notifications_list(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.api.v1.listeners.notifications_service import list_notifications

    data = list_notifications(
        db, current_user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/notifications/read-all",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Mark all notifications read",
)
def notifications_read_all(current_user: CurrentUser, db: DbSession):
    from app.api.v1.listeners.notifications_service import mark_all_read

    data = mark_all_read(db, current_user.id)
    return success_response(data.model_dump(mode="json"))


@router.delete(
    "/me/notifications/{notification_id}",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Soft-delete a notification",
)
def notifications_delete(
    notification_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    from app.api.v1.listeners.notifications_service import delete_notification

    data = delete_notification(db, current_user.id, notification_id)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/training",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="List training modules and progress",
)
def training_get(profile: CurrentListenerProfile, db: DbSession):
    from app.api.v1.listeners.training_service import get_training

    data = get_training(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/training/{module_id}/complete",
    response_model=APISuccessResponse,
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
    summary="Mark a training module complete",
)
def training_complete(
    module_id: str,
    profile: CurrentListenerProfile,
    db: DbSession,
):
    from app.api.v1.listeners.training_service import complete_training_module

    data = complete_training_module(db, profile, module_id)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/{listener_id}",
    response_model=APISuccessResponse[ListenerPublicResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
    summary="Public listener profile (ventor view)",
)
def public_listener(
    listener_id: UUID,
    current_user: CurrentVentor,
    db: DbSession,
):
    data = get_public_listener(db, listener_id, viewer=current_user)
    return success_response(data.model_dump(mode="json"))
