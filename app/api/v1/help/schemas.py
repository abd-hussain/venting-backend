from datetime import datetime

from pydantic import BaseModel


class HelpDocumentLink(BaseModel):
    topic: str
    locale: str
    title: str
    url: str
    updated_at: datetime


class HelpLinksResponse(BaseModel):
    locale: str
    items: list[HelpDocumentLink]
