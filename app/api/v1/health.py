from fastapi import APIRouter

from app.core.errors import invalid_credentials
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.get(
    "/",
    response_model=APISuccessResponse[dict],
    responses={400: {"model": APIErrorResponse}},
    include_in_schema=False,
)
def read_root():
    """Platform / local probe — kept out of OpenAPI docs."""
    return success_response({"message": "Venting Backend Hello, World!"})


@router.get(
    "/demo/error",
    response_model=APIErrorResponse,
    include_in_schema=False,
)
def demo_error():
    """Example endpoint that returns the standard MainAPIException shape."""
    raise invalid_credentials()
