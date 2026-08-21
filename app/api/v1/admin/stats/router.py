"""Admin dashboard statistics routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.api.v1.admin.deps import AdminPrincipal, require_permission
from app.api.v1.admin.stats.schemas import (
    Granularity,
    ListenerStats,
    OverviewStats,
    RevenueStats,
    SessionsStats,
    UsersStats,
    WellnessStats,
)
from app.api.v1.admin.stats.service import (
    get_listener_stats,
    get_overview,
    get_revenue_stats,
    get_sessions_stats,
    get_users_stats,
    get_wellness_stats,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/stats", tags=["admin-stats"])
AnalyticsAdmin = Annotated[
    AdminPrincipal,
    Depends(require_permission("analytics:read")),
]


@router.get("/overview", response_model=APISuccessResponse[OverviewStats])
def overview(db: DbSession, admin: AnalyticsAdmin):
    return success_response(get_overview(db).model_dump(mode="json"))


@router.get("/users", response_model=APISuccessResponse[UsersStats])
def users(
    db: DbSession,
    admin: AnalyticsAdmin,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    granularity: Granularity = "day",
):
    data = get_users_stats(
        db,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
    )
    return success_response(data.model_dump(mode="json"))


@router.get("/sessions", response_model=APISuccessResponse[SessionsStats])
def sessions(
    db: DbSession,
    admin: AnalyticsAdmin,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    granularity: Granularity = "day",
):
    data = get_sessions_stats(
        db,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
    )
    return success_response(data.model_dump(mode="json"))


@router.get("/revenue", response_model=APISuccessResponse[RevenueStats])
def revenue(
    db: DbSession,
    admin: AnalyticsAdmin,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    granularity: Granularity = "day",
):
    data = get_revenue_stats(
        db,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
    )
    return success_response(data.model_dump(mode="json"))


@router.get("/listeners", response_model=APISuccessResponse[ListenerStats])
def listeners(db: DbSession, admin: AnalyticsAdmin):
    return success_response(get_listener_stats(db).model_dump(mode="json"))


@router.get("/wellness", response_model=APISuccessResponse[WellnessStats])
def wellness(
    db: DbSession,
    admin: AnalyticsAdmin,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
):
    data = get_wellness_stats(db, from_date=from_date, to_date=to_date)
    return success_response(data.model_dump(mode="json"))
