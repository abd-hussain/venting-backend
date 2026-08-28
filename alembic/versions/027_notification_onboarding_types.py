"""Add onboarding notification types

Revision ID: 027_notification_onboarding_types
Revises: 026_availability_session_minutes
Create Date: 2026-08-28 17:40:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "027_notification_onboarding_types"
down_revision: Union[str, Sequence[str], None] = "026_availability_session_minutes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_VALUES = ("welcome", "complete_registration", "book_first_session")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE notification_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    pass
