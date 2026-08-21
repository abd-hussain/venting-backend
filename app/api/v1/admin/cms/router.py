from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.cms.schemas import (
    CmsBannerCreate,
    CmsBannerResponse,
    CmsBannerUpdate,
    CmsPageCreate,
    CmsPageResponse,
    CmsPageUpdate,
)
from app.api.v1.admin.cms.service import (
    create_banner,
    create_page,
    deactivate_banner,
    list_banners,
    list_pages,
    publish_page,
    update_banner,
    update_page,
)
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/cms", tags=["admin-cms"])
CmsReader = Annotated[
    AdminPrincipal, Depends(require_any_permission("cms:write", "users:read"))
]
CmsWriter = Annotated[AdminPrincipal, Depends(require_permission("cms:write"))]


@router.get("/pages", response_model=APISuccessResponse[list[CmsPageResponse]])
def pages(db: DbSession, _admin: CmsReader):
    return success_response([row.model_dump(mode="json") for row in list_pages(db)])


@router.post("/pages", response_model=APISuccessResponse[CmsPageResponse])
def page_create(body: CmsPageCreate, db: DbSession, admin: CmsWriter):
    return success_response(create_page(db, body, admin).model_dump(mode="json"))


@router.patch(
    "/pages/{page_id}", response_model=APISuccessResponse[CmsPageResponse]
)
def page_update(
    page_id: UUID, body: CmsPageUpdate, db: DbSession, admin: CmsWriter
):
    return success_response(
        update_page(db, page_id, body, admin).model_dump(mode="json")
    )


@router.post(
    "/pages/{page_id}/publish", response_model=APISuccessResponse[CmsPageResponse]
)
def page_publish(page_id: UUID, db: DbSession, admin: CmsWriter):
    return success_response(publish_page(db, page_id, admin).model_dump(mode="json"))


@router.get("/banners", response_model=APISuccessResponse[list[CmsBannerResponse]])
def banners(db: DbSession, _admin: CmsReader):
    return success_response([row.model_dump(mode="json") for row in list_banners(db)])


@router.post("/banners", response_model=APISuccessResponse[CmsBannerResponse])
def banner_create(body: CmsBannerCreate, db: DbSession, _admin: CmsWriter):
    return success_response(create_banner(db, body).model_dump(mode="json"))


@router.patch(
    "/banners/{banner_id}", response_model=APISuccessResponse[CmsBannerResponse]
)
def banner_update(
    banner_id: UUID, body: CmsBannerUpdate, db: DbSession, _admin: CmsWriter
):
    return success_response(
        update_banner(db, banner_id, body).model_dump(mode="json")
    )


@router.delete(
    "/banners/{banner_id}", response_model=APISuccessResponse[CmsBannerResponse]
)
def banner_delete(banner_id: UUID, db: DbSession, _admin: CmsWriter):
    return success_response(deactivate_banner(db, banner_id).model_dump(mode="json"))
