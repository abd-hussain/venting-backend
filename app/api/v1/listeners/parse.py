"""Multipart form parsing for listener registration (#22)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import UploadFile

from app.core.errors import validation_error


def _upload(value: Any) -> UploadFile | None:
    if isinstance(value, UploadFile) and value.filename:
        return value
    return None


def _scalar(form: Any, name: str, *, default: str | None = None) -> str | None:
    value = form.get(name)
    if value is None or value == "":
        return default
    if isinstance(value, UploadFile):
        return default
    text = str(value).strip()
    return text or default


def form_json_list_raw(form: Any, name: str) -> str | None:
    """Read a list field as a JSON array string or from repeated parts."""
    parts: list[str] = []
    if hasattr(form, "getlist"):
        parts = [str(v).strip() for v in form.getlist(name) if str(v).strip()]

    if len(parts) > 1:
        return json.dumps(parts)

    if len(parts) == 1:
        single = parts[0]
        if single.startswith("["):
            return single
        return json.dumps([single])

    return _scalar(form, name)


def parse_session_minutes_list(raw: str | int | list[int] | None) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [int(item) for item in raw]
    if isinstance(raw, int):
        return [raw]

    text = str(raw).strip()
    if not text:
        return []

    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise validation_error(
                "session_minutes must be an integer or JSON array of integers",
                ar="session_minutes يجب أن يكون عددًا صحيحًا أو مصفوفة",
            ) from exc
        if not isinstance(parsed, list):
            raise validation_error(
                "session_minutes must be an integer or JSON array of integers",
                ar="session_minutes يجب أن يكون عددًا صحيحًا أو مصفوفة",
            )
        numbers: list[int] = []
        for item in parsed:
            try:
                numbers.append(int(item))
            except (TypeError, ValueError) as exc:
                raise validation_error(
                    "session_minutes must be an integer or JSON array of integers",
                    ar="session_minutes يجب أن يكون عددًا صحيحًا أو مصفوفة",
                ) from exc
        return numbers

    try:
        return [int(text)]
    except ValueError as exc:
        raise validation_error(
            "session_minutes must be an integer or JSON array of integers",
            ar="session_minutes يجب أن يكون عددًا صحيحًا أو مصفوفة",
        ) from exc


def parse_session_minutes(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw

    text = str(raw).strip()
    if not text:
        return None

    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise validation_error(
                "session_minutes must be an integer or JSON array of integers",
                ar="session_minutes يجب أن يكون عددًا صحيحًا",
            ) from exc
        if isinstance(parsed, list):
            numbers: list[int] = []
            for item in parsed:
                try:
                    numbers.append(int(item))
                except (TypeError, ValueError) as exc:
                    raise validation_error(
                        "session_minutes must be an integer or JSON array of integers",
                        ar="session_minutes يجب أن يكون عددًا صحيحًا",
                    ) from exc
            return min(numbers) if numbers else None

    try:
        return int(text)
    except ValueError as exc:
        raise validation_error(
            "session_minutes must be an integer",
            ar="session_minutes يجب أن يكون عددًا صحيحًا",
        ) from exc


def parse_register_form(form: Any) -> dict[str, Any]:
    # Canonical: identity_document. Legacy aliases kept for migration.
    identity_document = (
        _upload(form.get("identity_document"))
        or _upload(form.get("document_front"))
        or _upload(form.get("identity_document_front"))
    )
    # document_back ignored for mobile onboarding (single ID photo).

    session_raw = _scalar(form, "session_minutes")

    return {
        "full_name": _scalar(form, "full_name") or "",
        "phone": _scalar(form, "phone"),
        "phone_country": _scalar(form, "phone_country"),
        "date_of_birth": _scalar(form, "date_of_birth"),
        "country_iso": _scalar(form, "country_iso"),
        "city": _scalar(form, "city"),
        "language_ids_raw": form_json_list_raw(form, "language_ids"),
        "life_experience_ids_raw": form_json_list_raw(form, "life_experience_ids"),
        "custom_experiences_raw": form_json_list_raw(form, "custom_experiences"),
        "comfort_area_ids_raw": form_json_list_raw(form, "comfort_area_ids"),
        "custom_comfort_area_text": _scalar(form, "custom_comfort_area_text"),
        "boundary_ids_raw": form_json_list_raw(form, "boundary_ids"),
        "custom_boundary_text": _scalar(form, "custom_boundary_text"),
        "availability_raw": _scalar(form, "availability"),
        "session_minutes": parse_session_minutes_list(session_raw),
        "fcm_token": _scalar(form, "fcm_token"),
        "voice_intro_seconds": parse_session_minutes(_scalar(form, "voice_intro_seconds")),
        "avatar": _upload(form.get("avatar")),
        "identity_document": identity_document,
        "selfie": _upload(form.get("selfie")),
        "voice_intro": _upload(form.get("voice_intro")),
    }
