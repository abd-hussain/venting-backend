from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status

from app.api.deps import (
    CurrentUser,
    CurrentVentor,
    CurrentVentorProfile,
    DbSession,
    SettingsDep,
)
from app.api.v1.sessions.schemas import CancelSessionRequest
from app.api.v1.ventors.rewards_service import RedeemRequest
from app.api.v1.ventors.schemas import (
    AchievementsResponse,
    FavoritesResponse,
    Gender,
    HomeResponse,
    MoodCheckinRequest,
    MoodCheckinResponse,
    MoodJourneyResponse,
    NotificationPreferences,
    OkResponse,
    PrivacySettings,
    VentorProfileResponse,
    VentorProfileUpdate,
    VentorRegisterCompleteRequest,
    VentorRegisterInterestsRequest,
    VentorRegisterLanguagesRequest,
    VentorRegisterProfileRequest,
    VentorRegisterProgressResponse,
)
from app.api.v1.ventors.register_service import (
    complete_register as complete_ventor_register,
    get_register_progress as get_ventor_register_progress,
    save_register_interests_step,
    save_register_languages_step,
    save_register_profile_step,
)
from app.api.v1.ventors.service import (
    add_favorite,
    create_mood_checkin,
    get_home,
    get_mood_journey,
    get_notification_preferences,
    get_privacy,
    get_ventor_profile,
    list_achievements,
    list_favorites,
    remove_favorite,
    update_notification_preferences,
    update_privacy,
    update_ventor_profile,
)
from app.core.errors import validation_error
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.get(
    "/register/progress",
    response_model=APISuccessResponse[VentorRegisterProgressResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get ventor registration progress (#8a)",
)
def register_progress(
    current_user: CurrentVentor,
    db: DbSession,
):
    data = get_ventor_register_progress(db, current_user)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/profile",
    response_model=APISuccessResponse[VentorRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save ventor registration profile step (#8b)",
)
async def register_step_profile(
    request: Request,
    current_user: CurrentVentor,
    db: DbSession,
    settings: SettingsDep,
    nickname: str | None = Form(None),
    gender: str | None = Form(None),
    avatar_preset_index: int | None = Form(None),
    avatar: UploadFile | None = File(None),
):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = VentorRegisterProfileRequest.model_validate(await request.json())
        payload = body
        avatar_upload = None
    else:
        form = await request.form()
        gender_raw = str(form.get("gender") or gender or "")
        try:
            gender_val = Gender(gender_raw)
        except ValueError as exc:
            raise validation_error("Invalid gender") from exc
        preset_raw = form.get("avatar_preset_index")
        preset = avatar_preset_index
        if preset_raw not in (None, ""):
            preset = int(preset_raw)
        avatar_field = form.get("avatar")
        avatar_upload = avatar
        if isinstance(avatar_field, UploadFile) and avatar_field.filename:
            avatar_upload = avatar_field
        payload = VentorRegisterProfileRequest(
            nickname=str(form.get("nickname") or nickname or ""),
            gender=gender_val,
            avatar_preset_index=preset,
        )

    data = await save_register_profile_step(
        db,
        current_user,
        payload=payload,
        avatar=avatar_upload,
        settings=settings,
    )
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/languages",
    response_model=APISuccessResponse[VentorRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save ventor registration languages step (#8c)",
)
async def register_step_languages(
    request: Request,
    current_user: CurrentVentor,
    db: DbSession,
):
    body = VentorRegisterLanguagesRequest.model_validate(await request.json())
    data = save_register_languages_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/register/steps/interests",
    response_model=APISuccessResponse[VentorRegisterProgressResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Save ventor registration interests step (#8d)",
)
async def register_step_interests(
    request: Request,
    current_user: CurrentVentor,
    db: DbSession,
):
    body = VentorRegisterInterestsRequest.model_validate(await request.json())
    data = save_register_interests_step(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/register/complete",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[VentorProfileResponse],
    responses={
        400: {"model": APIErrorResponse},
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
    summary="Complete ventor registration (#8e)",
)
async def register_complete(
    request: Request,
    current_user: CurrentVentor,
    db: DbSession,
):
    body = VentorRegisterCompleteRequest.model_validate(await request.json())
    data = complete_ventor_register(db, current_user, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.get(
    "/me",
    response_model=APISuccessResponse[VentorProfileResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get current ventor profile",
)
def me(
    current_user: CurrentUser,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = get_ventor_profile(db, current_user, profile)
    return success_response(data.model_dump(mode="json"))


@router.patch(
    "/me",
    response_model=APISuccessResponse[VentorProfileResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update ventor profile",
)
async def patch_me(
    request: Request,
    current_user: CurrentUser,
    profile: CurrentVentorProfile,
    db: DbSession,
    settings: SettingsDep,
):
    content_type = request.headers.get("content-type", "")
    nickname: str | None = None
    quote: str | None = None
    avatar: UploadFile | None = None

    if "application/json" in content_type:
        payload = VentorProfileUpdate.model_validate(await request.json())
        nickname = payload.nickname
        quote = payload.quote
    else:
        form = await request.form()
        raw_nickname = form.get("nickname")
        raw_quote = form.get("quote")
        nickname = str(raw_nickname) if raw_nickname is not None else None
        quote = str(raw_quote) if raw_quote is not None else None
        avatar_field = form.get("avatar")
        if isinstance(avatar_field, UploadFile):
            avatar = avatar_field

    data = await update_ventor_profile(
        db,
        current_user,
        profile,
        nickname=nickname,
        quote=quote,
        avatar=avatar,
        settings=settings,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/home",
    response_model=APISuccessResponse[HomeResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Ventor home dashboard aggregate",
)
def home(
    current_user: CurrentUser,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = get_home(db, current_user, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/mood-checkins",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[MoodCheckinResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Submit today's mood check-in",
)
def mood_checkin(
    body: MoodCheckinRequest,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = create_mood_checkin(db, profile, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.get(
    "/me/mood-journey",
    response_model=APISuccessResponse[MoodJourneyResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Mood journey chart points",
)
def mood_journey(
    profile: CurrentVentorProfile,
    db: DbSession,
    days: int = Query(7, ge=1, le=90),
):
    data = get_mood_journey(db, profile, days=days)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/favorites",
    response_model=APISuccessResponse[FavoritesResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="List favorite listeners",
)
def favorites(profile: CurrentVentorProfile, db: DbSession):
    data = list_favorites(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/favorites/{listener_id}",
    response_model=APISuccessResponse[OkResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
    summary="Favorite a listener",
)
def favorite_add(
    listener_id: UUID,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = add_favorite(db, profile, listener_id)
    return success_response(data.model_dump(mode="json"))


@router.delete(
    "/me/favorites/{listener_id}",
    response_model=APISuccessResponse[OkResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Unfavorite a listener",
)
def favorite_remove(
    listener_id: UUID,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = remove_favorite(db, profile, listener_id)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/achievements",
    response_model=APISuccessResponse[AchievementsResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="List achievements",
)
def achievements(profile: CurrentVentorProfile, db: DbSession):
    data = list_achievements(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/privacy",
    response_model=APISuccessResponse[PrivacySettings],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get privacy settings",
)
def privacy_get(profile: CurrentVentorProfile, db: DbSession):
    data = get_privacy(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.put(
    "/me/privacy",
    response_model=APISuccessResponse[PrivacySettings],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update privacy settings",
)
def privacy_put(
    body: PrivacySettings,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = update_privacy(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/notification-preferences",
    response_model=APISuccessResponse[NotificationPreferences],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Get notification preferences",
)
def notification_preferences_get(profile: CurrentVentorProfile, db: DbSession):
    data = get_notification_preferences(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.put(
    "/me/notification-preferences",
    response_model=APISuccessResponse[NotificationPreferences],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Update notification preferences",
)
def notification_preferences_put(
    body: NotificationPreferences,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    data = update_notification_preferences(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/sessions",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Ventor booked sessions",
)
def ventor_sessions(
    current_user: CurrentVentor,
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.api.v1.sessions.service import list_ventor_sessions

    data = list_ventor_sessions(
        db, current_user, status=status_filter, page=page, page_size=page_size
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/sessions/{session_id}",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Ventor session details",
)
def ventor_session_detail(
    session_id: UUID,
    current_user: CurrentVentor,
    db: DbSession,
):
    from app.api.v1.sessions.service import get_ventor_session

    data = get_ventor_session(db, current_user, session_id)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/sessions/{session_id}/cancel",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Cancel a booked session",
)
def ventor_session_cancel(
    session_id: UUID,
    current_user: CurrentVentor,
    db: DbSession,
    body: CancelSessionRequest | None = None,
):
    from app.api.v1.sessions.service import cancel_ventor_session

    data = cancel_ventor_session(db, current_user, session_id, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/rewards",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Rewards catalog and balance",
)
def rewards_get(profile: CurrentVentorProfile, db: DbSession):
    from app.api.v1.ventors.rewards_service import get_rewards

    data = get_rewards(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/rewards/redeem",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 422: {"model": APIErrorResponse}},
    summary="Redeem a reward offer",
)
def rewards_redeem(
    body: RedeemRequest,
    profile: CurrentVentorProfile,
    db: DbSession,
):
    from app.api.v1.ventors.rewards_service import redeem_offer

    data = redeem_offer(db, profile, body)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/rewards/trades",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Reward trade history",
)
def rewards_trades(profile: CurrentVentorProfile, db: DbSession):
    from app.api.v1.ventors.rewards_service import list_trades

    data = list_trades(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/invites",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Invite friends summary",
)
def invites_get(profile: CurrentVentorProfile, db: DbSession):
    from app.api.v1.ventors.rewards_service import get_invites

    data = get_invites(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/invites/refresh-code",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}},
    summary="Refresh invite code",
)
def invites_refresh(profile: CurrentVentorProfile, db: DbSession):
    from app.api.v1.ventors.rewards_service import refresh_invite_code

    data = refresh_invite_code(db, profile)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/me/notifications",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="List ventor notifications",
)
def notifications_list(
    current_user: CurrentVentor,
    db: DbSession,
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    from app.services.inbox_notifications import list_notifications

    data = list_notifications(
        db, current_user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/me/notifications/read-all",
    response_model=APISuccessResponse,
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
    summary="Mark all ventor notifications read",
)
def notifications_read_all(current_user: CurrentVentor, db: DbSession):
    from app.services.inbox_notifications import mark_all_read

    data = mark_all_read(db, current_user.id)
    return success_response(data.model_dump(mode="json"))


@router.delete(
    "/me/notifications/{notification_id}",
    response_model=APISuccessResponse,
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
    summary="Soft-delete a ventor notification",
)
def notifications_delete(
    notification_id: UUID,
    current_user: CurrentVentor,
    db: DbSession,
):
    from app.services.inbox_notifications import delete_notification

    data = delete_notification(db, current_user.id, notification_id)
    return success_response(data.model_dump(mode="json"))
