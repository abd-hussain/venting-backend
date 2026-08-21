"""admin portal cms tables 44-55

Revision ID: 003_admin_cms
Revises: 2b5cc45b943b
Create Date: 2026-08-21 15:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_admin_cms"
down_revision: Union[str, Sequence[str], None] = "2b5cc45b943b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_ROLES = [
    ("super_admin", "Super Admin", "Full access to the admin portal"),
    ("ops", "Operations", "Approvals, users, sessions, reports"),
    ("support", "Support", "Users read, notes, limited suspend"),
    ("finance", "Finance", "Payouts, wallet adjustments, earnings"),
    ("content", "Content", "Catalogs, CMS pages, banners, training"),
    ("analyst", "Analyst", "Dashboard and analytics (read-only)"),
]

ADMIN_PERMISSIONS = [
    ("users:read", "View mobile users"),
    ("users:write", "Update / suspend / ban users"),
    ("listeners:approve", "Approve or reject listeners"),
    ("identity:read", "View identity documents"),
    ("sessions:write", "Cancel / refund sessions"),
    ("reports:triage", "Triage session reports"),
    ("payouts:approve", "Approve or reject payouts"),
    ("wallet:adjust", "Adjust listener wallets"),
    ("catalogs:write", "Manage lookup catalogs"),
    ("rewards:write", "Manage reward offers"),
    ("promo:write", "Manage promo codes"),
    ("cms:write", "Manage CMS pages and banners"),
    ("config:write", "Manage feature flags and config"),
    ("admins:manage", "Manage admin users and roles"),
    ("audit:read", "View audit logs"),
    ("analytics:read", "View analytics and dashboards"),
]

# role_key -> permission keys
ROLE_PERMISSIONS = {
    "super_admin": [p[0] for p in ADMIN_PERMISSIONS],
    "ops": [
        "users:read",
        "users:write",
        "listeners:approve",
        "identity:read",
        "sessions:write",
        "reports:triage",
        "audit:read",
        "analytics:read",
    ],
    "support": [
        "users:read",
        "users:write",
        "identity:read",
        "reports:triage",
        "audit:read",
    ],
    "finance": [
        "users:read",
        "payouts:approve",
        "wallet:adjust",
        "analytics:read",
        "audit:read",
    ],
    "content": [
        "catalogs:write",
        "rewards:write",
        "promo:write",
        "cms:write",
        "config:write",
    ],
    "analyst": [
        "users:read",
        "analytics:read",
        "audit:read",
    ],
}


def upgrade() -> None:
    bind = op.get_bind()
    new_enums = [
        ("admin_status", ("active", "invited", "disabled")),
        (
            "moderation_action_type",
            ("warn", "suspend", "unsuspend", "ban", "unban", "force_logout"),
        ),
        ("review_decision", ("approved", "rejected", "needs_more_info")),
        ("cms_page_status", ("draft", "published", "archived")),
        (
            "banner_placement",
            ("ventor_home", "listener_home", "checkout", "global"),
        ),
    ]
    for name, values in new_enums:
        postgresql.ENUM(*values, name=name, create_type=False).create(
            bind, checkfirst=True
        )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "invited", "disabled", name="admin_status", create_type=False
            ),
            server_default="invited",
            nullable=False,
        ),
        sa.Column("mfa_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "admin_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "admin_permissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "admin_user_roles",
        sa.Column("admin_user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["admin_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("admin_user_id", "role_id"),
    )

    op.create_table(
        "admin_role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["admin_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["admin_permissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"]
    )
    op.create_index(
        "ix_admin_audit_logs_admin_user_id", "admin_audit_logs", ["admin_user_id"]
    )
    op.create_index(
        "ix_admin_audit_logs_entity",
        "admin_audit_logs",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "admin_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_notes_entity", "admin_notes", ["entity_type", "entity_id"]
    )

    op.create_table(
        "app_feature_flags",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rollout_percent", sa.Integer(), server_default="100", nullable=False),
        sa.Column("audience", sa.String(length=32), server_default="all", nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["admin_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "app_config_kv",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["admin_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "cms_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("body_markdown", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "published",
                "archived",
                name="cms_page_status",
                create_type=False,
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["updated_by"], ["admin_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "locale", name="uq_cms_pages_slug_locale"),
    )

    op.create_table(
        "cms_banners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cta_label", sa.String(length=64), nullable=True),
        sa.Column("cta_url", sa.Text(), nullable=True),
        sa.Column(
            "placement",
            postgresql.ENUM(
                "ventor_home",
                "listener_home",
                "checkout",
                "global",
                name="banner_placement",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("audience", sa.String(length=32), server_default="all", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cms_banners_placement_active",
        "cms_banners",
        ["placement", "is_active"],
    )

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(
                "warn",
                "suspend",
                "unsuspend",
                "ban",
                "unban",
                "force_logout",
                name="moderation_action_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_report_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["related_report_id"], ["session_reports.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_moderation_actions_user_id", "moderation_actions", ["user_id"]
    )
    op.create_index(
        "ix_moderation_actions_created_at", "moderation_actions", ["created_at"]
    )

    # Recommended columns on existing mobile tables
    op.add_column(
        "users",
        sa.Column("suspended_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "listener_profiles",
        sa.Column("reviewed_by_admin_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "listener_profiles",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "listener_profiles",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_listener_profiles_reviewed_by_admin_id",
        "listener_profiles",
        "admin_users",
        ["reviewed_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "listener_identity_verifications",
        sa.Column("reviewed_by_admin_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_listener_identity_reviewed_by_admin_id",
        "listener_identity_verifications",
        "admin_users",
        ["reviewed_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "session_reports",
        sa.Column("assigned_admin_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "session_reports",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "session_reports",
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_session_reports_assigned_admin_id",
        "session_reports",
        "admin_users",
        ["assigned_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "payouts",
        sa.Column("reviewed_by_admin_id", sa.UUID(), nullable=True),
    )
    op.add_column("payouts", sa.Column("admin_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_payouts_reviewed_by_admin_id",
        "payouts",
        "admin_users",
        ["reviewed_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Seed RBAC
    connection = op.get_bind()
    for key, name, description in ADMIN_ROLES:
        connection.execute(
            sa.text(
                "INSERT INTO admin_roles (id, key, name, description) "
                "VALUES (gen_random_uuid(), :key, :name, :description)"
            ),
            {"key": key, "name": name, "description": description},
        )
    for key, description in ADMIN_PERMISSIONS:
        connection.execute(
            sa.text(
                "INSERT INTO admin_permissions (id, key, description) "
                "VALUES (gen_random_uuid(), :key, :description)"
            ),
            {"key": key, "description": description},
        )
    for role_key, perm_keys in ROLE_PERMISSIONS.items():
        for perm_key in perm_keys:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO admin_role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM admin_roles r, admin_permissions p
                    WHERE r.key = :role_key AND p.key = :perm_key
                    """
                ),
                {"role_key": role_key, "perm_key": perm_key},
            )


def downgrade() -> None:
    op.drop_constraint("fk_payouts_reviewed_by_admin_id", "payouts", type_="foreignkey")
    op.drop_column("payouts", "admin_note")
    op.drop_column("payouts", "reviewed_by_admin_id")

    op.drop_constraint(
        "fk_session_reports_assigned_admin_id", "session_reports", type_="foreignkey"
    )
    op.drop_column("session_reports", "resolution_note")
    op.drop_column("session_reports", "resolved_at")
    op.drop_column("session_reports", "assigned_admin_id")

    op.drop_constraint(
        "fk_listener_identity_reviewed_by_admin_id",
        "listener_identity_verifications",
        type_="foreignkey",
    )
    op.drop_column("listener_identity_verifications", "reviewed_by_admin_id")

    op.drop_constraint(
        "fk_listener_profiles_reviewed_by_admin_id",
        "listener_profiles",
        type_="foreignkey",
    )
    op.drop_column("listener_profiles", "rejection_reason")
    op.drop_column("listener_profiles", "reviewed_at")
    op.drop_column("listener_profiles", "reviewed_by_admin_id")

    op.drop_column("users", "suspended_until")

    op.drop_index("ix_moderation_actions_created_at", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_user_id", table_name="moderation_actions")
    op.drop_table("moderation_actions")

    op.drop_index("ix_cms_banners_placement_active", table_name="cms_banners")
    op.drop_table("cms_banners")
    op.drop_table("cms_pages")
    op.drop_table("app_config_kv")
    op.drop_table("app_feature_flags")
    op.drop_index("ix_admin_notes_entity", table_name="admin_notes")
    op.drop_table("admin_notes")
    op.drop_index("ix_admin_audit_logs_entity", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_user_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_table("admin_role_permissions")
    op.drop_table("admin_user_roles")
    op.drop_table("admin_permissions")
    op.drop_table("admin_roles")
    op.drop_table("admin_users")

    bind = op.get_bind()
    for name in (
        "banner_placement",
        "cms_page_status",
        "review_decision",
        "moderation_action_type",
        "admin_status",
    ):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
