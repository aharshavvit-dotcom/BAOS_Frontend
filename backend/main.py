"""BAOS AI FastAPI application entry point."""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI

from backend.app_lifecycle import lifespan
from backend.config import settings
from backend.middleware import register_middleware
from backend.middleware.error_handler import register_error_handlers
from backend.middleware.request_logger import RequestLoggingMiddleware
from backend.routes import register_routes

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    # FIX (Phase 4): Checkpoint needs request logs visible in stdout -> send standard logging there.
    stream=sys.stdout,
)
logger = logging.getLogger("baos_ai")

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade FastAPI backend for the Maritime Decision Intelligence Platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_middleware(app)
register_error_handlers(app)
# FIX (Phase 4): API had no request/response logging middleware -> register it after error handlers.
app.add_middleware(RequestLoggingMiddleware)
register_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
