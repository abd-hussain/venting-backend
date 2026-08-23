"""Recompute cached listener rating fields from session_ratings."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.profiles import ListenerProfile
from app.models.sessions import SessionRating


def recompute_listener_rating_cache(db: Session, listener_id: UUID) -> ListenerProfile:
    profile = db.get(ListenerProfile, listener_id)
    if profile is None:
        raise not_found("Listener")

    count, avg = (
        db.query(
            func.count(SessionRating.id),
            func.avg(SessionRating.stars),
        )
        .filter(SessionRating.listener_id == listener_id)
        .one()
    )
    count = int(count or 0)
    breakdown_rows = (
        db.query(SessionRating.stars, func.count(SessionRating.id))
        .filter(SessionRating.listener_id == listener_id)
        .group_by(SessionRating.stars)
        .all()
    )
    breakdown = {str(stars): 0 for stars in range(1, 6)}
    for stars, star_count in breakdown_rows:
        breakdown[str(stars)] = int(star_count)

    profile.rating_count = count
    profile.rating_avg = (
        Decimal("0") if count == 0 else Decimal(str(round(float(avg or 0), 2)))
    )
    profile.rating_breakdown = breakdown
    return profile
