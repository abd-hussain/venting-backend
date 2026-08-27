"""Add listener relationship_status and family_role_ids

Revision ID: 023_listener_experience_enums
Revises: 022_listener_privacy_v2
Create Date: 2026-08-28 00:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_listener_experience_enums"
down_revision: Union[str, Sequence[str], None] = "022_listener_privacy_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_profiles",
        sa.Column("relationship_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "listener_profiles",
        sa.Column(
            "family_role_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("listener_profiles", "family_role_ids")
    op.drop_column("listener_profiles", "relationship_status")
