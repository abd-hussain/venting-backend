"""Admin auth dependencies: CurrentAdmin + permission checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.api.deps import DbSession, SettingsDep
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_admin_access_token
from app.models.admin import AdminRole, AdminUser
from app.models.enums import AdminStatus

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AdminPrincipal:
    """Authenticated admin with resolved permission keys."""

    user: AdminUser
    permissions: set[str] = field(default_factory=set)
    role_keys: list[str] = field(default_factory=list)

    @property
    def id(self) -> UUID:
        return self.user.id

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def _load_admin_permissions(admin: AdminUser) -> tuple[set[str], list[str]]:
    perms: set[str] = set()
    role_keys: list[str] = []
    for role in admin.roles or []:
        role_keys.append(role.key)
        for perm in role.permissions or []:
            perms.add(perm.key)
    return perms, role_keys


def get_current_admin(
    db: DbSession,
    settings: SettingsDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
) -> AdminPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = decode_admin_access_token(credentials.credentials, settings)
        admin_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized() from None

    admin = (
        db.query(AdminUser)
        .options(
            joinedload(AdminUser.roles).joinedload(AdminRole.permissions),
        )
        .filter(AdminUser.id == admin_id)
        .one_or_none()
    )
    if admin is None or admin.status != AdminStatus.active:
        raise unauthorized()

    permissions, role_keys = _load_admin_permissions(admin)
    return AdminPrincipal(user=admin, permissions=permissions, role_keys=role_keys)


CurrentAdmin = Annotated[AdminPrincipal, Depends(get_current_admin)]


def require_permission(permission: str) -> Callable[..., AdminPrincipal]:
    def _checker(admin: CurrentAdmin) -> AdminPrincipal:
        if not admin.has(permission):
            raise forbidden()
        return admin

    return _checker


def require_any_permission(*permissions: str) -> Callable[..., AdminPrincipal]:
    def _checker(admin: CurrentAdmin) -> AdminPrincipal:
        if not any(admin.has(p) for p in permissions):
            raise forbidden()
        return admin

    return _checker
