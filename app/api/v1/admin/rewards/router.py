from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.rewards.schemas import (
    PromoCodeCreateRequest,
    PromoCodeList,
    PromoCodeResponse,
    PromoCodeUpdateRequest,
    PromoRedemptionList,
    RewardOfferCreateRequest,
    RewardOfferList,
    RewardOfferResponse,
    RewardOfferUpdateRequest,
    RewardTradeList,
)
from app.api.v1.admin.rewards.service import (
    create_promo_code,
    create_reward_offer,
    list_promo_codes,
    list_promo_redemptions,
    list_reward_offers,
    list_reward_trades,
    update_promo_code,
    update_reward_offer,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(tags=["admin-rewards"])

RewardReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("rewards:write", "users:read")),
]
RewardWriter = Annotated[
    AdminPrincipal, Depends(require_permission("rewards:write"))
]
PromoReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("promo:write", "users:read")),
]
PromoWriter = Annotated[AdminPrincipal, Depends(require_permission("promo:write"))]


@router.get(
    "/reward-offers",
    response_model=APISuccessResponse[RewardOfferList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def reward_offers_list(
    db: DbSession,
    _admin: RewardReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        list_reward_offers(db, page=page, page_size=page_size).model_dump(mode="json")
    )


@router.post(
    "/reward-offers",
    response_model=APISuccessResponse[RewardOfferResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def reward_offer_create(
    body: RewardOfferCreateRequest,
    db: DbSession,
    admin: RewardWriter,
):
    return success_response(
        create_reward_offer(db, body, admin).model_dump(mode="json")
    )


@router.patch(
    "/reward-offers/{offer_id}",
    response_model=APISuccessResponse[RewardOfferResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def reward_offer_update(
    offer_id: UUID,
    body: RewardOfferUpdateRequest,
    db: DbSession,
    admin: RewardWriter,
):
    return success_response(
        update_reward_offer(db, offer_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/reward-trades",
    response_model=APISuccessResponse[RewardTradeList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def reward_trades_list(
    db: DbSession,
    _admin: RewardWriter,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        list_reward_trades(db, page=page, page_size=page_size).model_dump(mode="json")
    )


@router.get(
    "/promo-codes",
    response_model=APISuccessResponse[PromoCodeList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def promo_codes_list(
    db: DbSession,
    _admin: PromoReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        list_promo_codes(db, page=page, page_size=page_size).model_dump(mode="json")
    )


@router.post(
    "/promo-codes",
    response_model=APISuccessResponse[PromoCodeResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def promo_code_create(
    body: PromoCodeCreateRequest,
    db: DbSession,
    admin: PromoWriter,
):
    return success_response(create_promo_code(db, body, admin).model_dump(mode="json"))


@router.patch(
    "/promo-codes/{promo_id}",
    response_model=APISuccessResponse[PromoCodeResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        409: {"model": APIErrorResponse},
    },
)
def promo_code_update(
    promo_id: UUID,
    body: PromoCodeUpdateRequest,
    db: DbSession,
    admin: PromoWriter,
):
    return success_response(
        update_promo_code(db, promo_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/promo-codes/{promo_id}/redemptions",
    response_model=APISuccessResponse[PromoRedemptionList],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def promo_code_redemptions(
    promo_id: UUID,
    db: DbSession,
    _admin: PromoWriter,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return success_response(
        list_promo_redemptions(
            db, promo_id, page=page, page_size=page_size
        ).model_dump(mode="json")
    )
