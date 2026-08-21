"""Admin report triage and moderation routes (A34–A40)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.reports.schemas import (
    FeedbackList,
    ModerationActionItem,
    ModerationActionList,
    ModerationCreateRequest,
    RatingList,
    ReportItem,
    ReportList,
    ReportStatus,
    ReportUpdateRequest,
)
from app.api.v1.admin.reports.service import (
    create_moderation_action,
    get_report,
    list_feedback,
    list_low_ratings,
    list_moderation_actions,
    list_reports,
    update_report,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(tags=["admin-reports"])

ReportsAdmin = Annotated[
    AdminPrincipal, Depends(require_permission("reports:triage"))
]
UsersWriteAdmin = Annotated[
    AdminPrincipal, Depends(require_permission("users:write"))
]
ReportsOrUsersReadAdmin = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("reports:triage", "users:read")),
]


@router.get(
    "/reports",
    response_model=APISuccessResponse[ReportList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_reports(
    db: DbSession,
    _admin: ReportsAdmin,
    status_filter: Annotated[ReportStatus | None, Query(alias="status")] = None,
    page: int = 1,
):
    data = list_reports(db, status=status_filter, page=page)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/reports/{report_id}",
    response_model=APISuccessResponse[ReportItem],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def get_report_detail(report_id: UUID, db: DbSession, _admin: ReportsAdmin):
    return success_response(get_report(db, report_id).model_dump(mode="json"))


@router.patch(
    "/reports/{report_id}",
    response_model=APISuccessResponse[ReportItem],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def patch_report(
    report_id: UUID,
    body: ReportUpdateRequest,
    db: DbSession,
    admin: ReportsAdmin,
):
    return success_response(
        update_report(db, admin, report_id, body).model_dump(mode="json")
    )


@router.post(
    "/moderation",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[ModerationActionItem],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def post_moderation(
    body: ModerationCreateRequest,
    db: DbSession,
    admin: UsersWriteAdmin,
):
    data = create_moderation_action(db, admin, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.get(
    "/moderation",
    response_model=APISuccessResponse[ModerationActionList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_moderation(
    user_id: UUID,
    db: DbSession,
    _admin: ReportsOrUsersReadAdmin,
    page: int = 1,
):
    data = list_moderation_actions(db, user_id=user_id, page=page)
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/ratings",
    response_model=APISuccessResponse[RatingList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_ratings(db: DbSession, _admin: ReportsAdmin, page: int = 1):
    return success_response(list_low_ratings(db, page=page).model_dump(mode="json"))


@router.get(
    "/feedback",
    response_model=APISuccessResponse[FeedbackList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_feedback(db: DbSession, _admin: ReportsAdmin, page: int = 1):
    return success_response(list_feedback(db, page=page).model_dump(mode="json"))
