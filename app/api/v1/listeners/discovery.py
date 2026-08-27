"""Listener discovery / find list."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import Session

from app.api.v1.listeners.schemas import ListenerListResponse, ListenerPublicResponse
from app.api.v1.listeners.service import get_public_listener
from app.core.pagination import clamp_page
from app.models.auth import User
from app.models.enums import Gender, ProfileStatus, UserRole
from app.models.lookups import ListenerComfortArea, ListenerLanguage
from app.models.profiles import ListenerProfile
from app.models.settings import ListenerPrivacySettings
from app.models.ventor_wellness import VentorFavorite


def list_listeners(
    db: Session,
    viewer: User,
    *,
    q: str | None = None,
    topic: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    languages: str | None = None,
    genders: str | None = None,
    min_rating: float | None = None,
    favorites: str = "any",
    online_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> ListenerListResponse:
    page, page_size = clamp_page(page, page_size)

    query = (
        db.query(ListenerProfile)
        .outerjoin(
            ListenerPrivacySettings,
            ListenerPrivacySettings.listener_id == ListenerProfile.user_id,
        )
        .filter(
            ListenerProfile.profile_status == ProfileStatus.approved,
            or_(
                ListenerPrivacySettings.profile_visible.is_(True),
                ListenerPrivacySettings.listener_id.is_(None),
            ),
        )
    )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                ListenerProfile.full_name.ilike(like),
                ListenerProfile.bio.ilike(like),
                ListenerProfile.about_me.ilike(like),
                ListenerProfile.city.ilike(like),
            )
        )
    if topic:
        query = query.filter(
            exists().where(
                and_(
                    ListenerComfortArea.listener_id == ListenerProfile.user_id,
                    ListenerComfortArea.comfort_area_id == topic,
                )
            )
        )
    if min_price is not None:
        query = query.filter(ListenerProfile.rate_per_minute >= Decimal(str(min_price)))
    if max_price is not None:
        query = query.filter(ListenerProfile.rate_per_minute <= Decimal(str(max_price)))
    if languages:
        lang_ids = [x.strip() for x in languages.split(",") if x.strip()]
        if lang_ids:
            query = query.filter(
                exists().where(
                    and_(
                        ListenerLanguage.listener_id == ListenerProfile.user_id,
                        ListenerLanguage.language_id.in_(lang_ids),
                    )
                )
            )
    if genders:
        gender_vals = []
        for raw in genders.split(","):
            raw = raw.strip()
            if raw in Gender.__members__:
                gender_vals.append(Gender(raw))
        if gender_vals:
            query = query.filter(ListenerProfile.gender.in_(gender_vals))
    if min_rating is not None:
        query = query.filter(ListenerProfile.rating_avg >= Decimal(str(min_rating)))
    if online_only:
        query = query.filter(ListenerProfile.is_online.is_(True))

    if viewer.role == UserRole.ventor and favorites in {"only", "exclude"}:
        fav_exists = exists().where(
            and_(
                VentorFavorite.ventor_id == viewer.id,
                VentorFavorite.listener_id == ListenerProfile.user_id,
            )
        )
        if favorites == "only":
            query = query.filter(fav_exists)
        else:
            query = query.filter(~fav_exists)

    total = query.with_entities(func.count(ListenerProfile.user_id)).scalar() or 0
    rows = (
        query.order_by(
            ListenerProfile.is_online.desc(),
            ListenerProfile.rating_avg.desc(),
            ListenerProfile.full_name.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        get_public_listener(db, row.user_id, viewer=viewer) for row in rows
    ]
    return ListenerListResponse(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )
