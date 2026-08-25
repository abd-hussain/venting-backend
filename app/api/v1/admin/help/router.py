from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.help.schemas import (
    HelpDocumentAdminResponse,
    HelpDocumentUpsertRequest,
)
from app.api.v1.admin.help.service import list_documents, upsert_document
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/help", tags=["admin-help"])
HelpReader = Annotated[
    AdminPrincipal, Depends(require_any_permission("cms:write", "users:read"))
]
HelpWriter = Annotated[AdminPrincipal, Depends(require_permission("cms:write"))]


@router.get(
    "/documents",
    response_model=APISuccessResponse[list[HelpDocumentAdminResponse]],
)
def documents_list(db: DbSession, _admin: HelpReader):
    return success_response(
        [row.model_dump(mode="json") for row in list_documents(db)]
    )


@router.put(
    "/documents/{topic}/{locale}",
    response_model=APISuccessResponse[HelpDocumentAdminResponse],
)
def documents_upsert(
    topic: str,
    locale: str,
    body: HelpDocumentUpsertRequest,
    db: DbSession,
    admin: HelpWriter,
):
    return success_response(
        upsert_document(
            db, topic=topic, locale=locale, payload=body, admin=admin
        ).model_dump(mode="json")
    )
