"""Notifications — docs/database-schema.md § 10."""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base, SoftDeleteMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationType


class Notification(Base, UUIDPrimaryKeyMixin, SoftDeleteMixin):
    __tablename__ = "notifications"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(
        Enum(NotificationType, name="notification_type", create_type=False),
        nullable=False,
    )
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)
    is_read = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_notifications_user_read_created",
            "user_id",
            "is_read",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("ix_notifications_user_deleted", "user_id", "deleted_at"),
    )
