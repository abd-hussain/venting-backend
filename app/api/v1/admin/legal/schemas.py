from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, HttpUrl


class LegalDocumentUpsertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=8)
    is_published: bool = True

    @field_validator("url")
    @classmethod
    def https_url(cls, value: str) -> str:
        trimmed = value.strip()
        parsed = HttpUrl(trimmed)
        if parsed.scheme != "https":
            raise ValueError("url must be an absolute HTTPS URL")
        return str(parsed)


class LegalDocumentAdminResponse(BaseModel):
    id: UUID
    document: str
    locale: str
    title: str
    url: str
    is_published: bool
    updated_at: datetime
    created_at: datetime
