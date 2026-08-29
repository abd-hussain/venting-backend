"""Ventor social / wellness — docs/database-schema.md § 5."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import MoodKind


class VentorFavorite(Base):
    __tablename__ = "ventor_favorites"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_ventor_favorites_listener_id", "listener_id"),)


class MoodCheckin(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "mood_checkins"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    mood = Column(Enum(MoodKind, name="mood_kind", create_type=False), nullable=False)
    note = Column(Text, nullable=True)
    checked_in_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    checkin_date = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("ventor_id", "checkin_date", name="uq_mood_checkins_ventor_date"),
        Index("ix_mood_checkins_ventor_id", "ventor_id"),
    )
