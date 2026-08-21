"""Reusable API errors that match the MainAPIException contract."""

from fastapi import status

from app.core.exceptions import MainAPIException


def invalid_credentials() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=100,
        message="Invalid credentials",
        localized_message={
            "en": "Invalid credentials",
            "ar": "بيانات الاعتماد غير صحيحة",
        },
        http_status=status.HTTP_401_UNAUTHORIZED,
    )


def unauthorized() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=101,
        message="Unauthorized",
        localized_message={
            "en": "Authentication required",
            "ar": "يلزم تسجيل الدخول",
        },
        http_status=status.HTTP_401_UNAUTHORIZED,
    )


def forbidden() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=103,
        message="Forbidden",
        localized_message={
            "en": "You do not have permission to perform this action",
            "ar": "ليس لديك صلاحية لتنفيذ هذا الإجراء",
        },
        http_status=status.HTTP_403_FORBIDDEN,
    )


def email_already_registered() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=102,
        message="Email already registered",
        localized_message={
            "en": "An account with this email already exists",
            "ar": "يوجد حساب بهذا البريد الإلكتروني بالفعل",
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def invalid_password() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=422,
        message="Password must be at least 8 characters and include 1 uppercase letter and 1 number",
        localized_message={
            "en": "Password must be at least 8 characters and include 1 uppercase letter and 1 number",
            "ar": "يجب أن تكون كلمة المرور 8 أحرف على الأقل وتحتوي على حرف كبير ورقم",
        },
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def not_found(resource: str = "Resource") -> MainAPIException:
    return MainAPIException(
        type="not_found",
        code=404,
        message=f"{resource} not found",
        localized_message={
            "en": f"{resource} not found",
            "ar": f"لم يتم العثور على {resource}",
        },
        http_status=status.HTTP_404_NOT_FOUND,
    )


def conflict(message: str, *, en: str | None = None, ar: str | None = None) -> MainAPIException:
    return MainAPIException(
        type="conflict",
        code=409,
        message=message,
        localized_message={
            "en": en or message,
            "ar": ar or message,
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def validation_error(message: str, *, en: str | None = None, ar: str | None = None) -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=422,
        message=message,
        localized_message={
            "en": en or message,
            "ar": ar or message,
        },
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
