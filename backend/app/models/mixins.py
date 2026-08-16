"""Reusable column mixins shared by ORM models.

UUID strategy: primary keys are generated client-side with `uuid.uuid4()`
(Python's `default=`, not a PostgreSQL `server_default`). This avoids
depending on a PostgreSQL extension (`pgcrypto`/`uuid-ossp`) being installed
on every environment, while still storing the value as a native `uuid`
column via `postgresql.UUID(as_uuid=True)`.

Timestamp strategy: every timestamp column in this schema is timezone-aware
(`DateTime(timezone=True)`), and every `created_at`/`updated_at` pair uses a
database-side `server_default=func.now()` so the value is correct even for
rows inserted outside the ORM. Naive datetimes are never used.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a client-generated UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds `created_at`/`updated_at`, both timezone-aware and server-defaulted."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
