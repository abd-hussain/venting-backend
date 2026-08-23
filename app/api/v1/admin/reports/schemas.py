"""Schemas for admin report triage and moderation APIs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.pagination import Paginated
from app.models.enums import ModerationActionType


ReportStatus = Literal["open", "reviewed", "closed"]


class ReportItem(BaseModel):
    id: str
    session_id: str
    reporter_user_id: str
    reported_role: str
    reason: str
    details: str | None = None
    status: str
    assigned_admin_id: str | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    created_at: datetime


class ReportList(Paginated[ReportItem]):
    pass


class ReportUpdateRequest(BaseModel):
    assigned_admin_id: UUID | None = None
    status: ReportStatus | None = None
    resolution_note: str | None = Field(default=None, max_length=5000)


class ModerationCreateRequest(BaseModel):
    user_id: UUID
    action: ModerationActionType
    reason: str = Field(min_length=1, max_length=5000)
    ends_at: datetime | None = None
    related_report_id: UUID | None = None


class ModerationActionItem(BaseModel):
    id: str
    user_id: str
    admin_user_id: str
    action: str
    reason: str
    starts_at: datetime
    ends_at: datetime | None = None
    related_report_id: str | None = None
    created_at: datetime


class ModerationActionList(Paginated[ModerationActionItem]):
    pass


class RatingItem(BaseModel):
    id: str
    session_id: str
    ventor_id: str
    listener_id: str
    stars: int
    review: str | None = None
    tip_amount: float | None = None
    created_at: datetime


class RatingList(Paginated[RatingItem]):
    pass


class RatingUpdateRequest(BaseModel):
    stars: int | None = Field(default=None, ge=1, le=5)
    review: str | None = None

    @model_validator(mode="after")
    def require_change(self) -> "RatingUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class FeedbackItem(BaseModel):
    id: str
    session_id: str
    listener_id: str
    ventor_id: str
    stars: int
    felt_heard: bool
    talk_again: bool
    created_at: datetime


class FeedbackList(Paginated[FeedbackItem]):
    pass
