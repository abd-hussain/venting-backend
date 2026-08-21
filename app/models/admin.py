"""Admin portal / CMS tables — docs/admin-portal-cms.md § 4–5.

Tables 44–55:
  - admin_users, admin_roles, admin_user_roles
  - admin_permissions, admin_role_permissions
  - admin_audit_logs, admin_notes
  - app_feature_flags, app_config_kv
  - cms_pages, cms_banners
  - moderation_actions
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AdminStatus,
    BannerPlacement,
    CmsPageStatus,
    ModerationActionType,
)


class AdminUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "admin_users"

    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    status = Column(
        Enum(AdminStatus, name="admin_status", create_type=False),
        nullable=False,
        server_default="invited",
    )
    mfa_enabled = Column(Boolean, nullable=False, server_default="false")
    mfa_secret_encrypted = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    disabled_at = Column(DateTime(timezone=True), nullable=True)

    roles = relationship(
        "AdminRole",
        secondary="admin_user_roles",
        back_populates="users",
    )


class AdminRole(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "admin_roles"

    key = Column(String(64), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    users = relationship(
        "AdminUser",
        secondary="admin_user_roles",
        back_populates="roles",
    )
    permissions = relationship(
        "AdminPermission",
        secondary="admin_role_permissions",
        back_populates="roles",
    )


class AdminPermission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "admin_permissions"

    key = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    roles = relationship(
        "AdminRole",
        secondary="admin_role_permissions",
        back_populates="permissions",
    )


class AdminUserRole(Base):
    __tablename__ = "admin_user_roles"

    admin_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class AdminRolePermission(Base):
    __tablename__ = "admin_role_permissions"

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class AdminAuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "admin_audit_logs"

    admin_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    ip = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_admin_audit_logs_created_at", "created_at"),
        Index("ix_admin_audit_logs_admin_user_id", "admin_user_id"),
        Index("ix_admin_audit_logs_entity", "entity_type", "entity_id"),
    )


class AdminNote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "admin_notes"

    admin_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    body = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_admin_notes_entity", "entity_type", "entity_id"),
    )


class AppFeatureFlag(Base):
    __tablename__ = "app_feature_flags"

    key = Column(String(64), primary_key=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, server_default="false")
    rollout_percent = Column(Integer, nullable=False, server_default="100")
    audience = Column(String(32), nullable=False, server_default="all")
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AppConfigKv(Base):
    __tablename__ = "app_config_kv"

    key = Column(String(64), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CmsPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cms_pages"

    slug = Column(String(120), nullable=False)
    title = Column(String(200), nullable=False)
    locale = Column(String(8), nullable=False, server_default="en")
    body_markdown = Column(Text, nullable=False, server_default="")
    status = Column(
        Enum(CmsPageStatus, name="cms_page_status", create_type=False),
        nullable=False,
        server_default="draft",
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("slug", "locale", name="uq_cms_pages_slug_locale"),
    )


class CmsBanner(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "cms_banners"

    title = Column(String(120), nullable=False)
    body = Column(Text, nullable=False)
    cta_label = Column(String(64), nullable=True)
    cta_url = Column(Text, nullable=True)
    placement = Column(
        Enum(
            BannerPlacement,
            name="banner_placement",
            create_type=False,
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
    )
    audience = Column(String(32), nullable=False, server_default="all")
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_cms_banners_placement_active", "placement", "is_active"),
    )


class ModerationAction(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "moderation_actions"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action = Column(
        Enum(ModerationActionType, name="moderation_action_type", create_type=False),
        nullable=False,
    )
    reason = Column(Text, nullable=False)
    starts_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ends_at = Column(DateTime(timezone=True), nullable=True)
    related_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_moderation_actions_user_id", "user_id"),
        Index("ix_moderation_actions_created_at", "created_at"),
    )
