"""comfort_areas category fields + seed

Revision ID: 009_comfort_categories
Revises: 008_social_auth
Create Date: 2026-08-25 13:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_comfort_categories"
down_revision: Union[str, Sequence[str], None] = "008_social_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_CATEGORIES = [
    {
        "id": "relationships",
        "name_en": "Relationships",
        "name_ar": "العلاقات",
        "icon_key": "favorite",
        "sort_order": 10,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "relationships",
    },
    {
        "id": "marriage",
        "name_en": "Marriage",
        "name_ar": "الزواج",
        "icon_key": "favorite_border",
        "sort_order": 20,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "relationships",
    },
    {
        "id": "parenting",
        "name_en": "Parenting",
        "name_ar": "الأبوة والأمومة",
        "icon_key": "family_restroom",
        "sort_order": 30,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "family",
    },
    {
        "id": "career_work",
        "name_en": "Career & work",
        "name_ar": "العمل والمسار المهني",
        "icon_key": "work_outline",
        "sort_order": 40,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "career",
    },
    {
        "id": "stress_anxiety",
        "name_en": "Stress & anxiety",
        "name_ar": "التوتر والقلق",
        "icon_key": "psychology_alt",
        "sort_order": 50,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "mental",
    },
    {
        "id": "loneliness",
        "name_en": "Loneliness",
        "name_ar": "الوحدة",
        "icon_key": "person_outline",
        "sort_order": 60,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "mental",
    },
    {
        "id": "student_life",
        "name_en": "Student life",
        "name_ar": "حياة الطالب",
        "icon_key": "school",
        "sort_order": 70,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "life",
    },
    {
        "id": "financial_stress",
        "name_en": "Financial stress",
        "name_ar": "الضغط المالي",
        "icon_key": "attach_money",
        "sort_order": 80,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "money",
    },
    {
        "id": "health_wellness",
        "name_en": "Health & wellness",
        "name_ar": "الصحة والعافية",
        "icon_key": "health_and_safety",
        "sort_order": 90,
        "allows_custom_text": False,
        "audience": "ventor",
        "topic_group": "health",
    },
    {
        "id": "other",
        "name_en": "Other",
        "name_ar": "أخرى",
        "icon_key": "add_circle_outline",
        "sort_order": 1000,
        "allows_custom_text": True,
        "audience": "ventor",
        "topic_group": None,
    },
]


def upgrade() -> None:
    op.add_column(
        "comfort_areas",
        sa.Column("icon_key", sa.String(length=64), server_default="category", nullable=False),
    )
    op.add_column(
        "comfort_areas",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "comfort_areas",
        sa.Column(
            "allows_custom_text",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "comfort_areas",
        sa.Column("audience", sa.String(length=32), server_default="all", nullable=False),
    )
    op.create_index("ix_comfort_areas_sort_order", "comfort_areas", ["sort_order"])
    op.create_index("ix_comfort_areas_audience", "comfort_areas", ["audience"])

    op.add_column(
        "ventor_interests",
        sa.Column("custom_text", sa.String(length=280), nullable=True),
    )

    comfort = sa.table(
        "comfort_areas",
        sa.column("id", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("icon_key", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("allows_custom_text", sa.Boolean),
        sa.column("audience", sa.String),
        sa.column("topic_group", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    bind = op.get_bind()
    for row in SEED_CATEGORIES:
        exists = bind.execute(
            sa.select(comfort.c.id).where(comfort.c.id == row["id"])
        ).fetchone()
        if exists:
            bind.execute(
                comfort.update()
                .where(comfort.c.id == row["id"])
                .values(
                    name_en=row["name_en"],
                    name_ar=row["name_ar"],
                    icon_key=row["icon_key"],
                    sort_order=row["sort_order"],
                    allows_custom_text=row["allows_custom_text"],
                    audience=row["audience"],
                    topic_group=row["topic_group"],
                    is_active=True,
                )
            )
        else:
            bind.execute(
                comfort.insert().values(
                    id=row["id"],
                    name_en=row["name_en"],
                    name_ar=row["name_ar"],
                    icon_key=row["icon_key"],
                    sort_order=row["sort_order"],
                    allows_custom_text=row["allows_custom_text"],
                    audience=row["audience"],
                    topic_group=row["topic_group"],
                    is_active=True,
                )
            )


def downgrade() -> None:
    op.drop_column("ventor_interests", "custom_text")
    op.drop_index("ix_comfort_areas_audience", table_name="comfort_areas")
    op.drop_index("ix_comfort_areas_sort_order", table_name="comfort_areas")
    op.drop_column("comfort_areas", "audience")
    op.drop_column("comfort_areas", "allows_custom_text")
    op.drop_column("comfort_areas", "sort_order")
    op.drop_column("comfort_areas", "icon_key")
