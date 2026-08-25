"""life_experiences.sort_order for catalog #76

Revision ID: 017_life_exp_sort
Revises: 016_password_reset
Create Date: 2026-08-25 21:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_life_exp_sort"
down_revision: Union[str, Sequence[str], None] = "016_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Prefer the mobile registration chip set; relationship/family enums are client-local.
SEED = (
    ("career_change", "Career Change", "تغيير المسار المهني", 10),
    ("job_loss", "Jobless", "بلا عمل", 20),
    ("grief_loss", "Grief/Loss", "الفقدان / الحزن", 30),
    ("anxiety_stress", "Anxiety/Stress", "القلق / التوتر", 40),
    ("financial_stress", "Financial Stress", "ضغط مالي", 50),
    ("life_stages", "Life Stages", "مراحل الحياة", 60),
    ("health_challenge", "Health Challenge", "تحدٍ صحي", 70),
)

# Legacy relationship/family rows — keep IDs but hide from public catalog.
DEACTIVATE = (
    "single",
    "in_relationship",
    "married",
    "divorced",
    "widowed",
    "parent",
    "single_parent",
    "caregiver",
    "startup_founder",
    "financial_struggle",
    "addiction_recovery",
)


def upgrade() -> None:
    op.add_column(
        "life_experiences",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )

    conn = op.get_bind()
    for item_id, name_en, name_ar, sort_order in SEED:
        exists = conn.execute(
            sa.text("SELECT 1 FROM life_experiences WHERE id = :id"),
            {"id": item_id},
        ).first()
        if exists:
            conn.execute(
                sa.text(
                    "UPDATE life_experiences "
                    "SET name_en = :name_en, name_ar = :name_ar, "
                    "sort_order = :sort_order, is_active = true "
                    "WHERE id = :id"
                ),
                {
                    "id": item_id,
                    "name_en": name_en,
                    "name_ar": name_ar,
                    "sort_order": sort_order,
                },
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO life_experiences "
                    "(id, name_en, name_ar, sort_order, is_active) "
                    "VALUES (:id, :name_en, :name_ar, :sort_order, true)"
                ),
                {
                    "id": item_id,
                    "name_en": name_en,
                    "name_ar": name_ar,
                    "sort_order": sort_order,
                },
            )

    if DEACTIVATE:
        conn.execute(
            sa.text(
                "UPDATE life_experiences SET is_active = false "
                "WHERE id IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"ids": list(DEACTIVATE)},
        )


def downgrade() -> None:
    op.drop_column("life_experiences", "sort_order")
