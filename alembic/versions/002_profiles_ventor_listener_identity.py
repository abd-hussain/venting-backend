"""profiles: ventor_profiles, listener_profiles, listener_identity_verifications

Revision ID: 002_profiles
Revises: 001_auth
Create Date: 2026-08-20

Tables from docs/database-schema.md § 2. Profiles.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_profiles"
down_revision = "001_auth"
branch_labels = None
depends_on = None

gender = postgresql.ENUM(
    "male", "female", "prefer_not_to_say", name="gender", create_type=False
)
profile_status = postgresql.ENUM(
    "incomplete",
    "under_review",
    "approved",
    "rejected",
    name="profile_status",
    create_type=False,
)
setup_step_status = postgresql.ENUM(
    "done", "in_progress", "locked", name="setup_step_status", create_type=False
)
earnings_tier = postgresql.ENUM(
    "starter",
    "rising",
    "trusted",
    "expert",
    "elite",
    name="earnings_tier",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    gender.create(bind, checkfirst=True)
    profile_status.create(bind, checkfirst=True)
    setup_step_status.create(bind, checkfirst=True)
    earnings_tier.create(bind, checkfirst=True)

    op.create_table(
        "ventor_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nickname", sa.String(length=20), nullable=False),
        sa.Column("gender", gender, nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("quote", sa.String(length=280), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("points_balance", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_reward_offer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mood_streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_mood_checkin_date", sa.Date(), nullable=True),
        sa.Column(
            "completed_sessions_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "listener_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone_e164", sa.String(length=32), nullable=True),
        sa.Column("phone_country_iso", sa.String(length=2), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("about_me", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("country_iso", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=30), nullable=True),
        sa.Column("gender", gender, nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("voice_intro_url", sa.Text(), nullable=True),
        sa.Column("voice_intro_seconds", sa.Integer(), nullable=True),
        sa.Column("is_online", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "profile_status",
            profile_status,
            server_default="incomplete",
            nullable=False,
        ),
        sa.Column(
            "accept_instant_calls", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "session_length_minutes", sa.Integer(), server_default="30", nullable=False
        ),
        sa.Column(
            "break_length_minutes", sa.Integer(), server_default="15", nullable=False
        ),
        sa.Column("time_zone_id", sa.String(length=64), nullable=False),
        sa.Column(
            "rate_per_minute",
            sa.Numeric(precision=8, scale=2),
            server_default="0.25",
            nullable=False,
        ),
        sa.Column(
            "current_tier",
            earnings_tier,
            server_default="starter",
            nullable=False,
        ),
        sa.Column(
            "rating_avg",
            sa.Numeric(precision=3, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("session_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rating_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "setup_identity_status",
            setup_step_status,
            server_default="locked",
            nullable=False,
        ),
        sa.Column(
            "setup_profile_status",
            setup_step_status,
            server_default="locked",
            nullable=False,
        ),
        sa.Column(
            "setup_availability_status",
            setup_step_status,
            server_default="locked",
            nullable=False,
        ),
        sa.Column(
            "setup_training_status",
            setup_step_status,
            server_default="locked",
            nullable=False,
        ),
        sa.Column(
            "setup_tutorial_status",
            setup_step_status,
            server_default="locked",
            nullable=False,
        ),
        sa.Column("first_session_tutorial_acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agreed_to_terms_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_listener_profiles_online_status",
        "listener_profiles",
        ["is_online", "profile_status"],
        unique=False,
    )
    op.create_index(
        "ix_listener_profiles_rate_per_minute",
        "listener_profiles",
        ["rate_per_minute"],
        unique=False,
    )
    op.create_index(
        "ix_listener_profiles_rating_avg",
        "listener_profiles",
        ["rating_avg"],
        unique=False,
    )
    op.create_index(
        "ix_listener_profiles_country_iso",
        "listener_profiles",
        ["country_iso"],
        unique=False,
    )

    op.create_table(
        "listener_identity_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listener_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_front_url", sa.Text(), nullable=False),
        sa.Column("document_back_url", sa.Text(), nullable=True),
        sa.Column("selfie_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            profile_status,
            server_default="under_review",
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["listener_id"], ["listener_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listener_identity_verifications_listener_created",
        "listener_identity_verifications",
        ["listener_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_listener_identity_verifications_listener_created",
        table_name="listener_identity_verifications",
    )
    op.drop_table("listener_identity_verifications")
    op.drop_index("ix_listener_profiles_country_iso", table_name="listener_profiles")
    op.drop_index("ix_listener_profiles_rating_avg", table_name="listener_profiles")
    op.drop_index("ix_listener_profiles_rate_per_minute", table_name="listener_profiles")
    op.drop_index("ix_listener_profiles_online_status", table_name="listener_profiles")
    op.drop_table("listener_profiles")
    op.drop_table("ventor_profiles")

    bind = op.get_bind()
    earnings_tier.drop(bind, checkfirst=True)
    setup_step_status.drop(bind, checkfirst=True)
    profile_status.drop(bind, checkfirst=True)
    gender.drop(bind, checkfirst=True)
