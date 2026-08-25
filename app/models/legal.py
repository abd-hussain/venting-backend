"""Legal documents — docs/database-schema.md § 43b."""

from sqlalchemy import Boolean, Column, String, Text, UniqueConstraint

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LegalDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "legal_documents"

    document = Column(String(16), nullable=False)
    locale = Column(String(8), nullable=False)
    title = Column(String(128), nullable=False)
    url = Column(Text, nullable=False)
    is_published = Column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("document", "locale", name="uq_legal_documents_document_locale"),
    )
