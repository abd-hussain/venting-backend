"""Transactional email helpers (password reset, etc.)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


def _reset_email_html(*, locale: str, reset_url: str) -> tuple[str, str]:
    if locale == "ar":
        subject = "إعادة تعيين كلمة مرور Venting"
        cta = "إعادة التعيين"
        body_line = "استخدم الزر أدناه لإعادة تعيين كلمة المرور. الرابط صالح لمدة 60 دقيقة."
        ignore = "إذا لم تطلب ذلك، تجاهل هذه الرسالة."
        dir_attr = ' dir="rtl"'
    else:
        subject = "Reset your Venting password"
        cta = "Reset password"
        body_line = (
            "Use the button below to reset your password. "
            "This link expires in 60 minutes."
        )
        ignore = "If you did not request this, you can ignore this email."
        dir_attr = ""

    html = f"""<!DOCTYPE html>
<html{dir_attr}>
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;background:#0A0614;font-family:Inter,Segoe UI,Tahoma,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0A0614;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:480px;background:#1a1524;border-radius:16px;padding:28px 24px;color:#f4f0fa;">
        <tr><td style="font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#8A3CFE;font-size:13px;padding-bottom:16px;">Venting</td></tr>
        <tr><td style="font-size:22px;font-weight:700;padding-bottom:10px;">{subject}</td></tr>
        <tr><td style="color:#a89bb8;font-size:15px;line-height:1.6;padding-bottom:24px;">{body_line}</td></tr>
        <tr><td align="center" style="padding-bottom:24px;">
          <a href="{reset_url}" style="display:inline-block;background:#8A3CFE;color:#fff;text-decoration:none;font-weight:700;padding:14px 28px;border-radius:999px;">{cta}</a>
        </td></tr>
        <tr><td style="color:#a89bb8;font-size:13px;line-height:1.5;">{ignore}</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return subject, html


def send_password_reset_email(
    *,
    settings: Settings,
    to_email: str,
    locale: str,
    reset_url: str,
) -> bool:
    """Send reset email. Returns True if sent (or logged in debug without SMTP)."""
    subject, html = _reset_email_html(locale=locale, reset_url=reset_url)
    from_addr = settings.mail_from or settings.support_email

    if not settings.smtp_host:
        logger.warning(
            "SMTP not configured — password reset link for %s: %s",
            to_email,
            reset_url,
        )
        return settings.debug

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(
        f"{subject}\n\n{reset_url}\n\nThis link expires in 60 minutes."
    )
    msg.add_alternative(html, subtype="html")

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=20
            ) as smtp:
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=20
            ) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
