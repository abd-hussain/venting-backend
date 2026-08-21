from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.deps import AdminPrincipal, require_permission
from app.api.v1.admin.notifications.schemas import (
    BroadcastRequest,
    BroadcastResponse,
    NotificationMessage,
    NotificationResponse,
)
from app.api.v1.admin.notifications.service import (
    broadcast,
    list_system_notifications,
    send_to_user,
)
from app.core.pagination import Paginated
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/notifications", tags=["admin-notifications"])
UsersReader = Annotated[AdminPrincipal, Depends(require_permission("users:read"))]
UsersWriter = Annotated[AdminPrincipal, Depends(require_permission("users:write"))]


@router.post("/broadcast", response_model=APISuccessResponse[BroadcastResponse])
def broadcast_notification(body: BroadcastRequest, db: DbSession, admin: UsersWriter):
    return success_response(broadcast(db, body, admin).model_dump(mode="json"))


@router.get("", response_model=APISuccessResponse[Paginated[NotificationResponse]])
def notification_history(
    db: DbSession, _admin: UsersReader, page: int = 1, page_size: int = 20
):
    return success_response(
        list_system_notifications(db, page=page, page_size=page_size).model_dump(
            mode="json"
        )
    )


@router.post(
    "/user/{user_id}", response_model=APISuccessResponse[NotificationResponse]
)
def notify_user(
    user_id: UUID, body: NotificationMessage, db: DbSession, _admin: UsersWriter
):
    return success_response(send_to_user(db, user_id, body).model_dump(mode="json"))
