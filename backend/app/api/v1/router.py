"""Aggregate router for API v1 — one `include_router` per resource module.

Mounted in app/main.py under `settings.API_V1_PREFIX`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router)
