"""Add registration wizard progress columns on users

Revision ID: 021_registration_progress
Revises: 020_identity_document
Create Date: 2026-08-27 01:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_registration_progress"
down_revision: Union[str, Sequence[str], None] = "020_identity_document"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VENTOR_STEPS = '["profile","languages","interests","notifications"]'
LISTENER_STEPS = (
    '["profile","identity","about","experiences","comfort-areas",'
    '"boundaries","voice-intro","availability","notifications"]'
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "registration_completed_steps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "users",
        sa.Column("registration_next_step", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE users SET registration_completed_steps = '{VENTOR_STEPS}'::jsonb "
            "WHERE registration_complete = true AND role = 'ventor'"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE users SET registration_completed_steps = '{LISTENER_STEPS}'::jsonb "
            "WHERE registration_complete = true AND role = 'listener'"
        )
    )


def downgrade() -> None:
    op.drop_column("users", "registration_next_step")
    op.drop_column("users", "registration_completed_steps")
