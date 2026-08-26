"""Rename KYC doc to single identity_document_url

Revision ID: 020_identity_document
Revises: 019_registration_push
Create Date: 2026-08-26 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_identity_document"
down_revision: Union[str, Sequence[str], None] = "019_registration_push"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listener_identity_verifications",
        sa.Column("identity_document_url", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE listener_identity_verifications "
            "SET identity_document_url = document_front_url "
            "WHERE identity_document_url IS NULL"
        )
    )
    op.alter_column(
        "listener_identity_verifications",
        "identity_document_url",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("listener_identity_verifications", "document_front_url")
    op.drop_column("listener_identity_verifications", "document_back_url")


def downgrade() -> None:
    op.add_column(
        "listener_identity_verifications",
        sa.Column("document_front_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "listener_identity_verifications",
        sa.Column("document_back_url", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE listener_identity_verifications "
            "SET document_front_url = identity_document_url"
        )
    )
    op.alter_column(
        "listener_identity_verifications",
        "document_front_url",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("listener_identity_verifications", "identity_document_url")
