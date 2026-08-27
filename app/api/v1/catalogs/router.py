from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.v1.catalogs.schemas import (
    BoundariesListResponse,
    CategoriesListResponse,
    LanguagesListResponse,
    LifeExperiencesListResponse,
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
def categories_list(db: DbSession):
    items = list_categories(db)
    response = success_response(
        CategoriesListResponse(items=items).model_dump(mode="json")
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


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
    response = success_response(
        LanguagesListResponse(items=items).model_dump(mode="json")
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@router.get(
    "/life-experiences",
    response_model=APISuccessResponse[LifeExperiencesListResponse],
    summary="Listener life-experience tags (focused catalog)",
)
def life_experiences_list(db: DbSession):
    items = list_life_experiences(db)
    response = success_response(
        LifeExperiencesListResponse(items=items).model_dump(mode="json")
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@router.get(
    "/boundaries",
    response_model=APISuccessResponse[BoundariesListResponse],
    summary="Listener boundary tags (focused catalog)",
)
def boundaries_list(db: DbSession):
    items = list_boundaries(db)
    response = success_response(
        BoundariesListResponse(items=items).model_dump(mode="json")
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
