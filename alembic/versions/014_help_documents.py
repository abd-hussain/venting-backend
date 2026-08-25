"""help_documents table for help center topic links

Revision ID: 014_help_documents
Revises: 013_legal_documents
Create Date: 2026-08-25 15:50:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_help_documents"
down_revision: Union[str, Sequence[str], None] = "013_legal_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (topic, locale, title, url)
SEED_ROWS = (
    (
        "getting_started",
        "en",
        "Getting started",
        "https://cdn.venting.app/help/en/getting-started.html",
    ),
    (
        "getting_started",
        "ar",
        "البدء",
        "https://cdn.venting.app/help/ar/getting-started.html",
    ),
    ("faqs", "en", "FAQs", "https://cdn.venting.app/help/en/faqs.html"),
    ("faqs", "ar", "الأسئلة الشائعة", "https://cdn.venting.app/help/ar/faqs.html"),
    (
        "guidelines",
        "en",
        "Community guidelines",
        "https://cdn.venting.app/help/en/guidelines.html",
    ),
    (
        "guidelines",
        "ar",
        "إرشادات المجتمع",
        "https://cdn.venting.app/help/ar/guidelines.html",
    ),
    ("licenses", "en", "Licenses", "https://cdn.venting.app/help/en/licenses.html"),
    ("licenses", "ar", "التراخيص", "https://cdn.venting.app/help/ar/licenses.html"),
)


def upgrade() -> None:
    op.create_table(
        "help_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
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
        sa.UniqueConstraint("topic", "locale", name="uq_help_documents_topic_locale"),
    )

    help_table = sa.table(
        "help_documents",
        sa.column("id", sa.UUID()),
        sa.column("topic", sa.String()),
        sa.column("locale", sa.String()),
        sa.column("title", sa.String()),
        sa.column("url", sa.Text()),
        sa.column("is_published", sa.Boolean()),
    )
    op.bulk_insert(
        help_table,
        [
            {
                "id": str(uuid.uuid4()),
                "topic": topic,
                "locale": locale,
                "title": title,
                "url": url,
                "is_published": True,
            }
            for topic, locale, title, url in SEED_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_table("help_documents")
