from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.api.v1.promo.service import ValidatePromoRequest, ValidatePromoResponse, validate_promo
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.post(
    "/validate",
    response_model=APISuccessResponse[ValidatePromoResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Validate a promo code at checkout",
)
def promo_validate(
    body: ValidatePromoRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    data = validate_promo(db, current_user, body)
    return success_response(data.model_dump(mode="json"))
