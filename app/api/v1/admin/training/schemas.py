from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TrainingStatus


class TrainingModuleResponse(BaseModel):
    id: str
    title_key: str
    content_url: str
    sort_order: int
    is_active: bool


class TrainingModuleUpsertRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title_key: str = Field(min_length=1, max_length=128)
    content_url: str = Field(min_length=1)
    sort_order: int = 0
    is_active: bool = True


class ListenerTrainingItem(BaseModel):
    module: TrainingModuleResponse
    status: TrainingStatus
    completed_at: datetime | None = None


class ListenerTrainingResponse(BaseModel):
    listener_id: str
    items: list[ListenerTrainingItem]
    completed_count: int
    total_count: int
    all_completed: bool


class InviteStatsResponse(BaseModel):
    invite_codes: int
    total_invites: int
    pending: int
    joined: int
    first_session: int
    booked_call: int
    points_earned: int
    converted_invites: int
    conversion_rate: float
