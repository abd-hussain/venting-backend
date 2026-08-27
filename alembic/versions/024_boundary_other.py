"""Add boundaries catalog other row with custom text

Revision ID: 024_boundary_other
Revises: 023_listener_experience_enums
Create Date: 2026-08-28 01:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024_boundary_other"
down_revision: Union[str, Sequence[str], None] = "023_listener_experience_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM boundaries WHERE id = :id"),
        {"id": "other"},
    ).first()
    if exists:
        conn.execute(
            sa.text(
                "UPDATE boundaries "
                "SET name_en = :name_en, name_ar = :name_ar, "
                "icon_emoji = :icon_emoji, sort_order = :sort_order, "
                "allows_custom_text = true, is_active = true "
                "WHERE id = :id"
            ),
            {
                "id": "other",
                "name_en": "Other",
                "name_ar": "أخرى",
                "icon_emoji": "➕",
                "sort_order": 1000,
            },
        )
    else:
        conn.execute(
            sa.text(
                "INSERT INTO boundaries "
                "(id, name_en, name_ar, icon_emoji, sort_order, allows_custom_text, is_active) "
                "VALUES (:id, :name_en, :name_ar, :icon_emoji, :sort_order, true, true)"
            ),
            {
                "id": "other",
                "name_en": "Other",
                "name_ar": "أخرى",
                "icon_emoji": "➕",
                "sort_order": 1000,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE boundaries "
            "SET is_active = false, allows_custom_text = false "
            "WHERE id = :id"
        ),
        {"id": "other"},
    )
