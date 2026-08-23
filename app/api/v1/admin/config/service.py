from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.config.schemas import (
    ConfigResponse,
    FeatureFlagResponse,
    FeatureFlagUpsertRequest,
)
from app.models.admin import AppConfigKv, AppFeatureFlag
from app.services.earnings_tiers import (
    EARNINGS_TIERS_KEY,
    get_stored_tiers,
    refresh_listener_rates,
    tiers_with_listener_counts,
    validate_tier_update,
)


def _flag(row: AppFeatureFlag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        key=row.key,
        description=row.description,
        enabled=row.enabled,
        rollout_percent=row.rollout_percent,
        audience=row.audience,
        updated_at=row.updated_at,
    )


def _config(row: AppConfigKv) -> ConfigResponse:
    return ConfigResponse(key=row.key, value=row.value, updated_at=row.updated_at)


def list_feature_flags(db: Session) -> list[FeatureFlagResponse]:
    return [_flag(row) for row in db.query(AppFeatureFlag).order_by(AppFeatureFlag.key)]


def upsert_feature_flag(
    db: Session, key: str, payload: FeatureFlagUpsertRequest, admin: AdminPrincipal
) -> FeatureFlagResponse:
    row = db.get(AppFeatureFlag, key)
    before = None
    if row is None:
        row = AppFeatureFlag(key=key)
        db.add(row)
    else:
        before = {
            "description": row.description,
            "enabled": row.enabled,
            "rollout_percent": row.rollout_percent,
            "audience": row.audience,
        }
    changes = payload.model_dump()
    for field, value in changes.items():
        setattr(row, field, value)
    row.updated_by = admin.id
    write_audit(
        db,
        admin_user_id=admin.id,
        action="feature_flag.upsert",
        entity_type="feature_flag",
        entity_id=key,
        before=before,
        after=changes,
    )
    db.commit()
    db.refresh(row)
    return _flag(row)


def list_config(db: Session) -> list[ConfigResponse]:
    return [_config(row) for row in db.query(AppConfigKv).order_by(AppConfigKv.key)]


def upsert_config(
    db: Session, key: str, value: Any, admin: AdminPrincipal
) -> ConfigResponse:
    row = db.get(AppConfigKv, key)
    if row is None:
        row = AppConfigKv(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    row.updated_by = admin.id
    db.commit()
    db.refresh(row)
    return _config(row)


def get_earnings_tiers(db: Session) -> dict[str, Any]:
    return tiers_with_listener_counts(db)


def update_earnings_tiers(
    db: Session, value: dict[str, Any], admin: AdminPrincipal
) -> dict[str, Any]:
    before = get_stored_tiers(db)
    sanitized = validate_tier_update(db, value)
    row = db.get(AppConfigKv, EARNINGS_TIERS_KEY)
    if row is None:
        row = AppConfigKv(key=EARNINGS_TIERS_KEY, value=sanitized)
        db.add(row)
    else:
        row.value = sanitized
    row.updated_by = admin.id
    refresh_listener_rates(db, sanitized)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="config.earnings_tiers_update",
        entity_type="app_config_kv",
        entity_id=EARNINGS_TIERS_KEY,
        before=before,
        after=sanitized,
    )
    db.commit()
    return tiers_with_listener_counts(db)
