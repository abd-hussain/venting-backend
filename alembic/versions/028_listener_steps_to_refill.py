"""Add listener steps_to_refill for profile reject flow

Revision ID: 028_listener_steps_refill
Revises: 027_onboarding_notif_types
Create Date: 2026-08-28 23:58:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028_listener_steps_refill"
down_revision: Union[str, Sequence[str], None] = "027_onboarding_notif_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_profiles",
        sa.Column(
            "steps_to_refill",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("listener_profiles", "steps_to_refill")
