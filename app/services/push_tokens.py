"""Persist FCM device tokens for push notifications."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notifications import UserPushToken


def upsert_push_token(db: Session, user_id: UUID, token: str | None) -> None:
    cleaned = (token or "").strip()
    if not cleaned:
        return

    row = db.query(UserPushToken).filter(UserPushToken.token == cleaned).one_or_none()
    if row is None:
        db.add(UserPushToken(user_id=user_id, token=cleaned))
        return

    row.user_id = user_id
