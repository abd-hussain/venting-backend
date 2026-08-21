from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, SettingsDep
from app.api.v1.auth.schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    OkResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.api.v1.auth.service import (
    change_password,
    delete_account,
    get_me,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[RegisterResponse],
    responses={
        409: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Register a new ventor or listener account",
)
def register(
    body: RegisterRequest,
    db: DbSession,
    settings: SettingsDep,
):
    data = register_user(db, body, settings)
    return success_response(data.model_dump(), status_code=status.HTTP_201_CREATED)


@router.post(
    "/login",
    response_model=APISuccessResponse[LoginResponse],
    responses={
        401: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Sign in with email, password, and role",
)
def login(
    body: LoginRequest,
    db: DbSession,
    settings: SettingsDep,
):
    data = login_user(db, body, settings)
    return success_response(data.model_dump())


@router.post(
    "/refresh",
    response_model=APISuccessResponse[RefreshResponse],
    responses={
        401: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Rotate refresh token and issue a new access token",
)
def refresh(
    body: RefreshRequest,
    db: DbSession,
    settings: SettingsDep,
):
    data = refresh_tokens(db, body, settings)
    return success_response(data.model_dump())


@router.post(
    "/logout",
    response_model=APISuccessResponse[OkResponse],
    responses={401: {"model": APIErrorResponse}},
    summary="Revoke refresh token(s) for the current user",
)
def logout(
    current_user: CurrentUser,
    db: DbSession,
    body: LogoutRequest | None = None,
):
    data = logout_user(db, current_user, body)
    return success_response(data.model_dump())


@router.delete(
    "/account",
    response_model=APISuccessResponse[OkResponse],
    responses={
        401: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Soft-delete the authenticated account",
)
def account_delete(
    current_user: CurrentUser,
    db: DbSession,
    body: DeleteAccountRequest | None = None,
):
    data = delete_account(db, current_user, body)
    return success_response(data.model_dump())


@router.post(
    "/change-password",
    response_model=APISuccessResponse[OkResponse],
    responses={
        401: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
    summary="Change password for the authenticated user",
)
def password_change(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    data = change_password(db, current_user, body)
    return success_response(data.model_dump())


@router.get(
    "/me",
    response_model=APISuccessResponse[MeResponse],
    responses={401: {"model": APIErrorResponse}},
    summary="Current user bootstrap profile",
)
def me(current_user: CurrentUser, db: DbSession):
    data = get_me(db, current_user)
    return success_response(data.model_dump())
