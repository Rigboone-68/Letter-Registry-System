"""Shared pytest fixtures.

Database fixtures for model and authentication tests. These connect to a
*dedicated local PostgreSQL test database* — never the application's
development or production database, and never a real departmental
database. See docs/database/README.md, "Providing a local test database"
for setup instructions.

If that test database isn't reachable, model/auth tests are skipped (not
failed) so the rest of the suite still runs in environments without
PostgreSQL — see docs/PROJECT_STATUS.md, "Known Limitations" for why this
repository's current environment cannot run them.

PostgreSQL, not SQLite, is used here on purpose: this schema relies on
PostgreSQL-specific behavior (native ENUM types, JSONB, functional unique
indexes, `SELECT ... FOR UPDATE`) that SQLite either can't represent or
would silently emulate differently, which would make a passing test suite
meaningless for this schema.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.session import get_db
# `Base` alone does not register any model (see app/database/base.py) —
# importing app.models is what populates Base.metadata, required before
# create_all()/drop_all() below.
import app.models  # noqa: F401

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://lrs_test:lrs_test@localhost:5432/lrs_test",
)


@pytest.fixture(scope="session")
def engine():
    """Session-scoped engine bound to the local PostgreSQL test database.

    Creates the full schema once per test session and drops it afterward.
    Skips (does not fail) the tests that depend on this fixture when no
    PostgreSQL test database is reachable.
    """
    try:
        eng = create_engine(TEST_DATABASE_URL, future=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(
            "No local PostgreSQL test database reachable at "
            f"{TEST_DATABASE_URL} ({exc.__class__.__name__}). "
            "See docs/database/README.md to provision one; "
            "override the target with the TEST_DATABASE_URL env var."
        )
        return

    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def db_session(engine):
    """Function-scoped session wrapped in a transaction that is always rolled
    back, so each test starts from a clean, empty schema regardless of what
    earlier tests inserted.

    `join_transaction_mode="create_savepoint"`: the authentication services
    (app/services/auth_service.py, app/services/bootstrap_service.py) call
    `session.commit()` internally as part of their own transaction
    handling. Without this, that commit would end the connection-level
    transaction opened below for real, defeating per-test rollback
    isolation. With it, the session's begin/commit becomes a SAVEPOINT
    nested inside this fixture's outer transaction — `session.commit()`
    only releases the savepoint; the outer `transaction.rollback()` at
    teardown still undoes everything, including already-"committed" work.
    This is the documented SQLAlchemy 2.0 pattern for testing code that
    manages its own transactions."""
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection,
        future=True,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        # A failed flush (e.g. an expected IntegrityError from a constraint
        # test) already rolls back and deassociates this transaction at the
        # DBAPI level, so it may no longer be active by the time we get here.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    """A FastAPI TestClient whose `get_db` dependency is overridden to yield
    the *same* `db_session` this test uses directly — so an HTTP call made
    through the client and an ORM assertion made by the test see the same
    in-progress transaction, and both are rolled back together at teardown.
    See app/main.py / app/database/session.py:get_db for the dependency
    being overridden."""
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
