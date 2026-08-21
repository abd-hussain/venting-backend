from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.payouts.schemas import (
    AdjustWalletRequest,
    ApprovePayoutRequest,
    EarningsTiersResponse,
    PayoutDetailResponse,
    PayoutListResponse,
    PayoutResponse,
    RejectPayoutRequest,
    WalletAdjustmentResponse,
    WalletResponse,
)
from app.api.v1.admin.payouts.service import (
    adjust_wallet,
    approve_payout,
    get_earnings_tiers,
    get_payout,
    get_wallet,
    list_payouts,
    reject_payout,
)
from app.core.responses import success_response
from app.models.enums import PayoutStatus
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(tags=["admin-payouts"])

PayoutApprover = Annotated[
    AdminPrincipal, Depends(require_permission("payouts:approve"))
]
WalletReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("wallet:adjust", "payouts:approve")),
]
WalletAdjuster = Annotated[
    AdminPrincipal, Depends(require_permission("wallet:adjust"))
]
TiersReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("analytics:read", "payouts:approve")),
]


@router.get(
    "/payouts",
    response_model=APISuccessResponse[PayoutListResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def payouts_list(
    db: DbSession,
    _admin: PayoutApprover,
    status: PayoutStatus = PayoutStatus.pending,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        list_payouts(
            db,
            status=status,
            page=page,
            page_size=page_size,
        ).model_dump(mode="json")
    )


@router.get(
    "/payouts/{payout_id}",
    response_model=APISuccessResponse[PayoutDetailResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def payout_detail(payout_id: UUID, db: DbSession, _admin: PayoutApprover):
    return success_response(get_payout(db, payout_id).model_dump(mode="json"))


@router.post(
    "/payouts/{payout_id}/approve",
    response_model=APISuccessResponse[PayoutResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def payout_approve(
    payout_id: UUID,
    body: ApprovePayoutRequest,
    db: DbSession,
    admin: PayoutApprover,
):
    return success_response(
        approve_payout(db, payout_id, body, admin).model_dump(mode="json")
    )


@router.post(
    "/payouts/{payout_id}/reject",
    response_model=APISuccessResponse[PayoutResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def payout_reject(
    payout_id: UUID,
    body: RejectPayoutRequest,
    db: DbSession,
    admin: PayoutApprover,
):
    return success_response(
        reject_payout(db, payout_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/listeners/{listener_id}/wallet",
    response_model=APISuccessResponse[WalletResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def listener_wallet(
    listener_id: UUID,
    db: DbSession,
    _admin: WalletReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        get_wallet(db, listener_id, page=page, page_size=page_size).model_dump(
            mode="json"
        )
    )


@router.post(
    "/listeners/{listener_id}/wallet/adjust",
    response_model=APISuccessResponse[WalletAdjustmentResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
)
def listener_wallet_adjust(
    listener_id: UUID,
    body: AdjustWalletRequest,
    db: DbSession,
    admin: WalletAdjuster,
):
    return success_response(
        adjust_wallet(db, listener_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/earnings/tiers",
    response_model=APISuccessResponse[EarningsTiersResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def earnings_tiers(db: DbSession, _admin: TiersReader):
    return success_response(get_earnings_tiers(db).model_dump(mode="json"))
