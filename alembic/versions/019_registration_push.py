"""Registration push tokens + listener custom tag text

Revision ID: 019_registration_push
Revises: 018_boundary_catalog
Create Date: 2026-08-26 02:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_registration_push"
down_revision: Union[str, Sequence[str], None] = "018_boundary_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_push_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_user_push_tokens_token"),
    )
    op.create_index("ix_user_push_tokens_user_id", "user_push_tokens", ["user_id"])

    op.add_column("listener_comfort_areas", sa.Column("custom_text", sa.Text(), nullable=True))
    op.add_column("listener_boundaries", sa.Column("custom_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("listener_boundaries", "custom_text")
    op.drop_column("listener_comfort_areas", "custom_text")
    op.drop_index("ix_user_push_tokens_user_id", table_name="user_push_tokens")
    op.drop_table("user_push_tokens")
