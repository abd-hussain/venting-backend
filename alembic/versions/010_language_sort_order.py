"""languages sort_order for speaking lookup

Revision ID: 010_language_sort_order
Revises: 009_comfort_categories
Create Date: 2026-08-25 13:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_language_sort_order"
down_revision: Union[str, Sequence[str], None] = "009_comfort_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_LANGUAGES = [
    {"id": "en", "name_en": "English", "name_ar": "الإنجليزية", "sort_order": 10},
    {"id": "ar", "name_en": "Arabic", "name_ar": "العربية", "sort_order": 20},
    {"id": "fr", "name_en": "French", "name_ar": "الفرنسية", "sort_order": 30},
    {"id": "es", "name_en": "Spanish", "name_ar": "الإسبانية", "sort_order": 40},
    {"id": "de", "name_en": "German", "name_ar": "الألمانية", "sort_order": 50},
    {"id": "tr", "name_en": "Turkish", "name_ar": "التركية", "sort_order": 60},
    {"id": "pt", "name_en": "Portuguese", "name_ar": "البرتغالية", "sort_order": 70},
    {"id": "hi", "name_en": "Hindi", "name_ar": "الهندية", "sort_order": 80},
    {"id": "ur", "name_en": "Urdu", "name_ar": "الأردية", "sort_order": 90},
]


def upgrade() -> None:
    op.add_column(
        "languages",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_languages_sort_order", "languages", ["sort_order"])

    languages = sa.table(
        "languages",
        sa.column("id", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    bind = op.get_bind()
    for row in SEED_LANGUAGES:
        exists = bind.execute(
            sa.select(languages.c.id).where(languages.c.id == row["id"])
        ).fetchone()
        if exists:
            bind.execute(
                languages.update()
                .where(languages.c.id == row["id"])
                .values(
                    name_en=row["name_en"],
                    name_ar=row["name_ar"],
                    sort_order=row["sort_order"],
                    is_active=True,
                )
            )
        else:
            bind.execute(
                languages.insert().values(
                    id=row["id"],
                    name_en=row["name_en"],
                    name_ar=row["name_ar"],
                    sort_order=row["sort_order"],
                    is_active=True,
                )
            )


def downgrade() -> None:
    op.drop_index("ix_languages_sort_order", table_name="languages")
    op.drop_column("languages", "sort_order")
