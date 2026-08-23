from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.v1.catalogs.schemas import (
    CatalogBundleResponse,
    CatalogItemResponse,
    ComfortAreaResponse,
)
from app.api.v1.catalogs.service import (
    list_all_catalogs,
    list_boundaries,
    list_comfort_areas,
    list_languages,
    list_life_experiences,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/catalog", tags=["catalogs"])


@router.get(
    "",
    response_model=APISuccessResponse[CatalogBundleResponse],
    summary="All active lookup catalogs for registration and profile pickers",
)
def catalog_bundle(db: DbSession):
    return success_response(list_all_catalogs(db).model_dump(mode="json"))


@router.get(
    "/languages",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
)
def languages_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_languages(db)]
    )


@router.get(
    "/comfort-areas",
    response_model=APISuccessResponse[list[ComfortAreaResponse]],
)
def comfort_areas_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_comfort_areas(db)]
    )


@router.get(
    "/life-experiences",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
)
def life_experiences_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_life_experiences(db)]
    )


@router.get(
    "/boundaries",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
)
def boundaries_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_boundaries(db)]
    )
