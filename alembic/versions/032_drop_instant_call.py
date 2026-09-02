"""Drop instant call columns and enum value

Revision ID: 032_drop_instant_call
Revises: 031_point_packages
Create Date: 2026-09-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032_drop_instant_call"
down_revision: Union[str, Sequence[str], None] = "031_point_packages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE session_requests SET time_mode = 'nearest' "
        "WHERE time_mode::text = 'instant'"
    )
    op.execute(
        "UPDATE sessions SET time_mode = 'nearest' "
        "WHERE time_mode::text = 'instant'"
    )

    op.drop_index(
        "ix_session_requests_instant_status_created",
        table_name="session_requests",
    )
    op.drop_column("session_requests", "is_instant")
    op.drop_column("sessions", "is_instant")
    op.drop_column("listener_profiles", "accept_instant_calls")
    op.drop_column("listener_availability_settings", "accept_instant_calls")

    op.execute("ALTER TYPE session_time_mode RENAME TO session_time_mode_old")
    op.execute(
        "CREATE TYPE session_time_mode AS ENUM ('nearest', 'scheduled')"
    )
    op.execute(
        "ALTER TABLE session_requests "
        "ALTER COLUMN time_mode TYPE session_time_mode "
        "USING time_mode::text::session_time_mode"
    )
    op.execute(
        "ALTER TABLE sessions "
        "ALTER COLUMN time_mode TYPE session_time_mode "
        "USING time_mode::text::session_time_mode"
    )
    op.execute("DROP TYPE session_time_mode_old")

    op.execute(
        "DELETE FROM app_feature_flags WHERE key = 'instant_match_enabled'"
    )


def downgrade() -> None:
    op.execute("ALTER TYPE session_time_mode RENAME TO session_time_mode_old")
    op.execute(
        "CREATE TYPE session_time_mode AS ENUM ('instant', 'nearest', 'scheduled')"
    )
    op.execute(
        "ALTER TABLE session_requests "
        "ALTER COLUMN time_mode TYPE session_time_mode "
        "USING time_mode::text::session_time_mode"
    )
    op.execute(
        "ALTER TABLE sessions "
        "ALTER COLUMN time_mode TYPE session_time_mode "
        "USING time_mode::text::session_time_mode"
    )
    op.execute("DROP TYPE session_time_mode_old")

    op.add_column(
        "listener_availability_settings",
        sa.Column(
            "accept_instant_calls",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "listener_profiles",
        sa.Column(
            "accept_instant_calls",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "is_instant",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "session_requests",
        sa.Column(
            "is_instant",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_session_requests_instant_status_created",
        "session_requests",
        ["is_instant", "status", "created_at"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO app_feature_flags (id, key, description, enabled, audience, created_at, updated_at)
        SELECT gen_random_uuid(), 'instant_match_enabled',
               'Allow ventors to start instant match', true, 'ventor', now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM app_feature_flags WHERE key = 'instant_match_enabled'
        )
        """
    )
