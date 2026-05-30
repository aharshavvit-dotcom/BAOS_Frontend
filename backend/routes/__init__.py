"""Route registry."""
from backend.auth.router import router as auth_v1_router
from backend.routes.assumptions import router as assumptions_router
from backend.routes.auth import router as auth_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.health import router as health_router
from backend.routes.ports import router as ports_router
from backend.routes.recommendations import router as recommendations_router
from backend.routes.websocket import socket_app

all_routers = [
    auth_router,
    auth_v1_router,
    dashboard_router,
    recommendations_router,
    ports_router,
    assumptions_router,
    health_router,
]
