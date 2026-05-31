"""
WebSocket route for real-time updates via Socket.IO.
"""
from __future__ import annotations

import logging

import socketio

from backend.config import settings

logger = logging.getLogger("baos_ai.ws")

# Create Socket.IO server (async mode for FastAPI)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=settings.DEBUG,
)

# ASGI app to mount on FastAPI
socket_app = socketio.ASGIApp(sio, socketio_path="/api/realtime")


@sio.event
async def connect(sid, environ, auth=None):
    """Client connected."""
    logger.debug("Client connected: %s", sid)  # FIX (Phase 7.8): print → logger
    await sio.emit("notification", {
        "message": "Connected to BAOS AI real-time updates",
        "type": "info",
    }, room=sid)


@sio.event
async def disconnect(sid):
    """Client disconnected."""
    logger.debug("Client disconnected: %s", sid)  # FIX (Phase 7.8): print → logger


@sio.event
async def subscribe_kpi(sid, data):
    """Subscribe to KPI updates for a specific port."""
    port_id = data.get("port_id", "default")
    await sio.enter_room(sid, f"kpi:{port_id}")
    logger.debug("%s subscribed to kpi:%s", sid, port_id)  # FIX (Phase 7.8): print → logger


@sio.event
async def unsubscribe_kpi(sid, data):
    """Unsubscribe from KPI updates."""
    port_id = data.get("port_id", "default")
    await sio.leave_room(sid, f"kpi:{port_id}")


@sio.event
async def subscribe_recommendations(sid, data=None):
    """Subscribe to recommendation updates."""
    await sio.enter_room(sid, "recommendations")
    logger.debug("%s subscribed to recommendations", sid)  # FIX (Phase 7.8): print → logger


@sio.event
async def subscribe_vessel_status(sid, data):
    """Subscribe to vessel status updates."""
    vessel_id = data.get("vessel_id")
    if vessel_id:
        await sio.enter_room(sid, f"vessel:{vessel_id}")


# ── Broadcast helpers (called from services/tasks) ──────────────────────────

async def broadcast_kpi_update(port_id: str, kpi_data: dict):
    """Broadcast KPI update to all subscribers of a port."""
    await sio.emit("kpi_updated", kpi_data, room=f"kpi:{port_id}")


async def broadcast_recommendation(recommendation_data: dict):
    """Broadcast new recommendation to subscribers."""
    await sio.emit("recommendation_generated", recommendation_data, room="recommendations")


async def broadcast_assignment_change(vessel_id: str, assignment_data: dict):
    """Broadcast assignment status change."""
    await sio.emit("assignment_status_changed", assignment_data, room=f"vessel:{vessel_id}")
    # Also broadcast to recommendations room
    await sio.emit("assignment_status_changed", assignment_data, room="recommendations")


async def broadcast_notification(message: str, msg_type: str = "info"):
    """Broadcast a generic notification to all clients."""
    await sio.emit("notification", {
        "message": message,
        "type": msg_type,
    })
