"""
Global error handler middleware for the FastAPI application.
"""
from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.utils.exceptions import TrainingError

logger = logging.getLogger("baos_ai")


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the app."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_type": "validation_error"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(TrainingError)
    async def training_error_handler(request: Request, exc: TrainingError):
        # FIX (Phase 5): Preserve model/feature integrity errors instead of hiding them behind a generic 500.
        return JSONResponse(
            status_code=500,
            content={
                "error": "training_error",
                "detail": str(exc),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred. Please try again.",
                "path": str(request.url.path),
            },
        )
