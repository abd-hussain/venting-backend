"""catalog lookup image_url columns

Revision ID: 005_catalog_image_url
Revises: 004_admin_refresh
Create Date: 2026-08-23 16:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_catalog_image_url"
down_revision: Union[str, Sequence[str], None] = "004_admin_refresh"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("languages", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("comfort_areas", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("life_experiences", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("boundaries", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("boundaries", "image_url")
    op.drop_column("life_experiences", "image_url")
    op.drop_column("comfort_areas", "image_url")
    op.drop_column("languages", "image_url")
