"""Shared list pagination helpers."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


def clamp_page(page: int = 1, page_size: int = 20, *, max_size: int = 50) -> tuple[int, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, max_size))
    return page, page_size
