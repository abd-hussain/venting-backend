from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import AdminStatus


def _validate_password(value: str) -> str:
    if not any(char.isupper() for char in value) or not any(
        char.isdigit() for char in value
    ):
        raise ValueError("Password must include at least 1 uppercase letter and 1 number")
    return value


class StaffInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    role_keys: list[str] = Field(default_factory=list)
    temporary_password: str | None = Field(default=None, min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("temporary_password")
    @classmethod
    def strong_temporary_password(cls, value: str | None) -> str | None:
        return _validate_password(value) if value is not None else None


class StaffUpdateRequest(BaseModel):
    role_keys: list[str] | None = None
    status: AdminStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> "StaffUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class StaffResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    status: str
    role_keys: list[str]
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class StaffInviteResponse(StaffResponse):
    temporary_password: str


class PermissionResponse(BaseModel):
    id: UUID
    key: str
    description: str | None


class RoleResponse(BaseModel):
    id: UUID
    key: str
    name: str
    description: str | None
    permission_keys: list[str]


class RolePermissionsRequest(BaseModel):
    permission_keys: list[str]


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)


class StaffOkResponse(BaseModel):
    ok: bool = True
