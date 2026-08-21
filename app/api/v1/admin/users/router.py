"""Admin user directory routes — A12–A21."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from app.api.deps import DbSession
from app.api.v1.admin.deps import AdminPrincipal, require_permission
from app.api.v1.admin.users import service
from app.api.v1.admin.users.schemas import (
    ActionResponse,
    ListenerSummary,
    ModerationRequest,
    SuspendRequest,
    UserDossier,
    UserSummary,
    UserUpdateRequest,
    VentorDetail,
    VentorSummary,
)
from app.core.pagination import Paginated
from app.core.responses import success_response
from app.models.enums import ProfileStatus, UserRole
from app.schemas.envelope import APISuccessResponse

router = APIRouter(tags=["admin-users"])


@router.get("/users", response_model=APISuccessResponse[Paginated[UserSummary]])
def users(
    db: DbSession,
    role: UserRole | None = None,
    is_active: bool | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _: AdminPrincipal = Depends(require_permission("users:read")),
):
    return success_response(
        jsonable_encoder(
            service.list_users(
                db,
                role=role,
                is_active=is_active,
                q=q,
                page=page,
                page_size=page_size,
            )
        )
    )


@router.get("/users/{user_id}", response_model=APISuccessResponse[UserDossier])
def user_dossier(
    user_id: UUID,
    db: DbSession,
    _: AdminPrincipal = Depends(require_permission("users:read")),
):
    return success_response(jsonable_encoder(service.get_user_dossier(db, user_id)))


@router.patch("/users/{user_id}", response_model=APISuccessResponse[UserSummary])
def patch_user(
    user_id: UUID,
    body: UserUpdateRequest,
    db: DbSession,
    admin: AdminPrincipal = Depends(require_permission("users:write")),
):
    return success_response(
        jsonable_encoder(service.update_user(db, user_id, body, admin))
    )


@router.post(
    "/users/{user_id}/suspend",
    response_model=APISuccessResponse[ActionResponse],
)
def suspend(
    user_id: UUID,
    db: DbSession,
    body: SuspendRequest | None = None,
    admin: AdminPrincipal = Depends(require_permission("users:write")),
):
    return success_response(
        jsonable_encoder(
            service.suspend_user(db, user_id, body or SuspendRequest(), admin)
        )
    )


@router.post(
    "/users/{user_id}/unsuspend",
    response_model=APISuccessResponse[ActionResponse],
)
def unsuspend(
    user_id: UUID,
    db: DbSession,
    body: ModerationRequest | None = None,
    admin: AdminPrincipal = Depends(require_permission("users:write")),
):
    return success_response(
        jsonable_encoder(
            service.unsuspend_user(db, user_id, body or ModerationRequest(), admin)
        )
    )


@router.post(
    "/users/{user_id}/ban",
    response_model=APISuccessResponse[ActionResponse],
)
def ban(
    user_id: UUID,
    db: DbSession,
    body: ModerationRequest | None = None,
    admin: AdminPrincipal = Depends(require_permission("users:write")),
):
    return success_response(
        jsonable_encoder(
            service.ban_user(db, user_id, body or ModerationRequest(), admin)
        )
    )


@router.post(
    "/users/{user_id}/force-logout",
    response_model=APISuccessResponse[ActionResponse],
)
def force_logout(
    user_id: UUID,
    db: DbSession,
    body: ModerationRequest | None = None,
    admin: AdminPrincipal = Depends(require_permission("users:write")),
):
    return success_response(
        jsonable_encoder(
            service.force_logout(db, user_id, body or ModerationRequest(), admin)
        )
    )


@router.get("/ventors", response_model=APISuccessResponse[Paginated[VentorSummary]])
def ventors(
    db: DbSession,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _: AdminPrincipal = Depends(require_permission("users:read")),
):
    return success_response(
        jsonable_encoder(
            service.list_ventors(db, q=q, page=page, page_size=page_size)
        )
    )


@router.get("/ventors/{ventor_id}", response_model=APISuccessResponse[VentorDetail])
def ventor(
    ventor_id: UUID,
    db: DbSession,
    _: AdminPrincipal = Depends(require_permission("users:read")),
):
    return success_response(jsonable_encoder(service.get_ventor(db, ventor_id)))


@router.get(
    "/listeners",
    response_model=APISuccessResponse[Paginated[ListenerSummary]],
)
def listeners(
    db: DbSession,
    profile_status: ProfileStatus | None = None,
    page: int = 1,
    page_size: int = 20,
    _: AdminPrincipal = Depends(require_permission("users:read")),
):
    return success_response(
        jsonable_encoder(
            service.list_listeners(
                db,
                profile_status=profile_status,
                page=page,
                page_size=page_size,
            )
        )
    )
