"""Add book_first_session_acked_at on listener profiles

Revision ID: 029_book_first_session_ack
Revises: 028_listener_steps_refill
Create Date: 2026-08-29 02:06:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "029_book_first_session_ack"
down_revision: Union[str, Sequence[str], None] = "028_listener_steps_refill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_profiles",
        sa.Column("book_first_session_acked_at", sa.DateTime(timezone=True), nullable=True),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE listener_profiles "
            "SET book_first_session_acked_at = first_session_tutorial_acked_at "
            "WHERE first_session_tutorial_acked_at IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("listener_profiles", "book_first_session_acked_at")
