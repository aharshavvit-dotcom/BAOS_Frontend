"""Application startup and shutdown hooks."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.db.session import close_db, init_db
from backend.services.model_training_service import auto_train_required_models

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy

logger = logging.getLogger("baos_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources and clean them up on shutdown."""
    logger.info("BAOS AI backend starting up...")
    try:
        await init_db()
        app.state.startup_training_task = asyncio.create_task(auto_train_required_models())
        logger.info("ML model readiness check scheduled")
        logger.info("Database tables ready")
    except Exception as exc:
        logger.error("Database initialization failed; limited endpoints may still run: %s", exc)

    yield

    training_task = getattr(app.state, "startup_training_task", None)
    if training_task and not training_task.done():
        training_task.cancel()

    logger.info("BAOS AI backend shutting down...")
    try:
        await close_db()
    except Exception as exc:
        logger.error("Error closing DB connection: %s", exc)
