from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.catalogs.schemas import (
    CatalogItemResponse,
    CatalogUpsertRequest,
    ComfortAreaResponse,
    ComfortAreaUpsertRequest,
)
from app.api.v1.admin.catalogs.service import (
    list_boundaries,
    list_comfort_areas,
    list_languages,
    list_life_experiences,
    upsert_boundary,
    upsert_comfort_area,
    upsert_language,
    upsert_life_experience,
)
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/catalog", tags=["admin-catalogs"])

CatalogReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("users:read", "catalogs:write")),
]
CatalogWriter = Annotated[
    AdminPrincipal, Depends(require_permission("catalogs:write"))
]


@router.get(
    "/languages",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def languages_list(db: DbSession, _admin: CatalogReader):
    return success_response(
        [item.model_dump(mode="json") for item in list_languages(db)]
    )


@router.put(
    "/languages/{item_id}",
    response_model=APISuccessResponse[CatalogItemResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def language_upsert(
    item_id: str,
    body: CatalogUpsertRequest,
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        upsert_language(db, item_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/comfort-areas",
    response_model=APISuccessResponse[list[ComfortAreaResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def comfort_areas_list(db: DbSession, _admin: CatalogReader):
    return success_response(
        [item.model_dump(mode="json") for item in list_comfort_areas(db)]
    )


@router.put(
    "/comfort-areas/{item_id}",
    response_model=APISuccessResponse[ComfortAreaResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def comfort_area_upsert(
    item_id: str,
    body: ComfortAreaUpsertRequest,
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        upsert_comfort_area(db, item_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/life-experiences",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def life_experiences_list(db: DbSession, _admin: CatalogReader):
    return success_response(
        [item.model_dump(mode="json") for item in list_life_experiences(db)]
    )


@router.put(
    "/life-experiences/{item_id}",
    response_model=APISuccessResponse[CatalogItemResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def life_experience_upsert(
    item_id: str,
    body: CatalogUpsertRequest,
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        upsert_life_experience(db, item_id, body, admin).model_dump(mode="json")
    )


@router.get(
    "/boundaries",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def boundaries_list(db: DbSession, _admin: CatalogReader):
    return success_response(
        [item.model_dump(mode="json") for item in list_boundaries(db)]
    )


@router.put(
    "/boundaries/{item_id}",
    response_model=APISuccessResponse[CatalogItemResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def boundary_upsert(
    item_id: str,
    body: CatalogUpsertRequest,
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        upsert_boundary(db, item_id, body, admin).model_dump(mode="json")
    )
