"""Auth business logic. Routers call this layer; it does not know about HTTP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.api.v1.auth.schemas import (
    AuthRole,
    ChangePasswordRequest,
    CheckEmailRequest,
    CheckEmailResponse,
    DeleteAccountRequest,
    LoggedInUser,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    OkResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RegisteredUser,
)
from app.core.config import Settings
from app.core.errors import (
    account_disabled,
    auth_role_mismatch,
    email_already_registered,
    invalid_credentials,
    rate_limited,
    unauthorized,
)
from app.core.rate_limit import check_email_limiter
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth import RefreshToken, User
from app.models.enums import ProfileStatus, UserRole
from app.models.profiles import ListenerProfile, VentorProfile


def _issue_tokens(db: Session, user: User, settings: Settings) -> tuple[str, str]:
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        settings=settings,
    )
    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return access_token, refresh_token


def _revoke_refresh_token(db: Session, user_id, raw_token: str) -> None:
    stored = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
        )
        .one_or_none()
    )
    if stored is not None:
        stored.revoked_at = datetime.now(timezone.utc)


def _revoke_all_refresh_tokens(db: Session, user_id) -> None:
    now = datetime.now(timezone.utc)
    (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .update({RefreshToken.revoked_at: now}, synchronize_session=False)
    )


def _get_valid_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(raw_token))
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at <= now
    ):
        raise unauthorized()

    user = (
        db.query(User)
        .filter(User.id == stored.user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None or not user.is_active:
        raise unauthorized()

    return stored


def check_email(
    db: Session,
    payload: CheckEmailRequest,
    *,
    client_ip: str | None = None,
    installation_id: str | None = None,
) -> CheckEmailResponse:
    if client_ip and not check_email_limiter.allow(f"ip:{client_ip}"):
        raise rate_limited()
    if installation_id and not check_email_limiter.allow(f"inst:{installation_id}"):
        raise rate_limited()

    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or user.deleted_at is not None:
        return CheckEmailResponse(
            exists=False,
            email=payload.email,
        )

    now = datetime.now(timezone.utc)
    if not user.is_active or (
        user.suspended_until is not None and user.suspended_until > now
    ):
        raise account_disabled()

    role = AuthRole(user.role.value)
    if payload.role is not None and payload.role != role:
        raise auth_role_mismatch()

    listener_profile_status: str | None = None
    if user.role == UserRole.listener:
        profile = db.get(ListenerProfile, user.id)
        listener_profile_status = (
            profile.profile_status.value
            if profile is not None
            else ProfileStatus.incomplete.value
        )

    return CheckEmailResponse(
        exists=True,
        email=payload.email,
        role=role,
        registration_complete=user.registration_complete,
        listener_profile_status=listener_profile_status,
    )


def register_user(
    db: Session,
    payload: RegisterRequest,
    settings: Settings,
) -> RegisterResponse:
    existing = (
        db.query(User)
        .filter(User.email == payload.email, User.deleted_at.is_(None))
        .one_or_none()
    )
    if existing is not None:
        raise email_already_registered()

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole(payload.role.value),
        is_active=True,
        registration_complete=False,
    )
    db.add(user)
    db.flush()

    access_token, refresh_token = _issue_tokens(db, user, settings)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=RegisteredUser(
            id=str(user.id),
            email=user.email,
            role=payload.role,
            is_new=True,
        ),
    )


def login_user(
    db: Session,
    payload: LoginRequest,
    settings: Settings,
) -> LoginResponse:
    user = (
        db.query(User)
        .filter(User.email == payload.email, User.deleted_at.is_(None))
        .one_or_none()
    )
    if (
        user is None
        or not user.is_active
        or user.role.value != payload.role.value
        or not verify_password(payload.password, user.password_hash)
    ):
        raise invalid_credentials()

    user.last_login_at = datetime.now(timezone.utc)
    access_token, refresh_token = _issue_tokens(db, user, settings)
    db.commit()
    db.refresh(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=LoggedInUser(
            id=str(user.id),
            email=user.email,
            role=payload.role,
            registration_complete=user.registration_complete,
        ),
    )


def refresh_tokens(
    db: Session,
    payload: RefreshRequest,
    settings: Settings,
) -> RefreshResponse:
    stored = _get_valid_refresh_token(db, payload.refresh_token)
    user = stored.user

    stored.revoked_at = datetime.now(timezone.utc)
    access_token, refresh_token = _issue_tokens(db, user, settings)
    db.commit()

    return RefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def logout_user(
    db: Session,
    user: User,
    payload: LogoutRequest | None = None,
) -> OkResponse:
    if payload and payload.refresh_token:
        _revoke_refresh_token(db, user.id, payload.refresh_token)
    else:
        _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return OkResponse(ok=True)


def delete_account(
    db: Session,
    user: User,
    payload: DeleteAccountRequest | None = None,
) -> OkResponse:
    if payload and payload.password is not None:
        if not verify_password(payload.password, user.password_hash):
            raise invalid_credentials()

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return OkResponse(ok=True)


def change_password(
    db: Session,
    user: User,
    payload: ChangePasswordRequest,
) -> OkResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise invalid_credentials()

    user.password_hash = hash_password(payload.new_password)
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return OkResponse(ok=True)


def get_me(db: Session, user: User) -> MeResponse:
    display_name: str | None = None
    avatar_url: str | None = None
    listener_profile_status: str | None = None

    if user.role == UserRole.ventor:
        profile = (
            db.query(VentorProfile)
            .filter(VentorProfile.user_id == user.id)
            .one_or_none()
        )
        if profile is not None:
            display_name = profile.nickname
            avatar_url = profile.avatar_url
    else:
        profile = (
            db.query(ListenerProfile)
            .filter(ListenerProfile.user_id == user.id)
            .one_or_none()
        )
        if profile is not None:
            display_name = profile.full_name
            avatar_url = profile.avatar_url
            listener_profile_status = profile.profile_status.value
        else:
            listener_profile_status = ProfileStatus.incomplete.value

    return MeResponse(
        id=str(user.id),
        email=user.email,
        role=AuthRole(user.role.value),
        display_name=display_name,
        avatar_url=avatar_url,
        registration_complete=user.registration_complete,
        listener_profile_status=listener_profile_status,
    )
