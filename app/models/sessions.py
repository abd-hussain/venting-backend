"""Sessions, payments, feedback — docs/database-schema.md § 7."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CallMode,
    PaymentStatus,
    ReportReason,
    ReportedRole,
    SessionRequestStatus,
    SessionStatus,
    SessionTimeMode,
)


class SessionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "session_requests"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    status = Column(
        Enum(SessionRequestStatus, name="session_request_status", create_type=False),
        nullable=False,
    )
    message = Column(Text, nullable=True)
    chosen_reason = Column(String(120), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    time_mode = Column(
        Enum(SessionTimeMode, name="session_time_mode", create_type=False),
        nullable=False,
    )
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    call_mode = Column(
        Enum(CallMode, name="call_mode", create_type=False),
        nullable=False,
    )
    speech_language = Column(String(64), nullable=False)
    voice_change_enabled = Column(Boolean, nullable=False, server_default="false")
    is_instant = Column(Boolean, nullable=False, server_default="false")
    promo_code_id = Column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="SET NULL"),
        nullable=True,
    )
    reward_offer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reward_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    quoted_amount = Column(Numeric(12, 2), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    # FK to sessions added after sessions table exists (use_alter).
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL", use_alter=True, name="fk_session_requests_session_id"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_session_requests_listener_status", "listener_id", "status"),
        Index("ix_session_requests_ventor_status", "ventor_id", "status"),
        Index(
            "ix_session_requests_instant_status_created",
            "is_instant",
            "status",
            "created_at",
        ),
    )


class Session(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sessions"

    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_requests.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(SessionStatus, name="session_status", create_type=False),
        nullable=False,
    )
    duration_minutes = Column(Integer, nullable=False)
    actual_duration_seconds = Column(Integer, nullable=True)
    time_mode = Column(
        Enum(SessionTimeMode, name="session_time_mode", create_type=False),
        nullable=False,
    )
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    call_mode = Column(
        Enum(CallMode, name="call_mode", create_type=False),
        nullable=False,
    )
    speech_language = Column(String(64), nullable=False)
    voice_change_enabled = Column(Boolean, nullable=False, server_default="false")
    is_instant = Column(Boolean, nullable=False, server_default="false")
    message = Column(Text, nullable=True)
    chosen_reason = Column(String(120), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    listener_history_outcome = Column(String(16), nullable=True)
    missed_by_listener = Column(Boolean, nullable=False, server_default="false")
    call_channel_id = Column(String(128), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_sessions_ventor_status_scheduled", "ventor_id", "status", "scheduled_at"),
        Index(
            "ix_sessions_listener_status_scheduled",
            "listener_id",
            "status",
            "scheduled_at",
        ),
    )


class SessionPayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "session_payments"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    currency = Column(String(3), nullable=False, server_default="USD")
    session_price = Column(Numeric(12, 2), nullable=False)
    voice_change_fee = Column(Numeric(12, 2), nullable=False, server_default="0")
    discount_amount = Column(Numeric(12, 2), nullable=False, server_default="0")
    tip_amount = Column(Numeric(12, 2), nullable=False, server_default="0")
    amount_paid = Column(Numeric(12, 2), nullable=False)
    refunded_amount = Column(Numeric(12, 2), nullable=False, server_default="0")
    status = Column(
        Enum(PaymentStatus, name="payment_status", create_type=False),
        nullable=False,
    )
    provider = Column(String(32), nullable=True)
    provider_payment_id = Column(String(128), nullable=True)
    promo_code_id = Column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="SET NULL"),
        nullable=True,
    )
    reward_offer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reward_offers.id", ondelete="SET NULL"),
        nullable=True,
    )


class SessionRating(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "session_ratings"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    stars = Column(SmallInteger, nullable=False)
    review = Column(Text, nullable=True)
    tip_amount = Column(Numeric(12, 2), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("stars >= 1 AND stars <= 5", name="ck_session_ratings_stars"),
        Index("ix_session_ratings_listener_id", "listener_id"),
    )


class SessionListenerFeedback(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "session_listener_feedback"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    stars = Column(SmallInteger, nullable=False)
    felt_heard = Column(Boolean, nullable=False)
    talk_again = Column(Boolean, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "stars >= 1 AND stars <= 5", name="ck_session_listener_feedback_stars"
        ),
    )


class SessionReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "session_reports"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporter_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reported_role = Column(
        Enum(ReportedRole, name="reported_role", create_type=False),
        nullable=False,
    )
    reason = Column(
        Enum(ReportReason, name="report_reason", create_type=False),
        nullable=False,
    )
    details = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, server_default="open")
    assigned_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_session_reports_session_id", "session_id"),)
