"""Declarative base.

`Base` deliberately has zero knowledge of `app.models` — this module does
not import any model, directly or indirectly. Each model module imports
`Base` *from here* (`from app.database.base import Base`), which is a
one-directional dependency; if this module also imported `app.models` (as an
earlier version did, "so Alembic can see them"), that created a real,
order-dependent circular import: `from app.models import X` in a fresh
interpreter would fail depending on which module happened to be imported
first, because `app.database.base` and `app.models` would each need the
other to finish initializing before either could.

Code that needs every model registered on `Base.metadata` (Alembic's
`env.py`, `tests/conftest.py`) is responsible for importing `app.models`
itself, in addition to importing `Base` from here — see those two files.
This keeps the dependency graph acyclic: `app.models.*` → `app.database.base`,
never the other way around. See docs/database/schema.md, "Model import and
registration strategy" for the full reasoning and the fresh-interpreter
tests (`tests/unit/test_imports.py`) that guard against regressing this.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all LRS ORM models."""
