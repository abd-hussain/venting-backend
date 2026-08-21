import secrets
import string
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.staff.schemas import (
    PermissionResponse,
    ResetPasswordRequest,
    RolePermissionsRequest,
    RoleResponse,
    StaffInviteRequest,
    StaffInviteResponse,
    StaffOkResponse,
    StaffResponse,
    StaffUpdateRequest,
)
from app.core.errors import conflict, not_found, validation_error
from app.core.security import hash_password
from app.models.admin import (
    AdminPermission,
    AdminRefreshToken,
    AdminRole,
    AdminUser,
)
from app.models.enums import AdminStatus


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _staff(row: AdminUser) -> StaffResponse:
    return StaffResponse(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        status=_value(row.status),
        role_keys=sorted(role.key for role in row.roles),
        mfa_enabled=row.mfa_enabled,
        last_login_at=row.last_login_at,
        created_at=row.created_at,
    )


def _role(row: AdminRole) -> RoleResponse:
    return RoleResponse(
        id=row.id,
        key=row.key,
        name=row.name,
        description=row.description,
        permission_keys=sorted(permission.key for permission in row.permissions),
    )


def _roles_by_keys(db: Session, role_keys: list[str]) -> list[AdminRole]:
    keys = set(role_keys)
    roles = db.query(AdminRole).filter(AdminRole.key.in_(keys)).all() if keys else []
    found = {role.key for role in roles}
    missing = sorted(keys - found)
    if missing:
        raise validation_error(f"Unknown role keys: {', '.join(missing)}")
    return roles


def _permissions_by_keys(
    db: Session, permission_keys: list[str]
) -> list[AdminPermission]:
    keys = set(permission_keys)
    permissions = (
        db.query(AdminPermission).filter(AdminPermission.key.in_(keys)).all()
        if keys
        else []
    )
    found = {permission.key for permission in permissions}
    missing = sorted(keys - found)
    if missing:
        raise validation_error(f"Unknown permission keys: {', '.join(missing)}")
    return permissions


def _temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.digits)
        + "".join(secrets.choice(alphabet) for _ in range(14))
    )


def list_staff(db: Session) -> list[StaffResponse]:
    rows = (
        db.query(AdminUser)
        .options(joinedload(AdminUser.roles))
        .order_by(AdminUser.created_at.desc())
        .all()
    )
    return [_staff(row) for row in rows]


def invite_staff(
    db: Session, payload: StaffInviteRequest, admin: AdminPrincipal
) -> StaffInviteResponse:
    if db.query(AdminUser.id).filter(AdminUser.email == payload.email).first():
        raise conflict("An admin account with this email already exists")
    roles = _roles_by_keys(db, payload.role_keys)
    password = payload.temporary_password or _temporary_password()
    row = AdminUser(
        email=str(payload.email),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(password),
        status=AdminStatus.invited,
        roles=roles,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="admin.invite",
        entity_type="admin_user",
        entity_id=row.id,
        after={"email": row.email, "role_keys": sorted(payload.role_keys)},
    )
    db.commit()
    db.refresh(row)
    return StaffInviteResponse(
        **_staff(row).model_dump(),
        temporary_password=password,
    )


def update_staff(
    db: Session,
    staff_id: UUID,
    payload: StaffUpdateRequest,
    admin: AdminPrincipal,
) -> StaffResponse:
    row = (
        db.query(AdminUser)
        .options(joinedload(AdminUser.roles))
        .filter(AdminUser.id == staff_id)
        .one_or_none()
    )
    if row is None:
        raise not_found("Admin user")
    before = {"status": _value(row.status), "role_keys": sorted(r.key for r in row.roles)}
    if payload.role_keys is not None:
        row.roles = _roles_by_keys(db, payload.role_keys)
    if payload.status is not None:
        row.status = payload.status
        if payload.status == AdminStatus.disabled:
            row.disabled_at = datetime.now(timezone.utc)
            (
                db.query(AdminRefreshToken)
                .filter(
                    AdminRefreshToken.admin_user_id == row.id,
                    AdminRefreshToken.revoked_at.is_(None),
                )
                .update(
                    {AdminRefreshToken.revoked_at: datetime.now(timezone.utc)},
                    synchronize_session=False,
                )
            )
        else:
            row.disabled_at = None
    after = {"status": _value(row.status), "role_keys": sorted(r.key for r in row.roles)}
    write_audit(
        db,
        admin_user_id=admin.id,
        action="admin.update",
        entity_type="admin_user",
        entity_id=row.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(row)
    return _staff(row)


def list_roles(db: Session) -> list[RoleResponse]:
    rows = (
        db.query(AdminRole)
        .options(joinedload(AdminRole.permissions))
        .order_by(AdminRole.key)
        .all()
    )
    return [_role(row) for row in rows]


def replace_role_permissions(
    db: Session, role_id: UUID, payload: RolePermissionsRequest
) -> RoleResponse:
    row = (
        db.query(AdminRole)
        .options(joinedload(AdminRole.permissions))
        .filter(AdminRole.id == role_id)
        .one_or_none()
    )
    if row is None:
        raise not_found("Admin role")
    row.permissions = _permissions_by_keys(db, payload.permission_keys)
    db.commit()
    db.refresh(row)
    return _role(row)


def list_permissions(db: Session) -> list[PermissionResponse]:
    return [
        PermissionResponse(id=row.id, key=row.key, description=row.description)
        for row in db.query(AdminPermission).order_by(AdminPermission.key).all()
    ]


def reset_password(
    db: Session,
    staff_id: UUID,
    payload: ResetPasswordRequest,
    admin: AdminPrincipal,
) -> StaffOkResponse:
    row = db.get(AdminUser, staff_id)
    if row is None:
        raise not_found("Admin user")
    row.password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)
    (
        db.query(AdminRefreshToken)
        .filter(
            AdminRefreshToken.admin_user_id == row.id,
            AdminRefreshToken.revoked_at.is_(None),
        )
        .update({AdminRefreshToken.revoked_at: now}, synchronize_session=False)
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="admin.reset_password",
        entity_type="admin_user",
        entity_id=row.id,
    )
    db.commit()
    return StaffOkResponse()
