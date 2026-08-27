from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentVentor, CurrentUser, DbSession, SettingsDep
from app.api.v1.sessions.schemas import (
    BookSessionRequest,
    EndSessionRequest,
    EndSessionResponse,
    FeedbackRequest,
    InstantMatchRequest,
    InstantMatchResponse,
    JoinCallResponse,
    OkResponse,
    RatingRequest,
    RatingResponse,
    ReportRequest,
    ReportResponse,
    VentorBookedSession,
)
from app.api.v1.sessions.service import (
    book_session,
    end_session,
    instant_match,
    join_session,
    rate_session,
    report_session,
    submit_feedback,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.post(
    "/instant-match",
    response_model=APISuccessResponse[InstantMatchResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Instant match a listener",
)
def post_instant_match(
    body: InstantMatchRequest,
    current_user: CurrentVentor,
    db: DbSession,
):
    data = instant_match(db, current_user, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[VentorBookedSession],
    responses={
        401: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Book a session with a listener",
)
def post_session(
    body: BookSessionRequest,
    current_user: CurrentVentor,
    db: DbSession,
):
    data = book_session(db, current_user, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.post(
    "/{session_id}/join",
    response_model=APISuccessResponse[JoinCallResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Join a live call",
)
def post_join(
    session_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
):
    data = join_session(db, current_user, session_id, settings)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/{session_id}/end",
    response_model=APISuccessResponse[EndSessionResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="End a live session",
)
def post_end(
    session_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    body: EndSessionRequest | None = None,
):
    data = end_session(db, current_user, session_id, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/{session_id}/rating",
    response_model=APISuccessResponse[RatingResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Ventor rates a completed session",
)
def post_rating(
    session_id: UUID,
    body: RatingRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    data = rate_session(db, current_user, session_id, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/{session_id}/feedback",
    response_model=APISuccessResponse[OkResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Listener feedback after a session",
)
def post_feedback(
    session_id: UUID,
    body: FeedbackRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    data = submit_feedback(db, current_user, session_id, body)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/{session_id}/reports",
    response_model=APISuccessResponse[ReportResponse],
    responses={401: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}},
    summary="Report a session participant",
)
def post_report(
    session_id: UUID,
    body: ReportRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    data = report_session(db, current_user, session_id, body)
    return success_response(data.model_dump(mode="json"))
