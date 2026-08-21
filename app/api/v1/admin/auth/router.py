from fastapi import APIRouter

from app.api.deps import DbSession, SettingsDep
from app.api.v1.admin.auth.schemas import (
    AdminChangePasswordRequest,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutRequest,
    AdminMeResponse,
    AdminOkResponse,
    AdminRefreshRequest,
)
from app.api.v1.admin.auth.service import (
    change_admin_password,
    get_admin_me,
    login_admin,
    logout_admin,
    refresh_admin_tokens,
)
from app.api.v1.admin.deps import CurrentAdmin
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(prefix="/auth", tags=["admin-auth"])


@router.post(
    "/login",
    response_model=APISuccessResponse[AdminLoginResponse],
    responses={401: {"model": APIErrorResponse}},
)
def login(body: AdminLoginRequest, db: DbSession, settings: SettingsDep):
    return success_response(login_admin(db, body, settings).model_dump(mode="json"))


@router.post(
    "/refresh",
    response_model=APISuccessResponse[AdminLoginResponse],
    responses={401: {"model": APIErrorResponse}},
)
def refresh(body: AdminRefreshRequest, db: DbSession, settings: SettingsDep):
    return success_response(
        refresh_admin_tokens(db, body, settings).model_dump(mode="json")
    )


@router.post(
    "/logout",
    response_model=APISuccessResponse[AdminOkResponse],
    responses={401: {"model": APIErrorResponse}},
)
def logout(
    admin: CurrentAdmin,
    db: DbSession,
    body: AdminLogoutRequest | None = None,
):
    return success_response(logout_admin(db, admin, body).model_dump(mode="json"))


@router.get(
    "/me",
    response_model=APISuccessResponse[AdminMeResponse],
    responses={401: {"model": APIErrorResponse}},
)
def me(admin: CurrentAdmin):
    return success_response(get_admin_me(admin).model_dump(mode="json"))


@router.post(
    "/change-password",
    response_model=APISuccessResponse[AdminOkResponse],
    responses={401: {"model": APIErrorResponse}},
)
def change_password(
    body: AdminChangePasswordRequest,
    admin: CurrentAdmin,
    db: DbSession,
):
    return success_response(
        change_admin_password(db, admin, body).model_dump(mode="json")
    )