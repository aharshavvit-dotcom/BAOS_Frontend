"""Shared API response schemas."""
from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# FIX (Phase 4): List endpoints had inconsistent raw arrays -> define one pagination contract.


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard page/page_size wrapper for list endpoints."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


def build_paginated_response(
    *,
    items: list[T],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[T]:
    """Build a validated pagination envelope."""
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
