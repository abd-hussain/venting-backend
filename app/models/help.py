"""Help documents — docs/database-schema.md § 43c."""

from sqlalchemy import Boolean, Column, String, Text, UniqueConstraint

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HelpDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "help_documents"

    topic = Column(String(64), nullable=False)
    locale = Column(String(8), nullable=False)
    title = Column(String(128), nullable=False)
    url = Column(Text, nullable=False)
    is_published = Column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("topic", "locale", name="uq_help_documents_topic_locale"),
    )
