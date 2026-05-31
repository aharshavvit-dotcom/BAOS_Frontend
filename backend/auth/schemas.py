"""
Pydantic schemas for authentication endpoints.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


# ── Request Schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str = Field(..., min_length=4)

    @model_validator(mode="after")
    def require_identifier(self):
        if self.email is None and not self.username:
            raise ValueError("email or username is required")
        return self

    def identifier(self) -> str:
        value = str(self.email or self.username or "").strip()
        if "@" not in value:
            value = f"{value}@baos.ai"
        return value

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=150)
    company: str = Field(default="", max_length=200)
    port_code: str = Field(default="INMAA", max_length=20)

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)


# ── Response Schemas ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    company: str
    port_code: Optional[str] = None
    port_name: Optional[str] = None
    role: str

    # FIX (Phase 4): Pydantic v1 class Config remained -> use ConfigDict(from_attributes=True).
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str

    # FIX (Phase 4): Auth schemas still used implicit defaults -> enable ORM-compatible validation.
    model_config = ConfigDict(from_attributes=True)
