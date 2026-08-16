# Database Documentation

PostgreSQL is the system of record for all metadata. Scanned documents live on
the filesystem and are referenced by path.

> **Status: Phase 2 complete**, including a corrective hardening pass from a
> self-review. Core SQLAlchemy models exist for all entities described
> below, with two Alembic migrations: `3da4b7ee8167_core_schema...`
> (baseline) and `e8a5cea2ccc6_database_hardening...` (two missed indexes
> and a database-level default — see `schema.md` §1, "ORM deletion
> behavior" and §6, "Indexes"). No API, service, or repository layer
> consumes these models yet.

* [`schema.md`](schema.md) — every table, its purpose, columns, relationships,
  enums, constraints, indexes, and the reasoning behind each. Naming, key
  strategy (UUID), and timestamp conventions are documented there (§1),
  rather than in a separate `conventions.md`, since this is currently a
  two-migration schema.
* `migrations.md` — not yet created; see "Applying these migrations locally"
  below for the current workflow.

## Applying these migrations locally

```bash
cd backend
cp .env.example .env      # then set DATABASE_URL to your local Postgres
alembic upgrade head       # applies both migrations, in order
```

This creates all tables, enum types, foreign keys, indexes, and constraints
described in [`schema.md`](schema.md). `alembic downgrade base` reverses it
completely (drops all tables, then all enum types). `alembic history` shows
both revisions; `alembic current` shows which is applied.

**Never point `DATABASE_URL` at a real departmental database.** Use a
dedicated local development database (e.g. `lrs_dev`).

## Providing a local test database

Model tests (`backend/tests/integration/test_models.py`) require a real,
dedicated PostgreSQL **test** database — not the dev database above, and
never a real one. SQLite is deliberately not used as a stand-in: this schema
relies on PostgreSQL-specific behavior (native `ENUM` types, `JSONB`,
functional unique indexes) that SQLite cannot faithfully reproduce, so a
passing SQLite-backed suite would not actually verify this schema.

```sql
-- run once, as a Postgres superuser, on your local instance only
CREATE ROLE lrs_test WITH LOGIN PASSWORD 'lrs_test' CREATEDB;
CREATE DATABASE lrs_test OWNER lrs_test;
```

Then run the suite, pointing it at that database (defaults to
`postgresql+psycopg2://lrs_test:lrs_test@localhost:5432/lrs_test` if unset):

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg2://lrs_test:lrs_test@localhost:5432/lrs_test pytest
```

`backend/tests/conftest.py` creates the full schema once per test session
(`Base.metadata.create_all`) and drops it afterward; each test runs inside a
transaction that is always rolled back, so tests never see each other's
data. If no PostgreSQL test database is reachable, these tests are
**skipped**, not failed — see `docs/PROJECT_STATUS.md` for whether that is
currently the case in a given environment.

`backend/tests/unit/test_imports.py` is the one test module that needs no
database at all — it runs `from app.models import X` in fresh subprocesses
to guard against the circular-import regression described in `schema.md`
§1, "Model import and registration strategy". It always runs, regardless of
whether a PostgreSQL test database is available.
