"""Aggregate router for API v1 — one `include_router` per resource module.

Mounted in app/main.py under `settings.API_V1_PREFIX`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admins, auth, departments, dev_authz_test, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(admins.router)
api_router.include_router(users.router)
# Phase 3B.1 verification-only routes — see that module's docstring.
api_router.include_router(dev_authz_test.router)
