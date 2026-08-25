"""legal_documents table for terms/privacy links

Revision ID: 013_legal_documents
Revises: 012_icon_emoji
Create Date: 2026-08-25 15:35:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_legal_documents"
down_revision: Union[str, Sequence[str], None] = "012_icon_emoji"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_ROWS = (
    ("terms", "en", "Terms of Service", "https://cdn.venting.app/legal/en/terms.html"),
    ("terms", "ar", "شروط الخدمة", "https://cdn.venting.app/legal/ar/terms.html"),
    ("privacy", "en", "Privacy Policy", "https://cdn.venting.app/legal/en/privacy.html"),
    ("privacy", "ar", "سياسة الخصوصية", "https://cdn.venting.app/legal/ar/privacy.html"),
)


def upgrade() -> None:
    op.create_table(
        "legal_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document", "locale", name="uq_legal_documents_document_locale"
        ),
    )

    legal = sa.table(
        "legal_documents",
        sa.column("id", sa.UUID()),
        sa.column("document", sa.String()),
        sa.column("locale", sa.String()),
        sa.column("title", sa.String()),
        sa.column("url", sa.Text()),
        sa.column("is_published", sa.Boolean()),
    )
    op.bulk_insert(
        legal,
        [
            {
                "id": str(uuid.uuid4()),
                "document": document,
                "locale": locale,
                "title": title,
                "url": url,
                "is_published": True,
            }
            for document, locale, title, url in SEED_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_table("legal_documents")
