from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

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
    register_ventor,
    remove_favorite,
    update_notification_preferences,
    update_privacy,
    update_ventor_profile,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[VentorProfileResponse],
    responses={
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Complete ventor profile registration",
)
async def register(
    current_user: CurrentVentor,
    db: DbSession,
    settings: SettingsDep,
    nickname: str = Form(...),
    gender: Gender = Form(...),
    language_ids: str = Form(..., description='JSON array of language ids, e.g. ["en","ar"]'),
    interest_ids: str = Form(..., description='JSON array of comfort area ids, e.g. ["stress_anxiety"]'),
    other_interest_text: str | None = Form(
        None,
        description="Required (min 2 chars) when interest_ids includes a category with allows_custom_text",
    ),
    avatar_preset_index: int | None = Form(None),
    avatar: UploadFile | None = File(None),
):
    data = await register_ventor(
        db,
        current_user,
        nickname=nickname,
        gender=gender,
        language_ids_raw=language_ids,
        interest_ids_raw=interest_ids,
        other_interest_text=other_interest_text,
        avatar=avatar,
        avatar_preset_index=avatar_preset_index,
        settings=settings,
    )
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
    current_user: CurrentUser,
    profile: CurrentVentorProfile,
    db: DbSession,
    settings: SettingsDep,
    nickname: str | None = Form(None),
    quote: str | None = Form(None),
    avatar: UploadFile | None = File(None),
):
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
