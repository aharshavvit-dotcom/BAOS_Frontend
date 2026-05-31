"""Authentication request handlers."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from backend.auth.jwt import create_access_token
from backend.auth.service import (
    authenticate_user,
    build_user_response,
    create_tokens,
    create_user,
    refresh_access_token,
    revoke_session,
)
from backend.db.models.app_models import User


async def login_user(req: LoginRequest, db: AsyncSession) -> TokenResponse:
    """Authenticate a user and shape the token response."""
    user = await authenticate_user(db, req.identifier(), req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, refresh_token = await create_tokens(db, user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(**build_user_response(user)),
    )


async def signup_user(req: SignupRequest, db: AsyncSession) -> TokenResponse:
    """Register a user and shape the token response."""
    try:
        user = await create_user(
            db,
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            company=req.company,
            port_code=req.port_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    access_token, refresh_token = await create_tokens(db, user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(**build_user_response(user)),
    )


async def refresh_user_token(
    req: RefreshRequest | None,
    db: AsyncSession,
    user: User | None = None,
) -> AccessTokenResponse:
    """Refresh an access token."""
    if user is not None:
        new_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        })
        return AccessTokenResponse(access_token=new_token)

    if req is None or not req.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token or bearer token",
        )

    new_token = await refresh_access_token(db, req.refresh_token)
    if new_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return AccessTokenResponse(access_token=new_token)


async def current_user_response(user: User) -> UserResponse:
    """Shape the current-user profile response."""
    return UserResponse(**build_user_response(user))


async def logout_user(user: User, db: AsyncSession) -> MessageResponse:
    """Revoke the user's active sessions."""
    await revoke_session(db, user.id)
    return MessageResponse(message="Logged out successfully")
