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
