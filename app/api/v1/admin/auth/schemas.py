"""Admin auth schemas — A1–A5."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AdminRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AdminLogoutRequest(BaseModel):
    refresh_token: str | None = None


class AdminChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError(
                "Password must include at least 1 uppercase letter and 1 number"
            )
        return v


class AdminOkResponse(BaseModel):
    ok: bool = True


class AdminMeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    mfa_enabled: bool
    roles: list[str]
    permissions: list[str]
    last_login_at: datetime | None = None


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin: AdminMeResponse
