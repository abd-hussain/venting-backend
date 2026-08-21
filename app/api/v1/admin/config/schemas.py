from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureFlagUpsertRequest(BaseModel):
    description: str | None = None
    enabled: bool = False
    rollout_percent: int = Field(default=100, ge=0, le=100)
    audience: str = Field(default="all", min_length=1, max_length=32)


class FeatureFlagResponse(FeatureFlagUpsertRequest):
    key: str
    updated_at: datetime


class ConfigValueRequest(BaseModel):
    value: Any


class ConfigResponse(BaseModel):
    key: str
    value: Any
    updated_at: datetime
