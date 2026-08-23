"""reward_offers expires_at column

Revision ID: 007_reward_offer_expires_at
Revises: 006_ventor_favorites_listener_idx
Create Date: 2026-08-23 16:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_reward_offer_expires_at"
down_revision: Union[str, Sequence[str], None] = "006_ventor_favorites_listener_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reward_offers",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reward_offers", "expires_at")
