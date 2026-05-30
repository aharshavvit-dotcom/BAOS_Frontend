"""
Async SQLAlchemy engine and session factory.
Also provides sync session factory for ingestion scripts.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (for ingestion scripts / CLI) ───────────────────────────────
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
)

SyncSessionFactory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM base class."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Sync session for CLI / ingestion scripts."""
    session = SyncSessionFactory()
    try:
        return session
    except Exception:
        session.close()
        raise


async def init_db():
    """Create all tables (dev/test only)."""
    # Import baos_models to register them with Base.metadata
    import backend.db.models.baos_models  # noqa: F401
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS baos"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
