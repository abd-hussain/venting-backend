"""Drop achievements tables and show_achievements column

Revision ID: 030_drop_achievements
Revises: 029_book_first_session_ack
Create Date: 2026-08-29 18:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "030_drop_achievements"
down_revision: Union[str, Sequence[str], None] = "029_book_first_session_ack"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("ventor_achievements")
    op.drop_table("achievements")
    op.drop_column("ventor_privacy_settings", "show_achievements")


def downgrade() -> None:
    op.add_column(
        "ventor_privacy_settings",
        sa.Column("show_achievements", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_table(
        "achievements",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title_key", sa.String(length=128), nullable=False),
        sa.Column("subtitle_key", sa.String(length=128), nullable=False),
        sa.Column("description_key", sa.String(length=128), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ventor_achievements",
        sa.Column("ventor_id", sa.UUID(), nullable=False),
        sa.Column("achievement_id", sa.String(length=64), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["achievement_id"], ["achievements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ventor_id"], ["ventor_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("ventor_id", "achievement_id"),
    )
