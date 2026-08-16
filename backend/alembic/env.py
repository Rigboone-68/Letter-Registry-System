"""Alembic migration environment.

Reads the database URL from application settings (environment-based) and
targets the metadata registered on `app.database.base.Base`.

PHASE 1: no migration scripts exist. `alembic/versions/` is intentionally
empty and no migration has been generated or executed.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the `app` package importable when Alembic runs from `backend/`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Copy backend/.env.example to "
        "backend/.env before running Alembic."
    )

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Populated automatically once models are imported in app/database/base.py.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to a script without connecting to the database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
