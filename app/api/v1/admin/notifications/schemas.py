from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class NotificationMessage(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class BroadcastRequest(NotificationMessage):
    audience: Literal["all", "ventor", "listener", "user_ids"]
    user_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def validate_user_ids(self) -> "BroadcastRequest":
        if self.audience == "user_ids" and not self.user_ids:
            raise ValueError("user_ids is required for the user_ids audience")
        return self


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class BroadcastResponse(BaseModel):
    created_count: int
