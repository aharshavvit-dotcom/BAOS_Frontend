"""Request/response logging middleware."""
from __future__ import annotations

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.auth.jwt import decode_token

logger = logging.getLogger("baos_ai.requests")


def _user_id_from_request(request: Request) -> str:
    payload = getattr(request.state, "user_payload", None)
    if payload is None:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        payload = decode_token(token) if scheme.lower() == "bearer" and token else None
    if not payload:
        return "-"
    return str(payload.get("sub") or "-")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, duration, and user ID."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status_code = 500
        user_id = _user_id_from_request(request)
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            # FIX (Phase 4): Requests were not logged -> emit a structured request/response line.
            logger.info(
                "method=%s path=%s status=%s duration_ms=%.2f user_id=%s",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                user_id,
            )
