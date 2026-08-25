from fastapi import APIRouter, Header, Query

from app.api.deps import DbSession
from app.api.v1.help.schemas import HelpLinksResponse
from app.api.v1.help.service import get_help_links
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/help", tags=["help"])


@router.get(
    "/links",
    response_model=APISuccessResponse[HelpLinksResponse],
    responses={400: {"model": APIErrorResponse}, 503: {"model": APIErrorResponse}},
    summary="Locale-specific Help Center topic WebView links",
)
def help_links(
    db: DbSession,
    locale: str | None = Query(
        default=None,
        description="en | ar — defaults from Accept-Language / skel-accept-language",
    ),
    topic: str | None = Query(
        default=None,
        description="Optional topic key filter (e.g. getting_started, faqs)",
    ),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    skel_accept_language: str | None = Header(
        default=None, alias="skel-accept-language"
    ),
):
    if locale is not None:
        payload = get_help_links(
            db, locale=locale, locale_from_query=True, topic=topic
        )
    else:
        payload = get_help_links(
            db,
            locale=skel_accept_language or accept_language,
            locale_from_query=False,
            topic=topic,
        )
    response = success_response(payload.model_dump(mode="json"))
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
