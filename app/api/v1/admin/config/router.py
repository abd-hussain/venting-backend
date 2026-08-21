from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.config.schemas import (
    ConfigResponse,
    ConfigValueRequest,
    FeatureFlagResponse,
    FeatureFlagUpsertRequest,
)
from app.api.v1.admin.config.service import (
    get_earnings_tiers,
    list_config,
    list_feature_flags,
    update_earnings_tiers,
    upsert_config,
    upsert_feature_flag,
)
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(tags=["admin-config"])
ConfigReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("config:write", "analytics:read")),
]
ConfigWriter = Annotated[
    AdminPrincipal, Depends(require_permission("config:write"))
]
AnalyticsReader = Annotated[
    AdminPrincipal, Depends(require_permission("analytics:read"))
]


@router.get(
    "/feature-flags", response_model=APISuccessResponse[list[FeatureFlagResponse]]
)
def feature_flags(db: DbSession, _admin: ConfigReader):
    return success_response(
        [row.model_dump(mode="json") for row in list_feature_flags(db)]
    )


@router.put(
    "/feature-flags/{key}", response_model=APISuccessResponse[FeatureFlagResponse]
)
def feature_flag_upsert(
    key: str, body: FeatureFlagUpsertRequest, db: DbSession, admin: ConfigWriter
):
    return success_response(
        upsert_feature_flag(db, key, body, admin).model_dump(mode="json")
    )


@router.get("/config", response_model=APISuccessResponse[list[ConfigResponse]])
def config_list(db: DbSession, _admin: ConfigReader):
    return success_response([row.model_dump(mode="json") for row in list_config(db)])


@router.get(
    "/config/earnings-tiers", response_model=APISuccessResponse[dict[str, Any]]
)
def earnings_tiers(db: DbSession, _admin: AnalyticsReader):
    return success_response(get_earnings_tiers(db))


@router.put(
    "/config/earnings-tiers", response_model=APISuccessResponse[dict[str, Any]]
)
def earnings_tiers_update(
    body: dict[str, Any], db: DbSession, admin: ConfigWriter
):
    return success_response(update_earnings_tiers(db, body, admin))


@router.put("/config/{key}", response_model=APISuccessResponse[ConfigResponse])
def config_upsert(
    key: str, body: ConfigValueRequest, db: DbSession, admin: ConfigWriter
):
    return success_response(
        upsert_config(db, key, body.value, admin).model_dump(mode="json")
    )
