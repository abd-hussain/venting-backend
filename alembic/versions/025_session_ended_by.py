"""Add sessions.ended_by for call end attribution

Revision ID: 025_session_ended_by
Revises: 024_boundary_other
Create Date: 2026-08-28 01:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_session_ended_by"
down_revision: Union[str, Sequence[str], None] = "024_boundary_other"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("ended_by", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "ended_by")
