"""Auth business logic. Routers call this layer; it does not know about HTTP."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.api.v1.auth.schemas import (
    AuthRole,
    ChangePasswordRequest,
    CheckEmailRequest,
    CheckEmailResponse,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
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
    ResetPasswordRequest,
    ResetPasswordResponse,
    SocialAuthRequest,
    SocialAuthResponse,
    SocialAuthUser,
    SocialFullName,
)
from app.core.config import Settings
from app.core.errors import (
    account_disabled,
    auth_role_mismatch,
    email_already_registered,
    forgot_password_rate_limited,
    invalid_credentials,
    invalid_or_expired_reset_token,
    invalid_social_token,
    password_not_set,
    rate_limited,
    reset_password_rate_limited,
    social_account_disabled,
    social_email_unavailable,
    social_identity_conflict,
    social_nonce_mismatch,
    social_provider_unavailable,
    social_role_mismatch,
    unauthorized,
)
from app.core.rate_limit import (
    check_email_limiter,
    forgot_password_limiter,
    reset_password_limiter,
    social_auth_limiter,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth import AuthIdentity, PasswordResetToken, RefreshToken, User
from app.services.email import send_password_reset_email
from app.models.enums import AuthProvider, ProfileStatus, UserRole
from app.models.profiles import ListenerProfile, VentorProfile
from app.services.social_tokens import (
    InvalidSocialTokenError,
    NonceMismatchError,
    ProviderUnavailableError,
    verify_social_id_token,
)


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


def _assert_user_can_authenticate(user: User) -> None:
    now = datetime.now(timezone.utc)
    if user.deleted_at is not None:
        raise social_account_disabled()
    if not user.is_active or (
        user.suspended_until is not None and user.suspended_until > now
    ):
        raise social_account_disabled()


def _assert_role_matches(user: User, role: AuthRole) -> None:
    if user.role.value != role.value:
        raise social_role_mismatch()


def _apply_social_full_name(
    db: Session,
    user: User,
    full_name: SocialFullName | None,
) -> None:
    if full_name is None:
        return
    display = " ".join(
        part for part in (full_name.given_name, full_name.family_name) if part
    ).strip()
    if not display:
        return

    if user.role == UserRole.listener:
        profile = db.get(ListenerProfile, user.id)
        if profile is not None and not profile.full_name:
            profile.full_name = display
    elif user.role == UserRole.ventor:
        profile = db.get(VentorProfile, user.id)
        if profile is not None and not profile.nickname:
            profile.nickname = display[:20]


def _upsert_auth_identity(
    db: Session,
    *,
    user: User,
    provider: AuthProvider,
    provider_user_id: str,
    email: str | None,
    raw_profile: dict | None,
) -> AuthIdentity:
    identity = (
        db.query(AuthIdentity)
        .filter(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_user_id == provider_user_id,
        )
        .one_or_none()
    )
    if identity is None:
        existing_for_user = (
            db.query(AuthIdentity)
            .filter(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == provider,
            )
            .one_or_none()
        )
        if existing_for_user is not None:
            raise social_identity_conflict()

        identity = AuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            raw_profile=raw_profile,
        )
        db.add(identity)
    else:
        if identity.user_id != user.id:
            raise social_identity_conflict()
        identity.email = email or identity.email
        if raw_profile:
            identity.raw_profile = raw_profile

    return identity


def social_login(
    db: Session,
    payload: SocialAuthRequest,
    settings: Settings,
    *,
    client_ip: str | None = None,
    installation_id: str | None = None,
) -> SocialAuthResponse:
    if client_ip and not social_auth_limiter.allow(f"ip:{client_ip}"):
        raise rate_limited()
    if installation_id and not social_auth_limiter.allow(f"inst:{installation_id}"):
        raise rate_limited()

    provider = AuthProvider(payload.provider.value)
    try:
        verified = verify_social_id_token(
            provider=provider,
            id_token=payload.id_token,
            settings=settings,
            nonce=payload.nonce,
        )
    except NonceMismatchError:
        raise social_nonce_mismatch()
    except ProviderUnavailableError:
        raise social_provider_unavailable()
    except InvalidSocialTokenError:
        raise invalid_social_token()

    raw_profile: dict | None = None
    if payload.full_name is not None:
        raw_profile = {
            "full_name": payload.full_name.model_dump(exclude_none=True),
        }

    identity = (
        db.query(AuthIdentity)
        .filter(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_user_id == verified.provider_user_id,
        )
        .one_or_none()
    )

    is_new = False

    if identity is not None:
        user = db.get(User, identity.user_id)
        if user is None:
            raise invalid_social_token()
        _assert_user_can_authenticate(user)
        _assert_role_matches(user, payload.role)
        identity.email = verified.email or identity.email
        if raw_profile:
            merged = dict(identity.raw_profile or {})
            merged.update(raw_profile)
            identity.raw_profile = merged
        _apply_social_full_name(db, user, payload.full_name)
    else:
        user: User | None = None
        if verified.email:
            user = (
                db.query(User)
                .filter(User.email == verified.email)
                .one_or_none()
            )
            if user is not None:
                if user.deleted_at is not None:
                    raise social_account_disabled()
                _assert_user_can_authenticate(user)
                _assert_role_matches(user, payload.role)

                existing_provider = (
                    db.query(AuthIdentity)
                    .filter(
                        AuthIdentity.user_id == user.id,
                        AuthIdentity.provider == provider,
                    )
                    .one_or_none()
                )
                if (
                    existing_provider is not None
                    and existing_provider.provider_user_id != verified.provider_user_id
                ):
                    raise social_identity_conflict()

                _upsert_auth_identity(
                    db,
                    user=user,
                    provider=provider,
                    provider_user_id=verified.provider_user_id,
                    email=verified.email,
                    raw_profile=raw_profile,
                )
                _apply_social_full_name(db, user, payload.full_name)
        else:
            raise social_email_unavailable()

        if user is None:
            if not verified.email:
                raise social_email_unavailable()

            user = User(
                email=verified.email,
                password_hash=None,
                role=UserRole(payload.role.value),
                is_active=True,
                registration_complete=False,
            )
            db.add(user)
            db.flush()
            is_new = True

            _upsert_auth_identity(
                db,
                user=user,
                provider=provider,
                provider_user_id=verified.provider_user_id,
                email=verified.email,
                raw_profile=raw_profile,
            )
            _apply_social_full_name(db, user, payload.full_name)

    user.last_login_at = datetime.now(timezone.utc)
    access_token, refresh_token = _issue_tokens(db, user, settings)
    db.commit()
    db.refresh(user)

    return SocialAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=SocialAuthUser(
            id=str(user.id),
            email=user.email,
            role=payload.role,
            is_new=is_new,
            registration_complete=user.registration_complete,
        ),
    )


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
        or user.password_hash is None
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
        if user.password_hash is None or not verify_password(
            payload.password, user.password_hash
        ):
            raise invalid_credentials()

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    db.query(AuthIdentity).filter(AuthIdentity.user_id == user.id).delete(
        synchronize_session=False
    )
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return OkResponse(ok=True)


def change_password(
    db: Session,
    user: User,
    payload: ChangePasswordRequest,
) -> OkResponse:
    if user.password_hash is None:
        raise password_not_set()

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


PASSWORD_RESET_TTL = timedelta(minutes=60)


def request_password_reset(
    db: Session,
    payload: ForgotPasswordRequest,
    settings: Settings,
    *,
    client_ip: str | None = None,
) -> ForgotPasswordResponse:
    email = payload.email
    if client_ip and not forgot_password_limiter.allow(f"ip:{client_ip}"):
        raise forgot_password_rate_limited()
    if not forgot_password_limiter.allow(f"email:{email}"):
        raise forgot_password_rate_limited()

    locale = payload.locale.value
    response = ForgotPasswordResponse(email=email, sent=True)

    user = (
        db.query(User)
        .filter(User.email == email, User.deleted_at.is_(None))
        .one_or_none()
    )
    # Anti-enumeration: same response for unknown / wrong role / social-only.
    if (
        user is None
        or not user.is_active
        or user.role.value != payload.role.value
        or user.password_hash is None
    ):
        return response

    now = datetime.now(timezone.utc)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update(
        {PasswordResetToken.used_at: now},
        synchronize_session=False,
    )

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + PASSWORD_RESET_TTL,
            requested_ip=client_ip,
            locale=locale,
        )
    )
    db.commit()

    reset_url = (
        f"{settings.web_content_base_url.rstrip('/')}"
        f"/auth/{locale}/reset-password.html?token={raw_token}"
    )
    send_password_reset_email(
        settings=settings,
        to_email=user.email,
        locale=locale,
        reset_url=reset_url,
    )
    return response


def reset_password_with_token(
    db: Session,
    payload: ResetPasswordRequest,
    *,
    client_ip: str | None = None,
) -> ResetPasswordResponse:
    if client_ip and not reset_password_limiter.allow(f"ip:{client_ip}"):
        raise reset_password_rate_limited()

    token_hash = hash_token(payload.token.strip())
    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .one_or_none()
    )
    if (
        row is None
        or row.used_at is not None
        or row.expires_at <= now
    ):
        raise invalid_or_expired_reset_token()

    user = (
        db.query(User)
        .filter(User.id == row.user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None or not user.is_active:
        raise invalid_or_expired_reset_token()

    user.password_hash = hash_password(payload.password)
    row.used_at = now
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return ResetPasswordResponse(email=user.email, reset=True)
