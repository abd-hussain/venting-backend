"""Session price tier config — app_config_kv `earnings_tiers` + listener counts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import tier_has_listeners, validation_error
from app.models.admin import AppConfigKv
from app.models.enums import EarningsTier
from app.models.profiles import ListenerProfile

EARNINGS_TIERS_KEY = "earnings_tiers"

DEFAULT_EARNINGS_TIERS: dict[str, dict[str, Any]] = {
    "starter": {"rate_per_minute": 0.25, "min_sessions": 0, "label": "Starter"},
    "rising": {"rate_per_minute": 0.35, "min_sessions": 25, "label": "Rising"},
    "trusted": {"rate_per_minute": 0.45, "min_sessions": 100, "label": "Trusted"},
    "expert": {"rate_per_minute": 0.55, "min_sessions": 250, "label": "Expert"},
    "elite": {"rate_per_minute": 0.70, "min_sessions": 500, "label": "Elite"},
}


def get_stored_tiers(db: Session) -> dict[str, dict[str, Any]]:
    row = db.get(AppConfigKv, EARNINGS_TIERS_KEY)
    if row is None or not isinstance(row.value, dict):
        return dict(DEFAULT_EARNINGS_TIERS)
    return row.value


def listener_counts_by_tier(db: Session) -> dict[str, int]:
    rows = (
        db.query(ListenerProfile.current_tier, func.count(ListenerProfile.user_id))
        .group_by(ListenerProfile.current_tier)
        .all()
    )
    return {
        (tier.value if hasattr(tier, "value") else str(tier)): int(count)
        for tier, count in rows
    }


def count_listeners_on_tier(db: Session, tier_id: str) -> int:
    try:
        tier = EarningsTier(tier_id)
    except ValueError:
        return 0
    return int(
        db.query(func.count(ListenerProfile.user_id))
        .filter(ListenerProfile.current_tier == tier)
        .scalar()
        or 0
    )


def tiers_with_listener_counts(db: Session) -> dict[str, dict[str, Any]]:
    stored = get_stored_tiers(db)
    counts = listener_counts_by_tier(db)
    return {
        tier_id: {
            **tier_data,
            "listener_count": counts.get(tier_id, 0),
        }
        for tier_id, tier_data in stored.items()
    }


def _sanitize_tier_entry(
    tier_id: str,
    data: Any,
    *,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise validation_error(f"Invalid tier payload for {tier_id}")
    if "listener_count" in data:
        data = {key: value for key, value in data.items() if key != "listener_count"}
    if "rate_per_minute" not in data:
        raise validation_error(
            f"rate_per_minute is required for tier {tier_id}",
            en=f"rate_per_minute is required for tier {tier_id}",
        )
    try:
        rate = float(data["rate_per_minute"])
    except (TypeError, ValueError) as exc:
        raise validation_error(
            f"Invalid rate_per_minute for tier {tier_id}",
            en=f"Invalid rate_per_minute for tier {tier_id}",
        ) from exc
    if rate < 0:
        raise validation_error(
            f"rate_per_minute must be >= 0 for tier {tier_id}",
            en=f"rate_per_minute must be >= 0 for tier {tier_id}",
        )
    sanitized: dict[str, Any] = {"rate_per_minute": rate}
    if "label" in data and data["label"] is not None:
        sanitized["label"] = str(data["label"])
    elif existing and existing.get("label") is not None:
        sanitized["label"] = existing["label"]
    if "min_sessions" in data:
        sanitized["min_sessions"] = data["min_sessions"]
    elif existing and "min_sessions" in existing:
        sanitized["min_sessions"] = existing["min_sessions"]
    return sanitized


def validate_tier_update(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict) or not payload:
        raise validation_error("At least one tier is required")
    stored = get_stored_tiers(db)
    removed = set(stored.keys()) - set(payload.keys())
    for tier_id in removed:
        assigned = count_listeners_on_tier(db, tier_id)
        if assigned > 0:
            raise tier_has_listeners(tier_id, assigned)
    return {
        tier_id: _sanitize_tier_entry(
            tier_id,
            tier_data,
            existing=stored.get(tier_id),
        )
        for tier_id, tier_data in payload.items()
    }


def refresh_listener_rates(db: Session, tiers: dict[str, dict[str, Any]]) -> None:
    for tier_id, tier_data in tiers.items():
        try:
            tier = EarningsTier(tier_id)
        except ValueError:
            continue
        rate = Decimal(str(tier_data["rate_per_minute"]))
        (
            db.query(ListenerProfile)
            .filter(ListenerProfile.current_tier == tier)
            .update(
                {ListenerProfile.rate_per_minute: rate},
                synchronize_session=False,
            )
        )
