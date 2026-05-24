"""
Global error handler middleware for the FastAPI application.
"""
from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("baos_ai")


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the app."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_type": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred",
                "error_type": "internal_error",
            },
        )
