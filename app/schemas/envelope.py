from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class LocalizedMessage(BaseModel):
    en: str
    ar: str


class APIErrorBody(BaseModel):
    type: str
    code: int
    message: str
    localized_message: LocalizedMessage | None = None


class APIErrorResponse(BaseModel):
    status: str = Field(default="failed", examples=["failed"])
    error: APIErrorBody


class APISuccessResponse(BaseModel, Generic[T]):
    status: str = Field(default="success", examples=["success"])
    data: T
