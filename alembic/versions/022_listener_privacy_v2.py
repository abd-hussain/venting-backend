"""Listener privacy settings v2 — profile_visible, drop per-field toggles

Revision ID: 022_listener_privacy_v2
Revises: 021_registration_progress
Create Date: 2026-08-27 22:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_listener_privacy_v2"
down_revision: Union[str, Sequence[str], None] = "021_registration_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_privacy_settings",
        sa.Column("profile_visible", sa.Boolean(), server_default="true", nullable=False),
    )
    op.drop_column("listener_privacy_settings", "show_languages")
    op.drop_column("listener_privacy_settings", "show_comfort_areas")
    op.drop_column("listener_privacy_settings", "show_experience_and_ratings")
    op.drop_column("listener_privacy_settings", "show_boundaries")
    op.alter_column(
        "listener_privacy_settings",
        "allow_search_indexing",
        server_default="true",
    )


def downgrade() -> None:
    op.alter_column(
        "listener_privacy_settings",
        "allow_search_indexing",
        server_default="false",
    )
    op.add_column(
        "listener_privacy_settings",
        sa.Column("show_boundaries", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "listener_privacy_settings",
        sa.Column(
            "show_experience_and_ratings",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "listener_privacy_settings",
        sa.Column("show_comfort_areas", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "listener_privacy_settings",
        sa.Column("show_languages", sa.Boolean(), server_default="true", nullable=False),
    )
    op.drop_column("listener_privacy_settings", "profile_visible")
