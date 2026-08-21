from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.v1.admin.cms.schemas import CmsBannerResponse, CmsPageResponse
from app.api.v1.admin.cms.service import public_banners, public_page
from app.core.responses import success_response
from app.models.enums import BannerPlacement
from app.schemas.envelope import APISuccessResponse

public_router = APIRouter(tags=["cms"])


@public_router.get(
    "/pages/{slug}", response_model=APISuccessResponse[CmsPageResponse]
)
def page_by_slug(slug: str, db: DbSession, locale: str = "en"):
    return success_response(public_page(db, slug, locale).model_dump(mode="json"))


@public_router.get(
    "/banners", response_model=APISuccessResponse[list[CmsBannerResponse]]
)
def active_banners(db: DbSession, placement: BannerPlacement | None = None):
    return success_response(
        [
            row.model_dump(mode="json")
            for row in public_banners(db, placement=placement)
        ]
    )
