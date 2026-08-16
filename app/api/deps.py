"""Shared FastAPI dependencies (auth, db session, headers, etc.)."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
