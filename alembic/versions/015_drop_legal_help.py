"""Drop legal_documents and help_documents (static HTML instead)

Revision ID: 015_drop_legal_help
Revises: 014_help_documents
Create Date: 2026-08-25 16:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_drop_legal_help"
down_revision: Union[str, Sequence[str], None] = "014_help_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("help_documents")
    op.drop_table("legal_documents")


def downgrade() -> None:
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
