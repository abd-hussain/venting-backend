"""Append-only admin audit log helper."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.admin import AdminAuditLog


def write_audit(
    db: Session,
    *,
    admin_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: str | UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminAuditLog:
    row = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=before,
        after=after,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(row)
    return row
