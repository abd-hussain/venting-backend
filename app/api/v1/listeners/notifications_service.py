"""Listener notifications — re-exports shared inbox service."""

from app.services.inbox_notifications import (
    NotificationItem,
    NotificationsResponse,
    OkCountResponse,
    delete_notification,
    list_notifications,
    mark_all_read,
)

__all__ = [
    "NotificationItem",
    "NotificationsResponse",
    "OkCountResponse",
    "delete_notification",
    "list_notifications",
    "mark_all_read",
]
