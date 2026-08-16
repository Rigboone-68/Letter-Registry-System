"""Engine and session factory.

The engine is created lazily so that importing the application does not
require a live database during Phase 1. The connection string always comes
from configuration — never from a literal in the source.
"""

from typing import Generator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine, creating it on first use."""
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not configured. Copy .env.example to .env and "
                "set the connection string for your local PostgreSQL instance."
            )
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the process-wide session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session.

    Usage in later phases:
        def endpoint(db: Session = Depends(get_db)): ...
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
