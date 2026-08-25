from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.v1.catalogs.schemas import (
    CatalogItemResponse,
    CategoriesListResponse,
    LanguagesListResponse,
)
from app.api.v1.catalogs.service import (
    list_boundaries,
    list_categories,
    list_languages,
    list_life_experiences,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/catalog", tags=["catalogs"])


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
    responses={400: {"model": APIErrorResponse}},
    summary="Speaking-language lookup (ventor + listener + speech_language)",
)
def languages_list(
    db: DbSession,
    q: str | None = Query(default=None, description="Search name_en / name_native / name_ar"),
):
    items = list_languages(db, q=q)
    return success_response(
        LanguagesListResponse(items=items).model_dump(mode="json")
    )


@router.get(
    "/life-experiences",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
    summary="Listener life-experience tags (focused catalog)",
)
def life_experiences_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_life_experiences(db)]
    )


@router.get(
    "/boundaries",
    response_model=APISuccessResponse[list[CatalogItemResponse]],
    summary="Listener boundary tags (focused catalog)",
)
def boundaries_list(db: DbSession):
    return success_response(
        [item.model_dump(mode="json") for item in list_boundaries(db)]
    )
