"""Favorite count helpers for admin listener views."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ventor_wellness import VentorFavorite


def favorite_count(db: Session, listener_id: UUID) -> int:
    return int(
        db.query(func.count(VentorFavorite.ventor_id))
        .filter(VentorFavorite.listener_id == listener_id)
        .scalar()
        or 0
    )


def favorite_counts_map(db: Session, listener_ids: list[UUID]) -> dict[UUID, int]:
    if not listener_ids:
        return {}
    rows = (
        db.query(VentorFavorite.listener_id, func.count(VentorFavorite.ventor_id))
        .filter(VentorFavorite.listener_id.in_(listener_ids))
        .group_by(VentorFavorite.listener_id)
        .all()
    )
    return {listener_id: int(count) for listener_id, count in rows}
