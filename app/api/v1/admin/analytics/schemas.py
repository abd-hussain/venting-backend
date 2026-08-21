"""Response models for admin analytics helpers."""

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    users: int
    sessions_today: int
    gmv: float
    pending_reviews: int
    open_reports: int


class FunnelStage(BaseModel):
    key: str
    count: int
    conversion_from_previous: float | None = None


class AnalyticsFunnels(BaseModel):
    stages: list[FunnelStage]


class GaEmbedConfig(BaseModel):
    measurement_id: str
