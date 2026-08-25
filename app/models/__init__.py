"""
Import all ORM models so Alembic autogenerate sees Base.metadata.

See docs/database-schema.md.
"""

from app.models import (  # noqa: F401
    admin,
    auth,
    availability,
    earnings,
    help,
    legal,
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
    "help",
    "legal",
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
