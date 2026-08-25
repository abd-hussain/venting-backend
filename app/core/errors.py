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


def image_required() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=1201,
        message="image_required",
        localized_message={
            "en": "A category image is required",
            "ar": "صورة الفئة مطلوبة",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_image_type() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=1202,
        message="invalid_image_type",
        localized_message={
            "en": "Image must be PNG, JPG, or JPEG",
            "ar": "يجب أن تكون الصورة بصيغة PNG أو JPG أو JPEG",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def file_too_large() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=1203,
        message="file_too_large",
        localized_message={
            "en": "Image must be 2MB or smaller",
            "ar": "يجب ألا يتجاوز حجم الصورة 2 ميجابايت",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def offer_expired() -> MainAPIException:
    return MainAPIException(
        type="conflict",
        code=1301,
        message="offer_expired",
        localized_message={
            "en": "This reward offer has expired.",
            "ar": "انتهت صلاحية عرض المكافأة هذا.",
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def tier_has_listeners(tier_id: str, count: int) -> MainAPIException:
    message = f'Cannot delete tier "{tier_id}": {count} listeners are assigned.'
    return MainAPIException(
        type="conflict",
        code=1302,
        message="tier_has_listeners",
        localized_message={
            "en": message,
            "ar": f'لا يمكن حذف المستوى "{tier_id}": {count} مستمعين مرتبطين به.',
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def invalid_email() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=110,
        message="Invalid email",
        localized_message={
            "en": "Invalid email address",
            "ar": "عنوان البريد الإلكتروني غير صالح",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_auth_role() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=111,
        message="Invalid role",
        localized_message={
            "en": "Role must be ventor or listener",
            "ar": "يجب أن يكون الدور ventor أو listener",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def auth_role_mismatch() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=112,
        message="Role mismatch",
        localized_message={
            "en": "This email is registered with a different account type",
            "ar": "هذا البريد مسجل بنوع حساب مختلف",
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def account_disabled() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=113,
        message="Account disabled",
        localized_message={
            "en": "This account is disabled or unavailable",
            "ar": "هذا الحساب معطل أو غير متاح",
        },
        http_status=status.HTTP_403_FORBIDDEN,
    )


def rate_limited() -> MainAPIException:
    return MainAPIException(
        type="rate_limit",
        code=429,
        message="Too many requests",
        localized_message={
            "en": "Too many requests. Please try again later.",
            "ar": "طلبات كثيرة جداً. يرجى المحاولة لاحقاً.",
        },
        http_status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def invalid_social_auth_request() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=120,
        message="Invalid social auth request",
        localized_message={
            "en": "Invalid provider, token, or role",
            "ar": "مزود أو رمز أو دور غير صالح",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_social_token() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=121,
        message="Invalid social ID token",
        localized_message={
            "en": "Sign-in token is invalid or expired",
            "ar": "رمز تسجيل الدخول غير صالح أو منتهي الصلاحية",
        },
        http_status=status.HTTP_401_UNAUTHORIZED,
    )


def social_nonce_mismatch() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=122,
        message="Apple nonce mismatch",
        localized_message={
            "en": "Sign-in verification failed. Please try again.",
            "ar": "فشل التحقق من تسجيل الدخول. يرجى المحاولة مرة أخرى.",
        },
        http_status=status.HTTP_401_UNAUTHORIZED,
    )


def social_email_unavailable() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=123,
        message="Email unavailable from provider",
        localized_message={
            "en": "Email unavailable; use the same Apple ID or continue with email",
            "ar": "البريد الإلكتروني غير متاح؛ استخدم نفس Apple ID أو تابع بالبريد",
        },
        http_status=status.HTTP_401_UNAUTHORIZED,
    )


def social_role_mismatch() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=124,
        message="Role mismatch",
        localized_message={
            "en": "This email is registered with a different account type",
            "ar": "هذا البريد مسجل بنوع حساب مختلف",
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def social_identity_conflict() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=125,
        message="Social identity conflict",
        localized_message={
            "en": "This account is already linked to a different sign-in method",
            "ar": "هذا الحساب مرتبط بالفعل بطريقة تسجيل دخول مختلفة",
        },
        http_status=status.HTTP_409_CONFLICT,
    )


def social_account_disabled() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=126,
        message="Account disabled",
        localized_message={
            "en": "This account is disabled or unavailable",
            "ar": "هذا الحساب معطل أو غير متاح",
        },
        http_status=status.HTTP_403_FORBIDDEN,
    )


def social_provider_unavailable() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=127,
        message="Social sign-in provider unavailable",
        localized_message={
            "en": "Sign-in service is temporarily unavailable. Please try again later.",
            "ar": "خدمة تسجيل الدخول غير متاحة مؤقتاً. يرجى المحاولة لاحقاً.",
        },
        http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def password_not_set() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=128,
        message="Password not set",
        localized_message={
            "en": "Set a password first before changing it",
            "ar": "قم بتعيين كلمة مرور أولاً قبل تغييرها",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_catalog_audience() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=740,
        message="Invalid audience",
        localized_message={
            "en": "audience must be ventor, listener, or all",
            "ar": "يجب أن يكون audience هو ventor أو listener أو all",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_forgot_password_request() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=210,
        message="Invalid email, role, or locale",
        localized_message={
            "en": "Invalid email, role, or locale",
            "ar": "البريد أو الدور أو اللغة غير صالحة",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def forgot_password_rate_limited() -> MainAPIException:
    return MainAPIException(
        type="rate_limit",
        code=211,
        message="Too many password reset requests",
        localized_message={
            "en": "Too many password reset requests. Please try again later.",
            "ar": "محاولات كثيرة لإعادة تعيين كلمة المرور. حاول لاحقاً.",
        },
        http_status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def invalid_reset_password() -> MainAPIException:
    return MainAPIException(
        type="validation",
        code=220,
        message="Weak or missing password",
        localized_message={
            "en": "Password must be at least 8 characters and include 1 uppercase letter and 1 number",
            "ar": "يجب أن تكون كلمة المرور 8 أحرف على الأقل وتحتوي على حرف كبير ورقم",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def invalid_or_expired_reset_token() -> MainAPIException:
    return MainAPIException(
        type="auth",
        code=221,
        message="Invalid or expired reset link",
        localized_message={
            "en": "This reset link is invalid or has expired",
            "ar": "رابط إعادة التعيين غير صالح أو منتهي الصلاحية",
        },
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def reset_password_rate_limited() -> MainAPIException:
    return MainAPIException(
        type="rate_limit",
        code=222,
        message="Too many reset attempts",
        localized_message={
            "en": "Too many reset attempts. Please try again later.",
            "ar": "محاولات كثيرة لإعادة التعيين. حاول لاحقاً.",
        },
        http_status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
