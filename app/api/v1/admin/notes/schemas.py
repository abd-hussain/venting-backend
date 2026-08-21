"""Schemas for admin audit logs and internal notes."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.pagination import Paginated


class AuditLogItem(BaseModel):
    id: str
    admin_user_id: str
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogList(Paginated[AuditLogItem]):
    pass


class AdminNoteItem(BaseModel):
    id: str
    admin_user_id: str
    entity_type: str
    entity_id: str
    body: str
    created_at: datetime
    updated_at: datetime


class AdminNoteList(Paginated[AdminNoteItem]):
    pass


class AdminNoteCreateRequest(BaseModel):
    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: UUID
    body: str = Field(min_length=1, max_length=10000)


class AdminNoteUpdateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
