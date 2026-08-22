"""Development/verification endpoints for the Phase 3B.1 authorization
layer ONLY — these are not business functionality and have no frontend.

They exist because the authorization dependencies in app/api/deps.py
(`require_system_admin`, `require_admin`, `require_admin_or_system_admin`,
`require_user_or_admin`, `require_department_access`) have nothing to
attach to yet — there is no real protected resource in this phase (no
Letter CRUD, no department/Admin/User management endpoints). Each route
below does nothing but apply one dependency and echo back the caller's own
profile, so the dependency chain (JWT → get_current_user → role/department
check) can be exercised end-to-end over real HTTP in
tests/integration/test_authorization.py, exactly the way a real protected
endpoint will be once one exists.

**Delete or repurpose this module once Phase 4 adds a real protected
resource** (e.g. Letter CRUD) — see docs/architecture/authorization.md,
"Resource-level authorization pattern". Tagged distinctly in the OpenAPI
schema (`dev-authorization-test`, not `auth`) so it's visually separated
in `/docs` from the real authentication endpoints in
app/api/v1/endpoints/auth.py.
"""

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import (
    require_admin,
    require_admin_or_system_admin,
    require_department_access,
    require_system_admin,
    require_user_or_admin,
)
from app.models.user import User
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/auth/test", tags=["dev-authorization-test"])


@router.get("/system-admin", response_model=UserPublic)
def test_system_admin_only(current_user: User = Depends(require_system_admin)) -> User:
    return current_user


@router.get("/admin", response_model=UserPublic)
def test_admin_only(current_user: User = Depends(require_admin)) -> User:
    return current_user


@router.get("/admin-or-system-admin", response_model=UserPublic)
def test_admin_or_system_admin(
    current_user: User = Depends(require_admin_or_system_admin),
) -> User:
    return current_user


@router.get("/user-or-admin", response_model=UserPublic)
def test_user_or_admin(current_user: User = Depends(require_user_or_admin)) -> User:
    return current_user


@router.get("/department/{department_id}", response_model=UserPublic)
def test_department_access(
    department_id: uuid.UUID,
    current_user: User = Depends(require_department_access),
) -> User:
    return current_user
