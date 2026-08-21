"""admin_refresh_tokens for portal JWT rotation

Revision ID: 004_admin_refresh
Revises: 003_admin_cms
Create Date: 2026-08-21 16:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_admin_refresh"
down_revision: Union[str, Sequence[str], None] = "003_admin_cms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_admin_refresh_tokens_admin_user_id",
        "admin_refresh_tokens",
        ["admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_refresh_tokens_admin_user_id",
        table_name="admin_refresh_tokens",
    )
    op.drop_table("admin_refresh_tokens")
