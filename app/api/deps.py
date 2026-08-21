"""Shared FastAPI dependencies (auth, db session, headers, etc.)."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.auth import User
from app.models.enums import UserRole
from app.models.profiles import ListenerProfile, VentorProfile

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    settings: SettingsDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = decode_access_token(credentials.credentials, settings)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized() from None

    user = (
        db.query(User)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None or not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_ventor(user: CurrentUser) -> User:
    if user.role != UserRole.ventor:
        raise forbidden()
    return user


CurrentVentor = Annotated[User, Depends(get_current_ventor)]


def get_current_ventor_profile(
    db: DbSession,
    user: CurrentVentor,
) -> VentorProfile:
    profile = (
        db.query(VentorProfile)
        .filter(VentorProfile.user_id == user.id)
        .one_or_none()
    )
    if profile is None:
        raise forbidden()
    return profile


CurrentVentorProfile = Annotated[VentorProfile, Depends(get_current_ventor_profile)]


def get_current_listener(user: CurrentUser) -> User:
    if user.role != UserRole.listener:
        raise forbidden()
    return user


CurrentListener = Annotated[User, Depends(get_current_listener)]


def get_current_listener_profile(
    db: DbSession,
    user: CurrentListener,
) -> ListenerProfile:
    profile = (
        db.query(ListenerProfile)
        .filter(ListenerProfile.user_id == user.id)
        .one_or_none()
    )
    if profile is None:
        raise forbidden()
    return profile


CurrentListenerProfile = Annotated[ListenerProfile, Depends(get_current_listener_profile)]
