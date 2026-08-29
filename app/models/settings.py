"""Privacy & notification settings — docs/database-schema.md § 6."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func
from sqlalchemy import String

from app.db.base import Base


class VentorPrivacySettings(Base):
    __tablename__ = "ventor_privacy_settings"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    show_mood_journey = Column(Boolean, nullable=False, server_default="true")
    show_stats = Column(Boolean, nullable=False, server_default="true")
    show_favorite_listeners = Column(Boolean, nullable=False, server_default="true")
    allow_listener_discovery = Column(Boolean, nullable=False, server_default="true")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ListenerPrivacySettings(Base):
    __tablename__ = "listener_privacy_settings"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    profile_visible = Column(Boolean, nullable=False, server_default="true")
    show_online_status = Column(Boolean, nullable=False, server_default="true")
    visible_in_all_countries = Column(Boolean, nullable=False, server_default="true")
    visible_countries = Column(ARRAY(String(2)), nullable=True)
    allow_search_indexing = Column(Boolean, nullable=False, server_default="true")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VentorNotificationPreferences(Base):
    __tablename__ = "ventor_notification_preferences"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    push_enabled = Column(Boolean, nullable=False, server_default="true")
    session_reminder_30_min = Column(Boolean, nullable=False, server_default="true")
    session_reminder_15_min = Column(Boolean, nullable=False, server_default="true")
    session_reminder_10_min = Column(Boolean, nullable=False, server_default="true")
    session_reminder_5_min = Column(Boolean, nullable=False, server_default="true")
    rewards_updates = Column(Boolean, nullable=False, server_default="true")
    promotions_updates = Column(Boolean, nullable=False, server_default="true")
    email_enabled = Column(Boolean, nullable=False, server_default="true")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ListenerNotificationPreferences(Base):
    __tablename__ = "listener_notification_preferences"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    push_enabled = Column(Boolean, nullable=False, server_default="true")
    new_session_requests = Column(Boolean, nullable=False, server_default="true")
    session_reminder_15_min = Column(Boolean, nullable=False, server_default="true")
    session_reminder_10_min = Column(Boolean, nullable=False, server_default="true")
    session_reminder_5_min = Column(Boolean, nullable=False, server_default="true")
    reviews_feedback = Column(Boolean, nullable=False, server_default="true")
    tips_earnings = Column(Boolean, nullable=False, server_default="true")
    promotions_updates = Column(Boolean, nullable=False, server_default="true")
    email_enabled = Column(Boolean, nullable=False, server_default="true")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
