from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import (
    CurrentListener,
    CurrentListenerProfile,
    CurrentUser,
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
    OnlineStatusRequest,
    OnlineStatusResponse,
    RegisterListenerResponse,
    ReviewsResponse,
    SetupProgressResponse,
    TutorialAckRequest,
    VoiceIntroResponse,
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
    register_listener,
    set_online_status,
    submit_identity_verification,
    update_listener_profile,
    update_notification_preferences,
    update_privacy,
    upload_voice_intro,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[RegisterListenerResponse],
    responses={
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Complete listener registration (steps 1–9)",
)
async def register(
    current_user: CurrentListener,
    db: DbSession,
    settings: SettingsDep,
    full_name: str = Form(...),
    phone: str | None = Form(None),
    phone_country: str | None = Form(None),
    agreed_to_terms: str = Form(...),
    date_of_birth: str | None = Form(None),
    country_iso: str | None = Form(None),
    city: str | None = Form(None),
    language_ids: str = Form(..., description='JSON array, e.g. ["en","ar"]'),
    life_experience_ids: str | None = Form(None),
    custom_experiences: str | None = Form(None),
    comfort_area_ids: str = Form(...),
    boundary_ids: str | None = Form(None),
    availability: str | None = Form(None, description="JSON availability object (#37)"),
    accept_instant_calls: str | None = Form("true"),
    session_minutes: int | None = Form(None),
    notifications_enabled: str | None = Form("true"),
    voice_intro_seconds: int | None = Form(None),
    avatar: UploadFile | None = File(None),
    identity_document_front: UploadFile | None = File(None),
    identity_document_back: UploadFile | None = File(None),
    selfie: UploadFile | None = File(None),
    voice_intro: UploadFile | None = File(None),
):
    data = await register_listener(
        db,
        current_user,
        settings=settings,
        full_name=full_name,
        phone=phone,
        phone_country=phone_country,
        agreed_to_terms=agreed_to_terms,
        date_of_birth=date_of_birth,
        country_iso=country_iso,
        city=city,
        language_ids_raw=language_ids,
        life_experience_ids_raw=life_experience_ids,
        custom_experiences_raw=custom_experiences,
        comfort_area_ids_raw=comfort_area_ids,
        boundary_ids_raw=boundary_ids,
        availability_raw=availability,
        accept_instant_calls=accept_instant_calls,
        session_minutes=session_minutes,
        notifications_enabled=notifications_enabled,
        avatar=avatar,
        identity_document_front=identity_document_front,
        identity_document_back=identity_document_back,
        selfie=selfie,
        voice_intro=voice_intro,
        voice_intro_seconds=voice_intro_seconds,
    )
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.post(
    "/me/identity-verification",
    response_model=APISuccessResponse[IdentityVerificationResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Submit or re-submit identity verification",
)
async def identity_verification(
    profile: CurrentListenerProfile,
    db: DbSession,
    settings: SettingsDep,
    document_front: UploadFile = File(...),
    selfie: UploadFile = File(...),
    document_back: UploadFile | None = File(None),
):
    data = await submit_identity_verification(
        db,
        profile,
        settings=settings,
        document_front=document_front,
        document_back=document_back,
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
    duration_seconds: int | None = Form(None),
):
    data = await upload_voice_intro(
        db,
        profile,
        settings=settings,
        audio=audio,
        duration_seconds=duration_seconds,
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
def setup_progress(profile: CurrentListenerProfile):
    data = get_setup_progress(profile)
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
    return success_response(data.model_dump(mode="json"))


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
    return success_response(data.model_dump(mode="json"))


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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
def listener_session_stats(current_user: CurrentUser, db: DbSession):
    from app.api.v1.sessions.service import session_stats

    data = session_stats(db, current_user)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/session-requests",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Pending session requests",
)
def listener_session_requests(current_user: CurrentUser, db: DbSession):
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
    db: DbSession,
):
    data = get_public_listener(db, listener_id, viewer=current_user)
    return success_response(data.model_dump(mode="json"))
