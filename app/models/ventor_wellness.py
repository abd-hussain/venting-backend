"""Ventor social / wellness — docs/database-schema.md § 5."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
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


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String(64), primary_key=True)
    title_key = Column(String(128), nullable=False)
    subtitle_key = Column(String(128), nullable=False)
    description_key = Column(String(128), nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")


class VentorAchievement(Base):
    __tablename__ = "ventor_achievements"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_id = Column(
        String(64),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unlocked_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
