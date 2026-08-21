"""Training — docs/database-schema.md § 11."""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.models.enums import TrainingStatus


class TrainingModule(Base):
    __tablename__ = "training_modules"

    id = Column(String(64), primary_key=True)
    title_key = Column(String(128), nullable=False)
    content_url = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")


class ListenerTrainingProgress(Base):
    __tablename__ = "listener_training_progress"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    module_id = Column(
        String(64),
        ForeignKey("training_modules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(
        Enum(TrainingStatus, name="training_status", create_type=False),
        nullable=False,
        server_default="not_started",
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
