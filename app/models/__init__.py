"""
Import all ORM models so Alembic autogenerate sees Base.metadata.

See docs/database-schema.md for the full 43-table map.
"""

from app.models import (  # noqa: F401
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
