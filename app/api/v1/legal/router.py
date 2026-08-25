from fastapi import APIRouter, Header, Query

from app.api.deps import DbSession
from app.api.v1.legal.schemas import LegalLinksResponse
from app.api.v1.legal.service import get_legal_links
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get(
    "/links",
    response_model=APISuccessResponse[LegalLinksResponse],
    responses={400: {"model": APIErrorResponse}, 503: {"model": APIErrorResponse}},
    summary="Locale-specific Terms and Privacy WebView links",
)
def legal_links(
    db: DbSession,
    locale: str | None = Query(
        default=None,
        description="en | ar — defaults from Accept-Language / skel-accept-language",
    ),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    skel_accept_language: str | None = Header(
        default=None, alias="skel-accept-language"
    ),
):
    if locale is not None:
        payload = get_legal_links(db, locale=locale, locale_from_query=True)
    else:
        payload = get_legal_links(
            db,
            locale=skel_accept_language or accept_language,
            locale_from_query=False,
        )
    response = success_response(payload.model_dump(mode="json"))
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
