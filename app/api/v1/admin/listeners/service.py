"""Admin listener review services — A22–A27."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.favorite_counts import favorite_count
from app.api.v1.admin.listeners.schemas import (
    IdentityDecision,
    IdentityDecisionRequest,
    IdentityVerificationDetail,
    ListenerMetricsUpdateRequest,
    ListenerQueueItem,
    ListenerReviewDetail,
    ListenerReviewResponse,
    RejectListenerRequest,
)
from app.api.v1.listeners.schemas import SetupStepId
from app.api.v1.admin.reports.schemas import RatingItem, RatingList
from app.core.errors import not_found, validation_error
from app.core.pagination import Paginated, clamp_page
from app.models.auth import User
from app.models.enums import ProfileStatus, SetupStepStatus
from app.models.lookups import (
    ListenerBoundary,
    ListenerComfortArea,
    ListenerLanguage,
    ListenerLifeExperience,
)
from app.models.profiles import ListenerIdentityVerification, ListenerProfile
from app.models.sessions import SessionRating


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _get_listener(db: Session, listener_id: UUID) -> tuple[ListenerProfile, User]:
    row = (
        db.query(ListenerProfile, User)
        .join(User, User.id == ListenerProfile.user_id)
        .filter(
            ListenerProfile.user_id == listener_id,
            User.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if row is None:
        raise not_found("Listener")
    return row


def _queue_item(profile: ListenerProfile, user: User) -> ListenerQueueItem:
    return ListenerQueueItem(
        id=str(profile.user_id),
        email=user.email,
        full_name=profile.full_name,
        avatar_url=profile.avatar_url,
        country=profile.country,
        profile_status=_value(profile.profile_status),
        submitted_at=profile.created_at,
    )


def list_review_queue(
    db: Session, *, page: int = 1, page_size: int = 20
) -> Paginated[ListenerQueueItem]:
    page, page_size = clamp_page(page, page_size)
    query = (
        db.query(ListenerProfile, User)
        .join(User, User.id == ListenerProfile.user_id)
        .filter(
            ListenerProfile.profile_status == ProfileStatus.under_review,
            User.deleted_at.is_(None),
        )
    )
    total = query.with_entities(func.count(ListenerProfile.user_id)).scalar() or 0
    rows = (
        query.order_by(ListenerProfile.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Paginated(
        items=[_queue_item(profile, user) for profile, user in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def _tag_values(db: Session, listener_id: UUID) -> dict:
    languages = [
        row.language_id
        for row in db.query(ListenerLanguage)
        .filter(ListenerLanguage.listener_id == listener_id)
        .order_by(ListenerLanguage.language_id)
        .all()
    ]
    comfort = [
        row.comfort_area_id
        for row in db.query(ListenerComfortArea)
        .filter(ListenerComfortArea.listener_id == listener_id)
        .order_by(ListenerComfortArea.comfort_area_id)
        .all()
    ]
    experiences = [
        {
            "id": row.life_experience_id,
            "custom_label": row.custom_label,
        }
        for row in db.query(ListenerLifeExperience)
        .filter(ListenerLifeExperience.listener_id == listener_id)
        .order_by(ListenerLifeExperience.life_experience_id)
        .all()
    ]
    boundaries = [
        row.boundary_id
        for row in db.query(ListenerBoundary)
        .filter(ListenerBoundary.listener_id == listener_id)
        .order_by(ListenerBoundary.boundary_id)
        .all()
    ]
    return {
        "languages": languages,
        "comfort_areas": comfort,
        "life_experiences": experiences,
        "boundaries": boundaries,
    }


def get_listener_review(db: Session, listener_id: UUID) -> ListenerReviewDetail:
    profile, user = _get_listener(db, listener_id)
    return ListenerReviewDetail(
        **_queue_item(profile, user).model_dump(),
        phone_e164=profile.phone_e164,
        date_of_birth=profile.date_of_birth,
        city=profile.city,
        gender=_value(profile.gender) if profile.gender else None,
        about_me=profile.about_me,
        bio=profile.bio,
        voice_intro_url=profile.voice_intro_url,
        voice_intro_seconds=profile.voice_intro_seconds,
        is_verified=profile.is_verified,
        rate_per_minute=float(profile.rate_per_minute or 0),
        rating=float(profile.rating_avg or 0),
        rating_count=profile.rating_count,
        session_count=profile.session_count,
        favorite_count=favorite_count(db, listener_id),
        rejection_reason=profile.rejection_reason,
        reviewed_at=profile.reviewed_at,
        **_tag_values(db, listener_id),
    )


def list_listener_ratings(
    db: Session,
    listener_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> RatingList:
    _get_listener(db, listener_id)
    page, page_size = clamp_page(page, page_size)
    query = db.query(SessionRating).filter(SessionRating.listener_id == listener_id)
    total = query.with_entities(func.count(SessionRating.id)).scalar() or 0
    rows = (
        query.order_by(SessionRating.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RatingList(
        items=[
            RatingItem(
                id=str(row.id),
                session_id=str(row.session_id),
                ventor_id=str(row.ventor_id),
                listener_id=str(row.listener_id),
                stars=row.stars,
                review=row.review,
                tip_amount=float(row.tip_amount) if row.tip_amount is not None else None,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def update_listener_metrics(
    db: Session,
    listener_id: UUID,
    payload: ListenerMetricsUpdateRequest,
    admin: AdminPrincipal,
) -> ListenerReviewDetail:
    profile, _ = _get_listener(db, listener_id)
    before = {
        "rate_per_minute": float(profile.rate_per_minute or 0),
        "rating_avg": float(profile.rating_avg or 0),
        "rating_count": profile.rating_count,
    }
    changes = payload.model_dump(exclude_unset=True)
    if "rate_per_minute" in changes:
        profile.rate_per_minute = Decimal(str(changes["rate_per_minute"]))
    if "rating" in changes:
        profile.rating_avg = Decimal(str(changes["rating"]))
    if "rating_count" in changes:
        profile.rating_count = changes["rating_count"]
    write_audit(
        db,
        admin_user_id=admin.id,
        action="listener.metrics_update",
        entity_type="listener",
        entity_id=profile.user_id,
        before=before,
        after={
            "rate_per_minute": float(profile.rate_per_minute or 0),
            "rating_avg": float(profile.rating_avg or 0),
            "rating_count": profile.rating_count,
        },
    )
    db.commit()
    db.refresh(profile)
    return get_listener_review(db, listener_id)


def _identity_detail(row: ListenerIdentityVerification) -> IdentityVerificationDetail:
    return IdentityVerificationDetail(
        id=str(row.id),
        listener_id=str(row.listener_id),
        identity_document_url=row.identity_document_url,
        selfie_url=row.selfie_url,
        status=_value(row.status),
        reviewer_note=row.reviewer_note,
        reviewed_by_admin_id=(
            str(row.reviewed_by_admin_id) if row.reviewed_by_admin_id else None
        ),
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        document_front_url=row.identity_document_url,
        document_back_url=None,
    )


def get_latest_identity(
    db: Session, listener_id: UUID
) -> IdentityVerificationDetail:
    _get_listener(db, listener_id)
    row = (
        db.query(ListenerIdentityVerification)
        .filter(ListenerIdentityVerification.listener_id == listener_id)
        .order_by(ListenerIdentityVerification.created_at.desc())
        .first()
    )
    if row is None:
        raise not_found("Identity verification")
    return _identity_detail(row)


def _review_response(profile: ListenerProfile) -> ListenerReviewResponse:
    return ListenerReviewResponse(
        id=str(profile.user_id),
        profile_status=_value(profile.profile_status),
        is_verified=profile.is_verified,
        reviewed_at=profile.reviewed_at,
    )


def approve_listener(
    db: Session, listener_id: UUID, admin: AdminPrincipal
) -> ListenerReviewResponse:
    profile, _ = _get_listener(db, listener_id)
    if profile.profile_status == ProfileStatus.approved and profile.is_verified:
        return _review_response(profile)
    before = {
        "profile_status": _value(profile.profile_status),
        "is_verified": profile.is_verified,
    }
    now = datetime.now(timezone.utc)
    profile.profile_status = ProfileStatus.approved
    profile.is_verified = True
    profile.reviewed_by_admin_id = admin.id
    profile.reviewed_at = now
    profile.rejection_reason = None
    profile.steps_to_refill = []
    profile.setup_identity_status = SetupStepStatus.done
    from app.services.inbox_notifications import send_book_first_session_listener

    send_book_first_session_listener(db, profile.user_id)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="listener.approve",
        entity_type="listener",
        entity_id=profile.user_id,
        before=before,
        after={"profile_status": "approved", "is_verified": True},
    )
    db.commit()
    db.refresh(profile)
    return _review_response(profile)


def reject_listener(
    db: Session,
    listener_id: UUID,
    payload: RejectListenerRequest,
    admin: AdminPrincipal,
) -> ListenerReviewResponse:
    profile, _ = _get_listener(db, listener_id)
    before = {
        "profile_status": _value(profile.profile_status),
        "is_verified": profile.is_verified,
        "rejection_reason": profile.rejection_reason,
    }
    status = (
        ProfileStatus.under_review
        if payload.needs_more_info
        else ProfileStatus.rejected
    )
    now = datetime.now(timezone.utc)
    profile.profile_status = status
    profile.is_verified = False
    profile.reviewed_by_admin_id = admin.id
    profile.reviewed_at = now
    profile.rejection_reason = payload.reason.strip()
    valid_step_ids = {step.value for step in SetupStepId}
    refill = [step_id for step_id in payload.steps_to_refill if step_id in valid_step_ids]
    if payload.steps_to_refill and len(refill) != len(payload.steps_to_refill):
        invalid = [step_id for step_id in payload.steps_to_refill if step_id not in valid_step_ids]
        raise validation_error(
            f"Invalid setup step ids: {', '.join(invalid)}",
            ar="معرّفات خطوات الإعداد غير صالحة",
        )
    profile.steps_to_refill = refill
    write_audit(
        db,
        admin_user_id=admin.id,
        action="listener.reject",
        entity_type="listener",
        entity_id=profile.user_id,
        before=before,
        after={
            "profile_status": status.value,
            "is_verified": False,
            "rejection_reason": profile.rejection_reason,
            "needs_more_info": payload.needs_more_info,
            "steps_to_refill": refill,
        },
    )
    db.commit()
    db.refresh(profile)
    return _review_response(profile)


def decide_identity(
    db: Session,
    verification_id: UUID,
    payload: IdentityDecisionRequest,
    admin: AdminPrincipal,
) -> IdentityVerificationDetail:
    row = db.get(ListenerIdentityVerification, verification_id)
    if row is None:
        raise not_found("Identity verification")
    before = {
        "status": _value(row.status),
        "reviewer_note": row.reviewer_note,
    }
    if payload.decision == IdentityDecision.approved:
        status = ProfileStatus.approved
    elif payload.decision == IdentityDecision.rejected:
        status = ProfileStatus.rejected
    else:
        # The persistence enum has no needs_more_info value; under_review means
        # the listener must provide another attempt.
        status = ProfileStatus.under_review
    row.status = status
    row.reviewer_note = payload.note
    row.reviewed_by_admin_id = admin.id
    row.reviewed_at = datetime.now(timezone.utc)
    profile = db.get(ListenerProfile, row.listener_id)
    if profile is not None:
        profile.setup_identity_status = (
            SetupStepStatus.done
            if status == ProfileStatus.approved
            else SetupStepStatus.in_progress
        )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="identity.decide",
        entity_type="listener_identity_verification",
        entity_id=row.id,
        before=before,
        after={
            "decision": payload.decision.value,
            "status": status.value,
            "reviewer_note": payload.note,
        },
    )
    db.commit()
    db.refresh(row)
    return _identity_detail(row)
