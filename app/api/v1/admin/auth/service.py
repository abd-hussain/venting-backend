"""Admin auth service — A1–A5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.auth.schemas import (
    AdminChangePasswordRequest,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutRequest,
    AdminMeResponse,
    AdminOkResponse,
    AdminRefreshRequest,
)
from app.api.v1.admin.deps import AdminPrincipal, _load_admin_permissions
from app.core.config import Settings
from app.core.errors import invalid_credentials, unauthorized
from app.core.security import (
    create_admin_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.admin import AdminRefreshToken, AdminRole, AdminUser
from app.models.enums import AdminStatus


def _me(admin: AdminUser, permissions: set[str], role_keys: list[str]) -> AdminMeResponse:
    return AdminMeResponse(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        status=admin.status.value if hasattr(admin.status, "value") else str(admin.status),
        mfa_enabled=admin.mfa_enabled,
        roles=role_keys,
        permissions=sorted(permissions),
        last_login_at=admin.last_login_at,
    )


def _issue_tokens(db: Session, admin: AdminUser, settings: Settings) -> tuple[str, str]:
    access = create_admin_access_token(admin_id=admin.id, settings=settings)
    refresh = generate_refresh_token()
    db.add(
        AdminRefreshToken(
            admin_user_id=admin.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return access, refresh


def _load_admin(db: Session, admin_id) -> AdminUser | None:
    return (
        db.query(AdminUser)
        .options(joinedload(AdminUser.roles).joinedload(AdminRole.permissions))
        .filter(AdminUser.id == admin_id)
        .one_or_none()
    )


def login_admin(
    db: Session, payload: AdminLoginRequest, settings: Settings
) -> AdminLoginResponse:
    admin = (
        db.query(AdminUser)
        .options(joinedload(AdminUser.roles).joinedload(AdminRole.permissions))
        .filter(AdminUser.email == payload.email)
        .one_or_none()
    )
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise invalid_credentials()
    if admin.status != AdminStatus.active:
        raise invalid_credentials()

    admin.last_login_at = datetime.now(timezone.utc)
    access, refresh = _issue_tokens(db, admin, settings)
    perms, roles = _load_admin_permissions(admin)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="admin.login",
        entity_type="admin_user",
        entity_id=admin.id,
    )
    db.commit()
    return AdminLoginResponse(
        access_token=access,
        refresh_token=refresh,
        admin=_me(admin, perms, roles),
    )


def refresh_admin_tokens(
    db: Session, payload: AdminRefreshRequest, settings: Settings
) -> AdminLoginResponse:
    stored = (
        db.query(AdminRefreshToken)
        .filter(AdminRefreshToken.token_hash == hash_token(payload.refresh_token))
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at <= now
    ):
        raise unauthorized()

    admin = _load_admin(db, stored.admin_user_id)
    if admin is None or admin.status != AdminStatus.active:
        raise unauthorized()

    stored.revoked_at = now
    access, refresh = _issue_tokens(db, admin, settings)
    perms, roles = _load_admin_permissions(admin)
    db.commit()
    return AdminLoginResponse(
        access_token=access,
        refresh_token=refresh,
        admin=_me(admin, perms, roles),
    )


def logout_admin(
    db: Session, admin: AdminPrincipal, payload: AdminLogoutRequest | None
) -> AdminOkResponse:
    now = datetime.now(timezone.utc)
    if payload and payload.refresh_token:
        stored = (
            db.query(AdminRefreshToken)
            .filter(
                AdminRefreshToken.admin_user_id == admin.id,
                AdminRefreshToken.token_hash == hash_token(payload.refresh_token),
                AdminRefreshToken.revoked_at.is_(None),
            )
            .one_or_none()
        )
        if stored is not None:
            stored.revoked_at = now
    else:
        (
            db.query(AdminRefreshToken)
            .filter(
                AdminRefreshToken.admin_user_id == admin.id,
                AdminRefreshToken.revoked_at.is_(None),
            )
            .update({AdminRefreshToken.revoked_at: now}, synchronize_session=False)
        )
    db.commit()
    return AdminOkResponse()


def get_admin_me(admin: AdminPrincipal) -> AdminMeResponse:
    return _me(admin.user, admin.permissions, admin.role_keys)


def change_admin_password(
    db: Session, admin: AdminPrincipal, payload: AdminChangePasswordRequest
) -> AdminOkResponse:
    if not verify_password(payload.current_password, admin.user.password_hash):
        raise invalid_credentials()
    admin.user.password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)
    (
        db.query(AdminRefreshToken)
        .filter(
            AdminRefreshToken.admin_user_id == admin.id,
            AdminRefreshToken.revoked_at.is_(None),
        )
        .update({AdminRefreshToken.revoked_at: now}, synchronize_session=False)
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="admin.change_password",
        entity_type="admin_user",
        entity_id=admin.id,
    )
    db.commit()
    return AdminOkResponse()
