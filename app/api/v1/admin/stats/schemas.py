"""Response models for admin dashboard statistics."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


Granularity = Literal["day", "week", "month"]


class OverviewStats(BaseModel):
    users: int
    sessions_today: int
    gmv: float
    pending_reviews: int
    open_reports: int


class UsersBucket(BaseModel):
    period: datetime
    ventors: int
    listeners: int
    total: int


class UsersStats(BaseModel):
    items: list[UsersBucket]
    active: int
    suspended: int


class SessionsBucket(BaseModel):
    period: datetime
    upcoming: int
    live: int
    completed: int
    cancelled: int
    missed: int
    total: int


class SessionsStats(BaseModel):
    items: list[SessionsBucket]


class RevenueBucket(BaseModel):
    period: datetime
    payments: float
    tips: float
    refunds: float
    discounts: float


class RevenueStats(BaseModel):
    items: list[RevenueBucket]
    payments: float
    tips: float
    refunds: float
    discounts: float


class NamedCount(BaseModel):
    name: str
    count: int


class ListenerStats(BaseModel):
    online: int
    by_tier: list[NamedCount]
    by_country: list[NamedCount]
    approval_funnel: list[NamedCount]


class WellnessStats(BaseModel):
    total: int
    distribution: list[NamedCount]
