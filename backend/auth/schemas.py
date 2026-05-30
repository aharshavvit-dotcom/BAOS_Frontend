"""
Pydantic schemas for authentication endpoints.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=150)
    company: str = Field(default="", max_length=200)
    port_code: str = Field(default="INMAA", max_length=20)


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Response Schemas ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    company: str
    port_code: Optional[str] = None
    port_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
