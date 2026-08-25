from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.v1.catalogs.schemas import (
    CatalogBundleResponse,
    CatalogItemResponse,
    CategoriesListResponse,
    ComfortAreaResponse,
    LanguagesListResponse,
)
from app.api.v1.catalogs.service import (
    list_all_catalogs,
    list_boundaries,
    list_categories,
    list_comfort_areas,
    list_languages,
    list_life_experiences,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/catalog", tags=["catalogs"])


@router.get(
    "",
    response_model=APISuccessResponse[CatalogBundleResponse],
    summary="All active lookup catalogs for registration and profile pickers",
)
def catalog_bundle(db: DbSession):
    return success_response(list_all_catalogs(db).model_dump(mode="json"))


@router.get(
    "/categories",
    response_model=APISuccessResponse[CategoriesListResponse],
    responses={400: {"model": APIErrorResponse}},
    summary="Interest / comfort categories for ventor or listener pickers",
)
def categories_list(
    db: DbSession,
    audience: str = Query(default="all", description="ventor | listener | all"),
):
    items = list_categories(db, audience=audience)
    return success_response(
        CategoriesListResponse(items=items).model_dump(mode="json")
    )


@router.get(
    "/languages",
    response_model=APISuccessResponse[LanguagesListResponse],
    summary="Speaking-language lookup (listener languages + session speech_language)",
)
def languages_list(db: DbSession):
    items = list_languages(db)
    return success_response(
        LanguagesListResponse(items=items).model_dump(mode="json")
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
