from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.training.schemas import (
    AchievementResponse,
    AchievementUpsertRequest,
    InviteStatsResponse,
    ListenerTrainingItem,
    ListenerTrainingResponse,
    TrainingModuleResponse,
    TrainingModuleUpsertRequest,
    VentorAchievementResponse,
)
from app.core.errors import not_found, validation_error
from app.models.enums import InviteStatus, SetupStepStatus, TrainingStatus
from app.models.profiles import ListenerProfile, VentorProfile
from app.models.rewards import InviteCode, InviteEvent
from app.models.training import ListenerTrainingProgress, TrainingModule
from app.models.ventor_wellness import Achievement, VentorAchievement


def _module_response(row: TrainingModule) -> TrainingModuleResponse:
    return TrainingModuleResponse(
        id=row.id,
        title_key=row.title_key,
        content_url=row.content_url,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


def _module_snapshot(row: TrainingModule) -> dict[str, Any]:
    return _module_response(row).model_dump(mode="json")


def _achievement_response(row: Achievement) -> AchievementResponse:
    return AchievementResponse(
        id=row.id,
        title_key=row.title_key,
        subtitle_key=row.subtitle_key,
        description_key=row.description_key,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


def _achievement_snapshot(row: Achievement) -> dict[str, Any]:
    return _achievement_response(row).model_dump(mode="json")


def list_training_modules(db: Session) -> list[TrainingModuleResponse]:
    rows = (
        db.query(TrainingModule)
        .order_by(TrainingModule.sort_order.asc(), TrainingModule.id.asc())
        .all()
    )
    return [_module_response(row) for row in rows]


def upsert_training_modules(
    db: Session,
    payload: TrainingModuleUpsertRequest | list[TrainingModuleUpsertRequest],
    admin: AdminPrincipal,
) -> list[TrainingModuleResponse]:
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise validation_error("At least one training module is required")
    if len({item.id for item in items}) != len(items):
        raise validation_error("Training module IDs must be unique")
    rows: list[TrainingModule] = []
    for item in items:
        row = db.get(TrainingModule, item.id)
        before = _module_snapshot(row) if row is not None else None
        if row is None:
            row = TrainingModule(id=item.id)
            db.add(row)
        row.title_key = item.title_key
        row.content_url = item.content_url
        row.sort_order = item.sort_order
        row.is_active = item.is_active
        write_audit(
            db,
            admin_user_id=admin.id,
            action="training_module.upsert",
            entity_type="training_module",
            entity_id=item.id,
            before=before,
            after=_module_snapshot(row),
        )
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_module_response(row) for row in rows]


def get_listener_training(
    db: Session, listener_id: UUID
) -> ListenerTrainingResponse:
    if db.get(ListenerProfile, listener_id) is None:
        raise not_found("Listener")
    modules = (
        db.query(TrainingModule)
        .order_by(TrainingModule.sort_order.asc(), TrainingModule.id.asc())
        .all()
    )
    progress = {
        row.module_id: row
        for row in db.query(ListenerTrainingProgress)
        .filter(ListenerTrainingProgress.listener_id == listener_id)
        .all()
    }
    items: list[ListenerTrainingItem] = []
    active_statuses: list[TrainingStatus] = []
    for module in modules:
        row = progress.get(module.id)
        status = row.status if row is not None else TrainingStatus.not_started
        items.append(
            ListenerTrainingItem(
                module=_module_response(module),
                status=status,
                completed_at=row.completed_at if row is not None else None,
            )
        )
        if module.is_active:
            active_statuses.append(status)
    completed_count = sum(
        status == TrainingStatus.completed for status in active_statuses
    )
    return ListenerTrainingResponse(
        listener_id=str(listener_id),
        items=items,
        completed_count=completed_count,
        total_count=len(active_statuses),
        all_completed=bool(active_statuses)
        and completed_count == len(active_statuses),
    )


def force_complete_training(
    db: Session,
    listener_id: UUID,
    module_id: str,
    admin: AdminPrincipal,
) -> ListenerTrainingResponse:
    profile = db.get(ListenerProfile, listener_id)
    if profile is None:
        raise not_found("Listener")
    if db.get(TrainingModule, module_id) is None:
        raise not_found("Training module")
    row = db.get(ListenerTrainingProgress, (listener_id, module_id))
    before = None
    if row is None:
        row = ListenerTrainingProgress(
            listener_id=listener_id,
            module_id=module_id,
        )
        db.add(row)
    else:
        before = {
            "status": row.status.value,
            "completed_at": (
                row.completed_at.isoformat() if row.completed_at is not None else None
            ),
        }
    if row.status != TrainingStatus.completed:
        row.status = TrainingStatus.completed
        row.completed_at = datetime.now(timezone.utc)
    if profile.setup_training_status == SetupStepStatus.locked:
        profile.setup_training_status = SetupStepStatus.in_progress
    db.flush()
    result = get_listener_training(db, listener_id)
    if result.all_completed:
        profile.setup_training_status = SetupStepStatus.done
        if profile.setup_tutorial_status == SetupStepStatus.locked:
            profile.setup_tutorial_status = SetupStepStatus.in_progress
    write_audit(
        db,
        admin_user_id=admin.id,
        action="listener_training.force_complete",
        entity_type="listener_training_progress",
        entity_id=f"{listener_id}:{module_id}",
        before=before,
        after={
            "status": row.status.value,
            "completed_at": (
                row.completed_at.isoformat() if row.completed_at is not None else None
            ),
        },
    )
    db.commit()
    return get_listener_training(db, listener_id)


def list_achievements(db: Session) -> list[AchievementResponse]:
    rows = (
        db.query(Achievement)
        .order_by(Achievement.sort_order.asc(), Achievement.id.asc())
        .all()
    )
    return [_achievement_response(row) for row in rows]


def upsert_achievements(
    db: Session,
    payload: AchievementUpsertRequest | list[AchievementUpsertRequest],
    admin: AdminPrincipal,
) -> list[AchievementResponse]:
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise validation_error("At least one achievement is required")
    if len({item.id for item in items}) != len(items):
        raise validation_error("Achievement IDs must be unique")
    rows: list[Achievement] = []
    for item in items:
        row = db.get(Achievement, item.id)
        before = _achievement_snapshot(row) if row is not None else None
        if row is None:
            row = Achievement(id=item.id)
            db.add(row)
        row.title_key = item.title_key
        row.subtitle_key = item.subtitle_key
        row.description_key = item.description_key
        row.sort_order = item.sort_order
        row.is_active = item.is_active
        write_audit(
            db,
            admin_user_id=admin.id,
            action="achievement.upsert",
            entity_type="achievement",
            entity_id=item.id,
            before=before,
            after=_achievement_snapshot(row),
        )
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_achievement_response(row) for row in rows]


def grant_achievement(
    db: Session,
    ventor_id: UUID,
    achievement_id: str,
    admin: AdminPrincipal,
) -> VentorAchievementResponse:
    if db.get(VentorProfile, ventor_id) is None:
        raise not_found("Ventor")
    if db.get(Achievement, achievement_id) is None:
        raise not_found("Achievement")
    row = db.get(VentorAchievement, (ventor_id, achievement_id))
    if row is None:
        row = VentorAchievement(
            ventor_id=ventor_id,
            achievement_id=achievement_id,
        )
        db.add(row)
        db.flush()
        write_audit(
            db,
            admin_user_id=admin.id,
            action="achievement.grant",
            entity_type="ventor_achievement",
            entity_id=f"{ventor_id}:{achievement_id}",
            after={
                "ventor_id": str(ventor_id),
                "achievement_id": achievement_id,
                "unlocked_at": row.unlocked_at.isoformat(),
            },
        )
        db.commit()
        db.refresh(row)
    return VentorAchievementResponse(
        ventor_id=str(row.ventor_id),
        achievement_id=row.achievement_id,
        unlocked_at=row.unlocked_at,
    )


def get_invite_stats(db: Session) -> InviteStatsResponse:
    invite_codes = db.query(func.count(InviteCode.id)).scalar() or 0
    grouped = (
        db.query(
            InviteEvent.status,
            func.count(InviteEvent.id),
            func.coalesce(func.sum(InviteEvent.points_earned), 0),
        )
        .group_by(InviteEvent.status)
        .all()
    )
    counts = {status: int(count) for status, count, _points in grouped}
    total_invites = sum(counts.values())
    points_earned = sum(int(points) for _status, _count, points in grouped)
    pending = counts.get(InviteStatus.pending, 0)
    converted = total_invites - pending
    return InviteStatsResponse(
        invite_codes=int(invite_codes),
        total_invites=total_invites,
        pending=pending,
        joined=counts.get(InviteStatus.joined, 0),
        first_session=counts.get(InviteStatus.first_session, 0),
        booked_call=counts.get(InviteStatus.booked_call, 0),
        points_earned=points_earned,
        converted_invites=converted,
        conversion_rate=round(converted / total_invites, 4) if total_invites else 0.0,
    )
