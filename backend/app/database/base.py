"""Declarative base and metadata registry.

Every ORM model created in later phases must inherit from `Base` and be
imported here so that Alembic autogeneration can see the full metadata.

PHASE 1: no models exist yet — the import block below is intentionally empty.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all LRS ORM models."""


# --------------------------------------------------------------------------
# Model imports for Alembic autogenerate.
#
# When models are added (Phase 2+), import them below, e.g.:
#     from app.models.user import User  # noqa: F401
#
# No models are defined in Phase 1.
# --------------------------------------------------------------------------
