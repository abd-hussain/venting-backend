"""ventor_favorites listener_id index

Revision ID: 006_ventor_favorites_listener_idx
Revises: 005_catalog_image_url
Create Date: 2026-08-23 16:45:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_ventor_favorites_listener_idx"
down_revision: Union[str, Sequence[str], None] = "005_catalog_image_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_ventor_favorites_listener_id",
        "ventor_favorites",
        ["listener_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ventor_favorites_listener_id", table_name="ventor_favorites")
