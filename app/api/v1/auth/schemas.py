"""Auth request/response schemas (Pydantic)."""

import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class AuthRole(str, Enum):
    ventor = "ventor"
    listener = "listener"


def _validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include at least 1 uppercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must include at least 1 number")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: AuthRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_rules(cls, value: str) -> str:
        return _validate_password_strength(value)


class RegisteredUser(BaseModel):
    id: str
    email: str
    role: AuthRole
    is_new: bool = True


class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: RegisteredUser


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: AuthRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoggedInUser(BaseModel):
    id: str
    email: str
    role: AuthRole
    registration_complete: bool


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: LoggedInUser


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class DeleteAccountRequest(BaseModel):
    password: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class OkResponse(BaseModel):
    ok: bool = True


class MeResponse(BaseModel):
    id: str
    email: str
    role: AuthRole
    display_name: str | None = None
    avatar_url: str | None = None
    registration_complete: bool
    listener_profile_status: str | None = None
