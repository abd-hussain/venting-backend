"""Availability tables — docs/database-schema.md § 4."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import DayOfWeek


class ListenerAvailabilitySettings(Base):
    __tablename__ = "listener_availability_settings"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    accept_instant_calls = Column(Boolean, nullable=False, server_default="true")
    session_length_minutes = Column(Integer, nullable=False, server_default="30")
    break_length_minutes = Column(Integer, nullable=False, server_default="15")
    time_zone_id = Column(String(64), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ListenerAvailabilitySlot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "listener_availability_slots"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    day = Column(Enum(DayOfWeek, name="day_of_week", create_type=False), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_availability_slot_time_range"),
        Index("ix_listener_availability_slots_listener_day", "listener_id", "day"),
    )
