"""Admin analytics routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, SettingsDep
from app.api.v1.admin.analytics.schemas import (
    AnalyticsFunnels,
    AnalyticsSummary,
    GaEmbedConfig,
)
from app.api.v1.admin.analytics.service import (
    get_funnels,
    get_ga_embed_config,
    get_summary,
)
from app.api.v1.admin.deps import AdminPrincipal, require_permission
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])
AnalyticsAdmin = Annotated[
    AdminPrincipal,
    Depends(require_permission("analytics:read")),
]


@router.get("/summary", response_model=APISuccessResponse[AnalyticsSummary])
def summary(db: DbSession, admin: AnalyticsAdmin):
    return success_response(get_summary(db).model_dump(mode="json"))


@router.get("/funnels", response_model=APISuccessResponse[AnalyticsFunnels])
def funnels(db: DbSession, admin: AnalyticsAdmin):
    return success_response(get_funnels(db).model_dump(mode="json"))


@router.get("/ga-embed-config", response_model=APISuccessResponse[GaEmbedConfig])
def ga_embed_config(
    db: DbSession,
    settings: SettingsDep,
    admin: AnalyticsAdmin,
):
    return success_response(
        get_ga_embed_config(db, settings).model_dump(mode="json")
    )
