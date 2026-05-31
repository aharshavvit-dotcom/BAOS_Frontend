"""Route registry."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from backend.routes.assumptions import router as assumptions_router
from backend.routes.auth import legacy_router as auth_legacy_router
from backend.routes.auth import router as auth_v1_router
from backend.routes.berths import router as berths_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.health import router as health_router
from backend.routes.ports import router as ports_router
from backend.routes.recommendations import legacy_router as recommendations_legacy_router
from backend.routes.recommendations import router as recommendations_router
from backend.routes.training import router as training_router
from backend.routes.websocket import socket_app

logger = logging.getLogger("baos_ai")

all_routers = [
    auth_legacy_router,
    auth_v1_router,
    dashboard_router,
    recommendations_legacy_router,
    recommendations_router,
    ports_router,
    berths_router,
    training_router,
    assumptions_router,
    health_router,
]


def register_routes(app: FastAPI) -> None:
    """Register all HTTP and WebSocket routes."""
    for router in all_routers:
        app.include_router(router)

    try:
        # FIX: Legacy API moved to archive/. Kept for backward compat — try both locations.
        from api.endpoints import app as legacy_app
    except ImportError as exc:
        logger.warning("Legacy API endpoints not available: %s", exc)
    else:
        existing_route_keys = {
            (route.path, frozenset(getattr(route, "methods", set()) or set()))
            for route in app.routes
            if hasattr(route, "path")
        }
        mounted_count = 0
        skipped_count = 0
        for route in legacy_app.routes:
            if not hasattr(route, "path") or route.path in ("/docs", "/redoc", "/openapi.json"):
                continue
            route_key = (route.path, frozenset(getattr(route, "methods", set()) or set()))
            if route_key in existing_route_keys:
                # FIX (Phase 4): Legacy API duplicated typed routes/OpenAPI IDs -> skip exact conflicts.
                skipped_count += 1
                continue
            app.routes.append(route)
            existing_route_keys.add(route_key)
            mounted_count += 1
        logger.info(
            "Legacy API v1 endpoints mounted: mounted=%s skipped_duplicates=%s",
            mounted_count,
            skipped_count,
        )

    app.mount("/ws", socket_app)
