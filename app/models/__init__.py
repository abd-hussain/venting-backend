"""
Import all ORM models so Alembic autogenerate sees Base.metadata.

See docs/database-schema.md (43 mobile) + docs/admin-portal-cms.md (12 CMS).
"""

from app.models import (  # noqa: F401
    admin,
    auth,
    availability,
    earnings,
    lookups,
    notifications,
    profiles,
    promo,
    rewards,
    sessions,
    settings,
    training,
    ventor_wellness,
)

__all__ = [
    "admin",
    "auth",
    "availability",
    "earnings",
    "lookups",
    "notifications",
    "profiles",
    "promo",
    "rewards",
    "sessions",
    "settings",
    "training",
    "ventor_wellness",
]
