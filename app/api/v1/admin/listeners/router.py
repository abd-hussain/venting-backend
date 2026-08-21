"""Admin listener review routes — A22–A27."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.listeners import service
from app.api.v1.admin.listeners.schemas import (
    IdentityDecisionRequest,
    IdentityVerificationDetail,
    ListenerQueueItem,
    ListenerReviewDetail,
    ListenerReviewResponse,
    RejectListenerRequest,
)
from app.core.pagination import Paginated
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(tags=["admin-listener-reviews"])


@router.get(
    "/listeners/queue",
    response_model=APISuccessResponse[Paginated[ListenerQueueItem]],
)
def review_queue(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    _: AdminPrincipal = Depends(require_permission("listeners:approve")),
):
    return success_response(
        jsonable_encoder(
            service.list_review_queue(db, page=page, page_size=page_size)
        )
    )


@router.get(
    "/listeners/{listener_id}",
    response_model=APISuccessResponse[ListenerReviewDetail],
)
def listener_review(
    listener_id: UUID,
    db: DbSession,
    _: AdminPrincipal = Depends(
        require_any_permission("listeners:approve", "users:read")
    ),
):
    return success_response(
        jsonable_encoder(service.get_listener_review(db, listener_id))
    )


@router.get(
    "/listeners/{listener_id}/identity",
    response_model=APISuccessResponse[IdentityVerificationDetail],
)
def listener_identity(
    listener_id: UUID,
    db: DbSession,
    _: AdminPrincipal = Depends(require_permission("identity:read")),
):
    return success_response(
        jsonable_encoder(service.get_latest_identity(db, listener_id))
    )


@router.post(
    "/listeners/{listener_id}/approve",
    response_model=APISuccessResponse[ListenerReviewResponse],
)
def approve(
    listener_id: UUID,
    db: DbSession,
    admin: AdminPrincipal = Depends(require_permission("listeners:approve")),
):
    return success_response(
        jsonable_encoder(service.approve_listener(db, listener_id, admin))
    )


@router.post(
    "/listeners/{listener_id}/reject",
    response_model=APISuccessResponse[ListenerReviewResponse],
)
def reject(
    listener_id: UUID,
    body: RejectListenerRequest,
    db: DbSession,
    admin: AdminPrincipal = Depends(require_permission("listeners:approve")),
):
    return success_response(
        jsonable_encoder(service.reject_listener(db, listener_id, body, admin))
    )


@router.post(
    "/identity/{verification_id}/decide",
    response_model=APISuccessResponse[IdentityVerificationDetail],
)
def decide_identity(
    verification_id: UUID,
    body: IdentityDecisionRequest,
    db: DbSession,
    admin: AdminPrincipal = Depends(require_permission("listeners:approve")),
):
    return success_response(
        jsonable_encoder(
            service.decide_identity(db, verification_id, body, admin)
        )
    )
