"""Store listener session_minutes array on availability settings

Revision ID: 026_availability_session_minutes
Revises: 025_session_ended_by
Create Date: 2026-08-28 16:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_availability_session_minutes"
down_revision: Union[str, Sequence[str], None] = "025_session_ended_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_availability_settings",
        sa.Column("session_minutes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE listener_availability_settings "
            "SET session_minutes = jsonb_build_array(session_length_minutes) "
            "WHERE session_length_minutes IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("listener_availability_settings", "session_minutes")
