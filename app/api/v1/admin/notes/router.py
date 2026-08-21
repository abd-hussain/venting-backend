"""Admin audit-log and internal-note routes (A91–A94)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.notes.schemas import (
    AdminNoteCreateRequest,
    AdminNoteItem,
    AdminNoteList,
    AdminNoteUpdateRequest,
    AuditLogList,
)
from app.api.v1.admin.notes.service import (
    create_note,
    list_audit_logs,
    list_notes,
    update_note,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(tags=["admin-audit"])

AuditReadAdmin = Annotated[
    AdminPrincipal, Depends(require_permission("audit:read"))
]
AuditOrUsersReadAdmin = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("audit:read", "users:read")),
]
UsersWriteAdmin = Annotated[
    AdminPrincipal, Depends(require_permission("users:write"))
]


@router.get(
    "/audit-logs",
    response_model=APISuccessResponse[AuditLogList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_audit_logs(
    db: DbSession,
    _admin: AuditReadAdmin,
    admin_user_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
    page: int = 1,
):
    data = list_audit_logs(
        db,
        admin_user_id=admin_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        from_at=from_at,
        to_at=to_at,
        page=page,
    )
    return success_response(data.model_dump(mode="json"))


@router.get(
    "/notes",
    response_model=APISuccessResponse[AdminNoteList],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def get_notes(
    entity_type: str,
    entity_id: UUID,
    db: DbSession,
    _admin: AuditOrUsersReadAdmin,
    page: int = 1,
):
    data = list_notes(db, entity_type=entity_type, entity_id=entity_id, page=page)
    return success_response(data.model_dump(mode="json"))


@router.post(
    "/notes",
    status_code=status.HTTP_201_CREATED,
    response_model=APISuccessResponse[AdminNoteItem],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def post_note(
    body: AdminNoteCreateRequest,
    db: DbSession,
    admin: UsersWriteAdmin,
):
    data = create_note(db, admin, body)
    return success_response(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.patch(
    "/notes/{note_id}",
    response_model=APISuccessResponse[AdminNoteItem],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def patch_note(
    note_id: UUID,
    body: AdminNoteUpdateRequest,
    db: DbSession,
    admin: UsersWriteAdmin,
):
    return success_response(
        update_note(db, admin, note_id, body).model_dump(mode="json")
    )
