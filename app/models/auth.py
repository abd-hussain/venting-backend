"""Auth tables — docs/database-schema.md § 1. Auth.

Tables:
  - users
  - refresh_tokens
  - auth_identities
  - password_reset_tokens
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuthProvider, UserRole


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum(UserRole, name="user_role", create_type=True), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    registration_complete = Column(Boolean, nullable=False, server_default="false")
    registration_completed_steps = Column(JSONB, nullable=False, server_default="[]")
    registration_next_step = Column(String(64), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    suspended_until = Column(DateTime(timezone=True), nullable=True)

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    auth_identities = relationship(
        "AuthIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ventor_profile = relationship(
        "VentorProfile", back_populates="user", uselist=False
    )
    listener_profile = relationship(
        "ListenerProfile", back_populates="user", uselist=False
    )

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_deleted_at", "deleted_at"),
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "refresh_tokens"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(255), nullable=False, unique=True)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)


class AuthIdentity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "auth_identities"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(
        Enum(AuthProvider, name="auth_provider", create_type=True),
        nullable=False,
    )
    provider_user_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    raw_profile = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="auth_identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identities_provider_sub"),
        UniqueConstraint("user_id", "provider", name="uq_auth_identities_user_provider"),
        Index("ix_auth_identities_user_id", "user_id"),
    )


class PasswordResetToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "password_reset_tokens"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    requested_ip = Column(String(64), nullable=True)
    locale = Column(String(8), nullable=False, server_default="en")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )
