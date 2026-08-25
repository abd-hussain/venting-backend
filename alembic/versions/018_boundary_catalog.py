"""boundaries catalog fields for #77

Revision ID: 018_boundary_catalog
Revises: 017_life_exp_sort
Create Date: 2026-08-26 01:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_boundary_catalog"
down_revision: Union[str, Sequence[str], None] = "017_life_exp_sort"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED = (
    ("suicide_self_harm", "🛡️", 10),
    ("domestic_violence", "🏠", 20),
    ("sexual_topics", "👁️", 30),
    ("addiction", "💊", 40),
    ("politics", "🏛️", 50),
    ("religion", "📖", 60),
    ("illegal_activities", "🚫", 70),
)


def upgrade() -> None:
    op.add_column(
        "boundaries",
        sa.Column("icon_emoji", sa.String(length=16), server_default="🛡️", nullable=False),
    )
    op.add_column("boundaries", sa.Column("icon_url", sa.Text(), nullable=True))
    op.add_column(
        "boundaries",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "boundaries",
        sa.Column(
            "allows_custom_text",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE boundaries SET icon_url = image_url "
            "WHERE image_url IS NOT NULL AND icon_url IS NULL"
        )
    )

    for item_id, icon_emoji, sort_order in SEED:
        conn.execute(
            sa.text(
                "UPDATE boundaries "
                "SET icon_emoji = :icon_emoji, sort_order = :sort_order "
                "WHERE id = :id"
            ),
            {"id": item_id, "icon_emoji": icon_emoji, "sort_order": sort_order},
        )


def downgrade() -> None:
    op.drop_column("boundaries", "allows_custom_text")
    op.drop_column("boundaries", "sort_order")
    op.drop_column("boundaries", "icon_url")
    op.drop_column("boundaries", "icon_emoji")
