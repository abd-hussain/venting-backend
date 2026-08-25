"""catalog icon_url flag_url ventor_languages

Revision ID: 011_catalog_urls_vl
Revises: 010_language_sort_order
Create Date: 2026-08-25 14:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_catalog_urls_vl"
down_revision: Union[str, Sequence[str], None] = "010_language_sort_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_LANGUAGES = [
    {
        "id": "en",
        "name_en": "English",
        "name_native": "English",
        "name_ar": "الإنجليزية",
        "flag_url": "https://flagcdn.com/w160/gb.png",
        "flag_emoji": "🇬🇧",
        "sort_order": 10,
    },
    {
        "id": "hi",
        "name_en": "Hindi",
        "name_native": "हिन्दी",
        "name_ar": "الهندية",
        "flag_url": "https://flagcdn.com/w160/in.png",
        "flag_emoji": "🇮🇳",
        "sort_order": 20,
    },
    {
        "id": "es",
        "name_en": "Spanish",
        "name_native": "Español",
        "name_ar": "الإسبانية",
        "flag_url": "https://flagcdn.com/w160/es.png",
        "flag_emoji": "🇪🇸",
        "sort_order": 30,
    },
    {
        "id": "ar",
        "name_en": "Arabic",
        "name_native": "العربية",
        "name_ar": "العربية",
        "flag_url": "https://flagcdn.com/w160/sa.png",
        "flag_emoji": "🇸🇦",
        "sort_order": 40,
    },
    {
        "id": "bn",
        "name_en": "Bengali",
        "name_native": "বাংলা",
        "name_ar": "البنغالية",
        "flag_url": "https://flagcdn.com/w160/bd.png",
        "flag_emoji": "🇧🇩",
        "sort_order": 50,
    },
    {
        "id": "tr",
        "name_en": "Turkish",
        "name_native": "Türkçe",
        "name_ar": "التركية",
        "flag_url": "https://flagcdn.com/w160/tr.png",
        "flag_emoji": "🇹🇷",
        "sort_order": 60,
    },
    {
        "id": "fr",
        "name_en": "French",
        "name_native": "Français",
        "name_ar": "الفرنسية",
        "flag_url": "https://flagcdn.com/w160/fr.png",
        "flag_emoji": "🇫🇷",
        "sort_order": 70,
    },
    {
        "id": "de",
        "name_en": "German",
        "name_native": "Deutsch",
        "name_ar": "الألمانية",
        "flag_url": "https://flagcdn.com/w160/de.png",
        "flag_emoji": "🇩🇪",
        "sort_order": 80,
    },
    {
        "id": "pt",
        "name_en": "Portuguese",
        "name_native": "Português",
        "name_ar": "البرتغالية",
        "flag_url": "https://flagcdn.com/w160/pt.png",
        "flag_emoji": "🇵🇹",
        "sort_order": 90,
    },
    {
        "id": "ur",
        "name_en": "Urdu",
        "name_native": "اردو",
        "name_ar": "الأردية",
        "flag_url": "https://flagcdn.com/w160/pk.png",
        "flag_emoji": "🇵🇰",
        "sort_order": 100,
    },
]


def upgrade() -> None:
    # languages: speaking-language catalog fields
    op.add_column("languages", sa.Column("name_native", sa.String(length=64), nullable=True))
    op.add_column("languages", sa.Column("flag_url", sa.Text(), nullable=True))
    op.add_column("languages", sa.Column("flag_emoji", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE languages
        SET name_native = COALESCE(name_native, name_en),
            flag_url = COALESCE(flag_url, image_url)
        """
    )
    op.alter_column("languages", "name_native", existing_type=sa.String(length=64), nullable=False)
    op.drop_column("languages", "image_url")

    # comfort_areas: icon_url replaces icon_key / image_url for mobile contract
    op.add_column("comfort_areas", sa.Column("icon_url", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE comfort_areas
        SET icon_url = COALESCE(icon_url, image_url)
        """
    )
    op.drop_column("comfort_areas", "icon_key")
    op.drop_column("comfort_areas", "image_url")

    op.alter_column(
        "ventor_interests",
        "custom_text",
        existing_type=sa.String(length=280),
        type_=sa.Text(),
        existing_nullable=True,
    )

    op.create_table(
        "ventor_languages",
        sa.Column("ventor_id", sa.UUID(), nullable=False),
        sa.Column("language_id", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ventor_id"], ["ventor_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ventor_id", "language_id"),
    )
    op.create_index("ix_ventor_languages_language_id", "ventor_languages", ["language_id"])

    languages = sa.table(
        "languages",
        sa.column("id", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_native", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("flag_url", sa.Text),
        sa.column("flag_emoji", sa.String),
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
                    name_native=row["name_native"],
                    name_ar=row["name_ar"],
                    flag_url=row["flag_url"],
                    flag_emoji=row["flag_emoji"],
                    sort_order=row["sort_order"],
                    is_active=True,
                )
            )
        else:
            bind.execute(
                languages.insert().values(
                    id=row["id"],
                    name_en=row["name_en"],
                    name_native=row["name_native"],
                    name_ar=row["name_ar"],
                    flag_url=row["flag_url"],
                    flag_emoji=row["flag_emoji"],
                    sort_order=row["sort_order"],
                    is_active=True,
                )
            )


def downgrade() -> None:
    op.drop_index("ix_ventor_languages_language_id", table_name="ventor_languages")
    op.drop_table("ventor_languages")

    op.alter_column(
        "ventor_interests",
        "custom_text",
        existing_type=sa.Text(),
        type_=sa.String(length=280),
        existing_nullable=True,
    )

    op.add_column("comfort_areas", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column(
        "comfort_areas",
        sa.Column("icon_key", sa.String(length=64), server_default="category", nullable=False),
    )
    op.execute("UPDATE comfort_areas SET image_url = icon_url")
    op.drop_column("comfort_areas", "icon_url")

    op.add_column("languages", sa.Column("image_url", sa.Text(), nullable=True))
    op.execute("UPDATE languages SET image_url = flag_url")
    op.drop_column("languages", "flag_emoji")
    op.drop_column("languages", "flag_url")
    op.drop_column("languages", "name_native")
