"""Profile tables — docs/database-schema.md § 2. Profiles.

Tables:
  - ventor_profiles
  - listener_profiles
  - listener_identity_verifications
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    EarningsTier,
    Gender,
    ProfileStatus,
    SetupStepStatus,
)


class VentorProfile(Base, TimestampMixin):
    __tablename__ = "ventor_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nickname = Column(String(20), nullable=False)
    gender = Column(Enum(Gender, name="gender", create_type=False), nullable=False)
    avatar_url = Column(Text, nullable=True)
    quote = Column(String(280), nullable=True)
    is_anonymous = Column(Boolean, nullable=False, server_default="true")
    points_balance = Column(Integer, nullable=False, server_default="0")
    active_reward_offer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "reward_offers.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_ventor_profiles_active_reward_offer_id",
        ),
        nullable=True,
    )
    mood_streak_days = Column(Integer, nullable=False, server_default="0")
    last_mood_checkin_date = Column(Date, nullable=True)
    completed_sessions_count = Column(Integer, nullable=False, server_default="0")

    user = relationship("User", back_populates="ventor_profile")


class ListenerProfile(Base, TimestampMixin):
    __tablename__ = "listener_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    full_name = Column(String(120), nullable=False)
    phone_e164 = Column(String(32), nullable=True)
    phone_country_iso = Column(String(2), nullable=True)
    avatar_url = Column(Text, nullable=True)
    about_me = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    country = Column(String(100), nullable=True)
    country_iso = Column(String(2), nullable=True)
    city = Column(String(30), nullable=True)
    gender = Column(Enum(Gender, name="gender", create_type=False), nullable=True)
    bio = Column(Text, nullable=True)
    relationship_status = Column(String(32), nullable=True)
    family_role_ids = Column(JSONB, nullable=False, server_default="[]")
    voice_intro_url = Column(Text, nullable=True)
    voice_intro_seconds = Column(Integer, nullable=True)
    is_online = Column(Boolean, nullable=False, server_default="false")
    is_verified = Column(Boolean, nullable=False, server_default="false")
    profile_status = Column(
        Enum(ProfileStatus, name="profile_status", create_type=False),
        nullable=False,
        server_default="incomplete",
    )
    session_length_minutes = Column(Integer, nullable=False, server_default="30")
    break_length_minutes = Column(Integer, nullable=False, server_default="15")
    time_zone_id = Column(String(64), nullable=False)
    rate_per_minute = Column(Numeric(8, 2), nullable=False, server_default="0.25")
    current_tier = Column(
        Enum(EarningsTier, name="earnings_tier", create_type=False),
        nullable=False,
        server_default="starter",
    )
    rating_avg = Column(Numeric(3, 2), nullable=False, server_default="0")
    rating_count = Column(Integer, nullable=False, server_default="0")
    session_count = Column(Integer, nullable=False, server_default="0")
    rating_breakdown = Column(JSONB, nullable=True)
    setup_identity_status = Column(
        Enum(SetupStepStatus, name="setup_step_status", create_type=False),
        nullable=False,
        server_default="locked",
    )
    setup_profile_status = Column(
        Enum(SetupStepStatus, name="setup_step_status", create_type=False),
        nullable=False,
        server_default="locked",
    )
    setup_availability_status = Column(
        Enum(SetupStepStatus, name="setup_step_status", create_type=False),
        nullable=False,
        server_default="locked",
    )
    setup_training_status = Column(
        Enum(SetupStepStatus, name="setup_step_status", create_type=False),
        nullable=False,
        server_default="locked",
    )
    setup_tutorial_status = Column(
        Enum(SetupStepStatus, name="setup_step_status", create_type=False),
        nullable=False,
        server_default="locked",
    )
    first_session_tutorial_acked_at = Column(DateTime(timezone=True), nullable=True)
    book_first_session_acked_at = Column(DateTime(timezone=True), nullable=True)
    agreed_to_terms_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    steps_to_refill = Column(JSONB, nullable=False, server_default="[]")

    user = relationship("User", back_populates="listener_profile")
    identity_verifications = relationship(
        "ListenerIdentityVerification",
        back_populates="listener",
        order_by="ListenerIdentityVerification.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_listener_profiles_online_status", "is_online", "profile_status"),
        Index("ix_listener_profiles_rate_per_minute", "rate_per_minute"),
        Index("ix_listener_profiles_rating_avg", "rating_avg"),
        Index("ix_listener_profiles_country_iso", "country_iso"),
    )


class ListenerIdentityVerification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "listener_identity_verifications"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    identity_document_url = Column(Text, nullable=False)
    selfie_url = Column(Text, nullable=False)
    status = Column(
        Enum(ProfileStatus, name="profile_status", create_type=False),
        nullable=False,
        server_default="under_review",
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_note = Column(Text, nullable=True)
    reviewed_by_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    listener = relationship("ListenerProfile", back_populates="identity_verifications")

    __table_args__ = (
        Index(
            "ix_listener_identity_verifications_listener_created",
            "listener_id",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )
