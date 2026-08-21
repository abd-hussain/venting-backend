"""Server-side analytics helpers for the admin portal."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.analytics.schemas import (
    AnalyticsFunnels,
    AnalyticsSummary,
    FunnelStage,
    GaEmbedConfig,
)
from app.api.v1.admin.stats.service import get_overview
from app.core.config import Settings
from app.models.admin import AppConfigKv
from app.models.auth import User
from app.models.enums import ProfileStatus, SessionStatus, UserRole
from app.models.profiles import ListenerProfile
from app.models.sessions import Session as VentingSession


def get_summary(db: Session) -> AnalyticsSummary:
    overview = get_overview(db)
    return AnalyticsSummary(**overview.model_dump())


def _conversion(current: int, previous: int) -> float:
    if previous == 0:
        return 0.0
    return round(current / previous * 100, 2)


def get_funnels(db: Session) -> AnalyticsFunnels:
    registered = (
        db.query(func.count(User.id))
        .filter(
            User.role == UserRole.listener,
            User.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    approved = (
        db.query(func.count(ListenerProfile.user_id))
        .filter(ListenerProfile.profile_status == ProfileStatus.approved)
        .scalar()
        or 0
    )
    first_session = (
        db.query(func.count(func.distinct(VentingSession.listener_id)))
        .filter(VentingSession.status == SessionStatus.completed)
        .scalar()
        or 0
    )
    registered = int(registered)
    approved = int(approved)
    first_session = int(first_session)
    return AnalyticsFunnels(
        stages=[
            FunnelStage(key="registered_listeners", count=registered),
            FunnelStage(
                key="approved_listeners",
                count=approved,
                conversion_from_previous=_conversion(approved, registered),
            ),
            FunnelStage(
                key="first_session",
                count=first_session,
                conversion_from_previous=_conversion(first_session, approved),
            ),
        ]
    )


def get_ga_embed_config(db: Session, settings: Settings) -> GaEmbedConfig:
    measurement_id = settings.ga4_measurement_id.strip()
    if not measurement_id:
        config = (
            db.query(AppConfigKv)
            .filter(AppConfigKv.key == "ga4_measurement_id")
            .one_or_none()
        )
        if config is not None:
            if isinstance(config.value, str):
                measurement_id = config.value
            elif isinstance(config.value, dict):
                raw = config.value.get("measurement_id", config.value.get("value", ""))
                measurement_id = str(raw) if raw is not None else ""
    return GaEmbedConfig(measurement_id=measurement_id)
