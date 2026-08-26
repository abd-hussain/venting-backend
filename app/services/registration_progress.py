"""Shared registration wizard progress helpers."""

from __future__ import annotations

import re

from app.core.errors import conflict, validation_error
from app.models.auth import User

VENTOR_REGISTER_STEPS: tuple[str, ...] = (
    "profile",
    "languages",
    "interests",
    "notifications",
)

LISTENER_REGISTER_STEPS: tuple[str, ...] = (
    "profile",
    "identity",
    "about",
    "experiences",
    "comfort-areas",
    "boundaries",
    "voice-intro",
    "availability",
    "notifications",
)

_AVATAR_PRESET_RE = re.compile(r"/static/avatars/presets/(\d+)\.png$")


def completed_steps(user: User) -> list[str]:
    raw = user.registration_completed_steps
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(step) for step in raw]
    return []


def next_step_for(user: User, steps: tuple[str, ...]) -> str:
    done = set(completed_steps(user))
    for step in steps:
        if step not in done:
            return step
    return steps[-1]


def mark_step_done(user: User, step: str, steps: tuple[str, ...]) -> None:
    done = set(completed_steps(user))
    done.add(step)
    user.registration_completed_steps = [item for item in steps if item in done]
    remaining = [item for item in steps if item not in done]
    user.registration_next_step = remaining[0] if remaining else None


def require_steps_done(
    user: User,
    required: tuple[str, ...],
    *,
    steps: tuple[str, ...],
) -> None:
    done = set(completed_steps(user))
    missing = [step for step in required if step not in done]
    if missing:
        raise validation_error(
            f"Complete registration steps first: {', '.join(missing)}",
            ar="أكمل خطوات التسجيل أولًا",
        )


def ensure_registration_open(user: User) -> None:
    if user.registration_complete:
        raise conflict(
            "Registration already complete",
            ar="التسجيل مكتمل بالفعل",
        )


def avatar_preset_from_url(url: str | None) -> int | None:
    if not url:
        return None
    match = _AVATAR_PRESET_RE.search(url)
    return int(match.group(1)) if match else None
