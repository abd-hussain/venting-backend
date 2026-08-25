from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.legal.schemas import (
    LegalDocumentAdminResponse,
    LegalDocumentUpsertRequest,
)
from app.api.v1.admin.legal.service import list_documents, upsert_document
from app.core.responses import success_response
from app.schemas.envelope import APISuccessResponse

router = APIRouter(prefix="/legal", tags=["admin-legal"])
LegalReader = Annotated[
    AdminPrincipal, Depends(require_any_permission("cms:write", "users:read"))
]
LegalWriter = Annotated[AdminPrincipal, Depends(require_permission("cms:write"))]


@router.get(
    "/documents",
    response_model=APISuccessResponse[list[LegalDocumentAdminResponse]],
)
def documents_list(db: DbSession, _admin: LegalReader):
    return success_response(
        [row.model_dump(mode="json") for row in list_documents(db)]
    )


@router.put(
    "/documents/{document}/{locale}",
    response_model=APISuccessResponse[LegalDocumentAdminResponse],
)
def documents_upsert(
    document: str,
    locale: str,
    body: LegalDocumentUpsertRequest,
    db: DbSession,
    admin: LegalWriter,
):
    return success_response(
        upsert_document(
            db, document=document, locale=locale, payload=body, admin=admin
        ).model_dump(mode="json")
    )
