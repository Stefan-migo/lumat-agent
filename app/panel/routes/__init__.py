"""Panel router aggregator for API, CSV export, and realtime contracts."""

from fastapi import APIRouter

from app.panel.api import api_router
from app.panel.routes import export
from app.panel.api.routes import realtime

panel_router = APIRouter(prefix="/panel", tags=["panel"])

panel_router.include_router(api_router)
panel_router.include_router(export.router)
panel_router.include_router(realtime.router)
