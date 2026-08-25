"""comfort_areas icon_emoji column

Revision ID: 012_icon_emoji
Revises: 011_catalog_urls_vl
Create Date: 2026-08-25 14:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_icon_emoji"
down_revision: Union[str, Sequence[str], None] = "011_catalog_urls_vl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_EMOJIS = {
    "relationships": "❤️",
    "marriage": "💍",
    "parenting": "👨‍👩‍👧",
    "career_work": "💼",
    "stress_anxiety": "😰",
    "loneliness": "😔",
    "student_life": "🎓",
    "financial_stress": "💰",
    "health_wellness": "🩺",
    "other": "➕",
}


def upgrade() -> None:
    op.add_column(
        "comfort_areas",
        sa.Column("icon_emoji", sa.String(length=16), server_default="📌", nullable=False),
    )

    comfort = sa.table(
        "comfort_areas",
        sa.column("id", sa.String),
        sa.column("icon_emoji", sa.String),
    )
    bind = op.get_bind()
    for item_id, emoji in SEED_EMOJIS.items():
        bind.execute(
            comfort.update().where(comfort.c.id == item_id).values(icon_emoji=emoji)
        )


def downgrade() -> None:
    op.drop_column("comfort_areas", "icon_emoji")
