"""Admin user directory and moderation services — A12–A21."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.favorite_counts import favorite_counts_map
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
from app.core.errors import not_found, validation_error
from app.core.pagination import Paginated, clamp_page
from app.models.admin import ModerationAction
from app.models.auth import RefreshToken, User
from app.models.enums import ModerationActionType, ProfileStatus, UserRole
from app.models.profiles import ListenerProfile, VentorProfile
from app.models.sessions import Session as VentingSession


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _json_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=str(user.id),
        email=user.email,
        role=_value(user.role),
        is_active=user.is_active,
        registration_complete=user.registration_complete,
        suspended_until=user.suspended_until,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _get_user(db: Session, user_id: UUID) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if user is None:
        raise not_found("User")
    return user


def list_users(
    db: Session,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
    email: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[UserSummary]:
    page, page_size = clamp_page(page, page_size)
    query = db.query(User).filter(User.deleted_at.is_(None))
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    if email and email.strip():
        query = query.filter(User.email.ilike(f"%{email.strip()}%"))
    total = query.with_entities(func.count(User.id)).scalar() or 0
    rows = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Paginated(
        items=[_user_summary(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_user_dossier(db: Session, user_id: UUID) -> UserDossier:
    user = _get_user(db, user_id)
    if user.role == UserRole.ventor:
        profile = db.get(VentorProfile, user.id)
        session_filter = VentingSession.ventor_id == user.id
        profile_data = (
            {
                "nickname": profile.nickname,
                "gender": _value(profile.gender),
                "avatar_url": profile.avatar_url,
                "quote": profile.quote,
                "points_balance": profile.points_balance,
                "completed_sessions_count": profile.completed_sessions_count,
            }
            if profile
            else None
        )
    else:
        profile = db.get(ListenerProfile, user.id)
        session_filter = VentingSession.listener_id == user.id
        profile_data = (
            {
                "full_name": profile.full_name,
                "avatar_url": profile.avatar_url,
                "profile_status": _value(profile.profile_status),
                "is_verified": profile.is_verified,
                "rating": float(profile.rating_avg or 0),
                "session_count": profile.session_count,
            }
            if profile
            else None
        )
    session_count = (
        db.query(func.count(VentingSession.id)).filter(session_filter).scalar() or 0
    )
    token_count = (
        db.query(func.count(RefreshToken.id))
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .scalar()
        or 0
    )
    actions = (
        db.query(ModerationAction)
        .filter(ModerationAction.user_id == user.id)
        .order_by(ModerationAction.created_at.desc())
        .limit(50)
        .all()
    )
    return UserDossier(
        **_user_summary(user).model_dump(),
        profile=profile_data,
        session_count=int(session_count),
        refresh_token_count=int(token_count),
        moderation_actions=[
            {
                "id": str(row.id),
                "action": _value(row.action),
                "reason": row.reason,
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
                "created_at": row.created_at,
            }
            for row in actions
        ],
    )


def update_user(
    db: Session,
    user_id: UUID,
    payload: UserUpdateRequest,
    admin: AdminPrincipal,
) -> UserSummary:
    user = _get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("email"):
        email = str(changes["email"]).strip().lower()
        exists = (
            db.query(User.id)
            .filter(User.email == email, User.id != user.id)
            .first()
        )
        if exists:
            raise validation_error("Email is already in use")
        changes["email"] = email
    before = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after=changes,
    )
    db.commit()
    db.refresh(user)
    return _user_summary(user)


def _revoke_tokens(db: Session, user_id: UUID, now: datetime) -> None:
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .update({RefreshToken.revoked_at: now}, synchronize_session=False)
    )


def _moderate(
    db: Session,
    user_id: UUID,
    admin: AdminPrincipal,
    *,
    action: ModerationActionType,
    reason: str,
    is_active: bool,
    suspended_until: datetime | None,
    revoke_tokens: bool,
) -> ActionResponse:
    user = _get_user(db, user_id)
    now = datetime.now(timezone.utc)
    before = {
        "is_active": user.is_active,
        "suspended_until": _json_datetime(user.suspended_until),
    }
    user.is_active = is_active
    user.suspended_until = suspended_until
    db.add(
        ModerationAction(
            user_id=user.id,
            admin_user_id=admin.id,
            action=action,
            reason=reason.strip(),
            starts_at=now,
            ends_at=suspended_until,
        )
    )
    if revoke_tokens:
        _revoke_tokens(db, user.id, now)
    after = {
        "is_active": is_active,
        "suspended_until": _json_datetime(suspended_until),
    }
    write_audit(
        db,
        admin_user_id=admin.id,
        action=f"user.{action.value}",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(user)
    return ActionResponse(user=_user_summary(user))


def suspend_user(
    db: Session, user_id: UUID, payload: SuspendRequest, admin: AdminPrincipal
) -> ActionResponse:
    if payload.suspended_until:
        until = payload.suspended_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until <= datetime.now(timezone.utc):
            raise validation_error("suspended_until must be in the future")
        payload.suspended_until = until
    return _moderate(
        db,
        user_id,
        admin,
        action=ModerationActionType.suspend,
        reason=payload.reason,
        is_active=False,
        suspended_until=payload.suspended_until,
        revoke_tokens=True,
    )


def unsuspend_user(
    db: Session, user_id: UUID, payload: ModerationRequest, admin: AdminPrincipal
) -> ActionResponse:
    return _moderate(
        db,
        user_id,
        admin,
        action=ModerationActionType.unsuspend,
        reason=payload.reason,
        is_active=True,
        suspended_until=None,
        revoke_tokens=False,
    )


def ban_user(
    db: Session, user_id: UUID, payload: ModerationRequest, admin: AdminPrincipal
) -> ActionResponse:
    return _moderate(
        db,
        user_id,
        admin,
        action=ModerationActionType.ban,
        reason=payload.reason,
        is_active=False,
        suspended_until=None,
        revoke_tokens=True,
    )


def force_logout(
    db: Session, user_id: UUID, payload: ModerationRequest, admin: AdminPrincipal
) -> ActionResponse:
    user = _get_user(db, user_id)
    now = datetime.now(timezone.utc)
    _revoke_tokens(db, user.id, now)
    db.add(
        ModerationAction(
            user_id=user.id,
            admin_user_id=admin.id,
            action=ModerationActionType.force_logout,
            reason=payload.reason.strip(),
            starts_at=now,
        )
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="user.force_logout",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return ActionResponse(user=_user_summary(user))


def list_ventors(
    db: Session,
    *,
    email: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[VentorSummary]:
    page, page_size = clamp_page(page, page_size)
    query = (
        db.query(VentorProfile, User)
        .join(User, User.id == VentorProfile.user_id)
        .filter(User.deleted_at.is_(None))
    )
    if email and email.strip():
        query = query.filter(User.email.ilike(f"%{email.strip()}%"))
    total = query.with_entities(func.count(VentorProfile.user_id)).scalar() or 0
    rows = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Paginated(
        items=[
            VentorSummary(
                id=str(profile.user_id),
                email=user.email,
                nickname=profile.nickname,
                avatar_url=profile.avatar_url,
                is_active=user.is_active,
                points_balance=profile.points_balance,
                completed_sessions_count=profile.completed_sessions_count,
                created_at=user.created_at,
            )
            for profile, user in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_ventor(db: Session, ventor_id: UUID) -> VentorDetail:
    row = (
        db.query(VentorProfile, User)
        .join(User, User.id == VentorProfile.user_id)
        .filter(VentorProfile.user_id == ventor_id, User.deleted_at.is_(None))
        .one_or_none()
    )
    if row is None:
        raise not_found("Ventor")
    profile, user = row
    return VentorDetail(
        id=str(profile.user_id),
        email=user.email,
        nickname=profile.nickname,
        avatar_url=profile.avatar_url,
        is_active=user.is_active,
        points_balance=profile.points_balance,
        completed_sessions_count=profile.completed_sessions_count,
        created_at=user.created_at,
        gender=_value(profile.gender),
        quote=profile.quote,
        is_anonymous=profile.is_anonymous,
        mood_streak_days=profile.mood_streak_days,
        last_mood_checkin_date=(
            profile.last_mood_checkin_date.isoformat()
            if profile.last_mood_checkin_date
            else None
        ),
    )


def list_listeners(
    db: Session,
    *,
    profile_status: ProfileStatus | None = None,
    email: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[ListenerSummary]:
    page, page_size = clamp_page(page, page_size)
    query = (
        db.query(ListenerProfile, User)
        .join(User, User.id == ListenerProfile.user_id)
        .filter(User.deleted_at.is_(None))
    )
    if profile_status is not None:
        query = query.filter(ListenerProfile.profile_status == profile_status)
    if email and email.strip():
        query = query.filter(User.email.ilike(f"%{email.strip()}%"))
    total = query.with_entities(func.count(ListenerProfile.user_id)).scalar() or 0
    rows = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    counts = favorite_counts_map(db, [profile.user_id for profile, _ in rows])
    return Paginated(
        items=[
            ListenerSummary(
                id=str(profile.user_id),
                email=user.email,
                full_name=profile.full_name,
                avatar_url=profile.avatar_url,
                is_active=user.is_active,
                is_online=profile.is_online,
                is_verified=profile.is_verified,
                profile_status=_value(profile.profile_status),
                rating=float(profile.rating_avg or 0),
                rating_count=profile.rating_count,
                rate_per_minute=float(profile.rate_per_minute or 0),
                session_count=profile.session_count,
                favorite_count=counts.get(profile.user_id, 0),
                created_at=user.created_at,
            )
            for profile, user in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )
