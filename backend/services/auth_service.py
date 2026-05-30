"""
Authentication service — user creation, credential verification, token management.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
)
from auth.password import hash_password, verify_password
try:
    from backend.config import settings
except ImportError:
    from config import settings
from database.models import Port, Session, User


def normalize_email(email: str) -> str:
    """Normalize email addresses consistently for lookup and storage."""
    return email.strip().lower()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    company: str = "",
    port_code: str = "INMAA",
) -> User:
    """Register a new user. Raises ValueError if email exists."""
    normalized_email = normalize_email(email)
    normalized_port_code = port_code.strip().upper() if port_code else ""

    # Check duplicate
    existing = await db.execute(
        select(User)
        .options(selectinload(User.port))
        .where(func.lower(User.email) == normalized_email)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    # Resolve port
    port_id = None
    if normalized_port_code:
        port_result = await db.execute(select(Port).where(Port.code == normalized_port_code))
        port = port_result.scalar_one_or_none()
        if port:
            port_id = port.id

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=full_name,
        company=company,
        port_id=port_id,
        role="operator",
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """Verify credentials. Returns User if valid, None otherwise."""
    normalized_email = normalize_email(email)
    result = await db.execute(
        select(User)
        .options(selectinload(User.port))
        .where(func.lower(User.email) == normalized_email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if user.email != normalized_email:
        user.email = normalized_email
        await db.flush()
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_tokens(
    db: AsyncSession,
    user: User,
) -> Tuple[str, str]:
    """Create access + refresh tokens and persist the session."""
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = Session(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=get_token_expiry(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()

    return access_token, refresh_token


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> Optional[str]:
    """Validate refresh token and issue a new access token."""
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return None

    # Find session
    result = await db.execute(
        select(Session).where(
            Session.refresh_token == refresh_token,
            Session.expires_at > datetime.utcnow(),
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    # Update last activity
    session.last_activity = datetime.utcnow()
    await db.flush()

    # Fetch user
    user_result = await db.execute(
        select(User)
        .options(selectinload(User.port))
        .where(User.id == session.user_id, User.is_active == True)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        return None

    return create_access_token({"sub": str(user.id), "email": user.email})


async def revoke_session(
    db: AsyncSession,
    user_id: UUID,
    refresh_token: Optional[str] = None,
) -> None:
    """Revoke a specific session or all sessions for a user."""
    if refresh_token:
        await db.execute(
            delete(Session).where(
                Session.user_id == user_id,
                Session.refresh_token == refresh_token,
            )
        )
    else:
        await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.flush()


def build_user_response(user: User) -> dict:
    """Build a user response dictionary including port info."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "company": user.company,
        "port_code": user.port.code if user.port else None,
        "port_name": user.port.name if user.port else None,
        "role": user.role,
    }
