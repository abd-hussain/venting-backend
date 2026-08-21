"""Admin session management routes."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.api.v1.admin.deps import AdminPrincipal, require_permission
from app.api.v1.admin.sessions.schemas import (
    CancelSessionRequest,
    RefundSessionRequest,
    SessionActionResponse,
    SessionDetail,
    SessionList,
    SessionRequestList,
    SessionTimeline,
)
from app.api.v1.admin.sessions.service import (
    cancel_session,
    get_session,
    get_session_timeline,
    list_session_requests,
    list_sessions,
    refund_session,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(tags=["admin-sessions"])
UsersReadAdmin = Annotated[
    AdminPrincipal,
    Depends(require_permission("users:read")),
]
SessionsWriteAdmin = Annotated[
    AdminPrincipal,
    Depends(require_permission("sessions:write")),
]


@router.get("/sessions", response_model=APISuccessResponse[SessionList])
def sessions(
    db: DbSession,
    admin: UsersReadAdmin,
    status: str | None = None,
    ventor_id: UUID | None = None,
    listener_id: UUID | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    data = list_sessions(
        db,
        status=status,
        ventor_id=ventor_id,
        listener_id=listener_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return success_response(data.model_dump(mode="json"))


@router.get("/sessions/{session_id}", response_model=APISuccessResponse[SessionDetail])
def session_detail(
    session_id: UUID,
    db: DbSession,
    admin: UsersReadAdmin,
):
    return success_response(get_session(db, session_id).model_dump(mode="json"))


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=APISuccessResponse[SessionActionResponse],
)
def session_cancel(
    session_id: UUID,
    db: DbSession,
    admin: SessionsWriteAdmin,
    body: CancelSessionRequest | None = None,
):
    data = cancel_session(
        db,
        admin,
        session_id,
        reason=body.reason if body else None,
    )
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/sessions/{session_id}/refund",
    response_model=APISuccessResponse[SessionActionResponse],
)
def session_refund(
    session_id: UUID,
    db: DbSession,
    admin: SessionsWriteAdmin,
    body: RefundSessionRequest | None = None,
):
    data = refund_session(
        db,
        admin,
        session_id,
        amount=body.amount if body else None,
    )
    return success_response(data.model_dump(mode="json"))


@router.get("/session-requests", response_model=APISuccessResponse[SessionRequestList])
def session_requests(
    db: DbSession,
    admin: UsersReadAdmin,
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    data = list_session_requests(
        db,
        status=status,
        page=page,
        page_size=page_size,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/sessions/{session_id}/timeline",
    response_model=APISuccessResponse[SessionTimeline],
)
def session_timeline(
    session_id: UUID,
    db: DbSession,
    admin: UsersReadAdmin,
):
    return success_response(
        get_session_timeline(db, session_id).model_dump(mode="json")
    )
