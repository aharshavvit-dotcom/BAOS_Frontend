"""Authentication API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, get_optional_user
from backend.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from backend.db.models.app_models import User
from backend.db.session import get_db
from backend.handlers.auth_handler import (
    current_user_response,
    login_user,
    logout_user,
    refresh_user_token,
    signup_user,
)

legacy_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@legacy_router.post("/login", response_model=TokenResponse)
@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    return await login_user(req, db)


@legacy_router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT tokens."""
    return await signup_user(req, db)


@legacy_router.post("/refresh", response_model=AccessTokenResponse)
@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    req: RefreshRequest | None = None,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token."""
    return await refresh_user_token(req, db, user)


@legacy_router.get("/me", response_model=UserResponse)
@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return await current_user_response(user)


@legacy_router.post("/logout", response_model=MessageResponse)
@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions for the current user."""
    return await logout_user(user, db)
