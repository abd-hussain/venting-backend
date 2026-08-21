from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BannerPlacement, CmsPageStatus


class CmsPageCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    locale: str = Field(default="en", min_length=2, max_length=8)
    body_markdown: str = ""


class CmsPageUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    locale: str | None = Field(default=None, min_length=2, max_length=8)
    body_markdown: str | None = None
    status: CmsPageStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> "CmsPageUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class CmsPageResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    locale: str
    body_markdown: str
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CmsBannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)
    cta_label: str | None = Field(default=None, max_length=64)
    cta_url: str | None = None
    placement: BannerPlacement
    audience: str = Field(default="all", min_length=1, max_length=32)
    starts_at: datetime
    ends_at: datetime | None = None
    is_active: bool = True


class CmsBannerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, min_length=1)
    cta_label: str | None = Field(default=None, max_length=64)
    cta_url: str | None = None
    placement: BannerPlacement | None = None
    audience: str | None = Field(default=None, min_length=1, max_length=32)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "CmsBannerUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class CmsBannerResponse(BaseModel):
    id: UUID
    title: str
    body: str
    cta_label: str | None
    cta_url: str | None
    placement: str
    audience: str
    starts_at: datetime
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
