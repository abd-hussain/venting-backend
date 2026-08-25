from datetime import datetime

from pydantic import BaseModel


class LegalDocumentLink(BaseModel):
    document: str
    locale: str
    title: str
    url: str
    updated_at: datetime


class LegalLinksResponse(BaseModel):
    locale: str
    terms: LegalDocumentLink
    privacy: LegalDocumentLink
