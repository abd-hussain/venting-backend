"""Listener training modules."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.v1.listeners.schemas import SetupProgressResponse
from app.api.v1.listeners.service import get_setup_progress
from app.core.errors import not_found
from app.models.enums import SetupStepStatus, TrainingStatus
from app.models.profiles import ListenerProfile
from app.models.training import ListenerTrainingProgress, TrainingModule
from pydantic import BaseModel


class TrainingModuleItem(BaseModel):
    id: str
    title: str
    status: str
    content_url: str


class TrainingResponse(BaseModel):
    modules: list[TrainingModuleItem]
    all_completed: bool
    setup_progress: SetupProgressResponse | None = None


def _title_from_key(module: TrainingModule) -> str:
    # Prefer humanized last segment of title_key; fall back to id.
    key = module.title_key or module.id
    leaf = key.rsplit(".", 1)[-1]
    return leaf.replace("_", " ").title()


def _training_response(
    db: Session,
    profile: ListenerProfile,
    *,
    include_setup: bool = False,
) -> TrainingResponse:
    modules = (
        db.query(TrainingModule)
        .filter(TrainingModule.is_active.is_(True))
        .order_by(TrainingModule.sort_order.asc(), TrainingModule.id.asc())
        .all()
    )
    progress = {
        row.module_id: row
        for row in db.query(ListenerTrainingProgress)
        .filter(ListenerTrainingProgress.listener_id == profile.user_id)
        .all()
    }
    items: list[TrainingModuleItem] = []
    for module in modules:
        row = progress.get(module.id)
        status = row.status.value if row is not None else TrainingStatus.not_started.value
        items.append(
            TrainingModuleItem(
                id=module.id,
                title=_title_from_key(module),
                status=status,
                content_url=module.content_url,
            )
        )
    all_completed = bool(items) and all(i.status == TrainingStatus.completed.value for i in items)
    return TrainingResponse(
        modules=items,
        all_completed=all_completed,
        setup_progress=get_setup_progress(db, profile) if include_setup or all_completed else None,
    )


def get_training(db: Session, profile: ListenerProfile) -> TrainingResponse:
    return _training_response(db, profile, include_setup=False)


def complete_training_module(
    db: Session,
    profile: ListenerProfile,
    module_id: str,
) -> TrainingResponse:
    module = (
        db.query(TrainingModule)
        .filter(TrainingModule.id == module_id, TrainingModule.is_active.is_(True))
        .one_or_none()
    )
    if module is None:
        raise not_found("Training module")

    row = (
        db.query(ListenerTrainingProgress)
        .filter(
            ListenerTrainingProgress.listener_id == profile.user_id,
            ListenerTrainingProgress.module_id == module_id,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = ListenerTrainingProgress(
            listener_id=profile.user_id,
            module_id=module_id,
            status=TrainingStatus.completed,
            completed_at=now,
        )
        db.add(row)
    else:
        row.status = TrainingStatus.completed
        row.completed_at = now

    if profile.setup_training_status == SetupStepStatus.locked:
        profile.setup_training_status = SetupStepStatus.in_progress

    db.flush()
    result = _training_response(db, profile, include_setup=True)
    if result.all_completed:
        profile.setup_training_status = SetupStepStatus.done
        # Unlock tutorial step when training finishes.
        if profile.setup_tutorial_status == SetupStepStatus.locked:
            profile.setup_tutorial_status = SetupStepStatus.in_progress
        db.flush()
        result = _training_response(db, profile, include_setup=True)

    db.commit()
    db.refresh(profile)
    return result
