"""
BAOS AI — FastAPI Main Application.

Entry point for the Maritime Decision Intelligence backend.
Mounts all routes, middleware, CORS, WebSocket, and startup/shutdown events.

Run:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# psycopg3 requires SelectorEventLoop on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.connection import close_db, init_db
from middleware.error_handler import register_error_handlers
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.recommendations import router as recommendations_router
from routes.websocket import socket_app

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("baos_ai")


# ── Add parent project to path for engine imports ────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Lifespan events ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 BAOS AI backend starting up...")
    await init_db()
    logger.info("✅ Database tables ready")
    yield
    logger.info("🛑 Shutting down...")
    await close_db()


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade FastAPI backend for the Maritime Decision Intelligence Platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers ───────────────────────────────────────────────────────────

register_error_handlers(app)

# ── Routes ───────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(recommendations_router)

# ── Mount existing API endpoints (from parent project) ───────────────────────

try:
    from api.endpoints import app as legacy_app

    # Re-export legacy endpoints under /api/v1 (the original paths)
    # We mount the legacy routes directly so they remain accessible
    for route in legacy_app.routes:
        if hasattr(route, "path") and route.path not in ("/docs", "/redoc", "/openapi.json"):
            app.routes.append(route)
    logger.info("✅ Legacy API v1 endpoints mounted")
except ImportError as e:
    logger.warning(f"⚠️ Legacy API endpoints not available: {e}")

# ── Mount WebSocket (Socket.IO) ──────────────────────────────────────────────

app.mount("/ws", socket_app)

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["System"])
async def root():
    """API welcome page."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
