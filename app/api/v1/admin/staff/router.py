from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.deps import AdminPrincipal, require_permission
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
from app.api.v1.admin.staff.service import (
    invite_staff,
    list_permissions,
    list_roles,
    list_staff,
    replace_role_permissions,
    reset_password,
    update_staff,
)
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(tags=["admin-staff"])
AdminManager = Annotated[
    AdminPrincipal, Depends(require_permission("admins:manage"))
]


@router.get("/staff", response_model=APISuccessResponse[list[StaffResponse]])
def staff_list(db: DbSession, _admin: AdminManager):
    return success_response([row.model_dump(mode="json") for row in list_staff(db)])


@router.post("/staff", response_model=APISuccessResponse[StaffInviteResponse])
def staff_invite(body: StaffInviteRequest, db: DbSession, admin: AdminManager):
    return success_response(invite_staff(db, body, admin).model_dump(mode="json"))


@router.patch(
    "/staff/{staff_id}", response_model=APISuccessResponse[StaffResponse]
)
def staff_update(
    staff_id: UUID, body: StaffUpdateRequest, db: DbSession, admin: AdminManager
):
    return success_response(
        update_staff(db, staff_id, body, admin).model_dump(mode="json")
    )


@router.get("/roles", response_model=APISuccessResponse[list[RoleResponse]])
def roles(db: DbSession, _admin: AdminManager):
    return success_response([row.model_dump(mode="json") for row in list_roles(db)])


@router.put(
    "/roles/{role_id}/permissions", response_model=APISuccessResponse[RoleResponse]
)
def role_permissions_replace(
    role_id: UUID,
    body: RolePermissionsRequest,
    db: DbSession,
    _admin: AdminManager,
):
    return success_response(
        replace_role_permissions(db, role_id, body).model_dump(mode="json")
    )


@router.get(
    "/permissions", response_model=APISuccessResponse[list[PermissionResponse]]
)
def permissions(db: DbSession, _admin: AdminManager):
    return success_response(
        [row.model_dump(mode="json") for row in list_permissions(db)]
    )


@router.post(
    "/staff/{staff_id}/reset-password",
    response_model=APISuccessResponse[StaffOkResponse],
)
def staff_reset_password(
    staff_id: UUID,
    body: ResetPasswordRequest,
    db: DbSession,
    admin: AdminManager,
):
    return success_response(
        reset_password(db, staff_id, body, admin).model_dump(mode="json")
    )
