# LRS Backend

FastAPI service for the Letter Registry System. **Phase 2: database
architecture and core models.** No endpoints, services, repositories, or
business logic are implemented yet — see `docs/architecture/overview.md`
§4 for exactly what is and isn't in place.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in local values; never commit .env
alembic upgrade head                # creates the Phase 2 schema — see below
uvicorn app.main:app --reload
```

Available now: `GET /health`, plus `/docs` and `/redoc`.

## Package layout

| Path | Responsibility |
|---|---|
| `app/main.py` | Application factory: logging, CORS, router mounting |
| `app/core/config.py` | Environment-based settings (single source of truth) |
| `app/core/security.py` | Placeholder — all hashing and token logic goes here |
| `app/core/logging.py` | Uniform log format and level |
| `app/database/base.py` | Declarative `Base` only — deliberately does not import `app.models` (see its docstring, and `docs/database/schema.md` §1) |
| `app/database/session.py` | Lazy engine, session factory, `get_db()` dependency |
| `app/models/` | SQLAlchemy models — 9 core entities (see `docs/database/schema.md`) |
| `app/schemas/` | Pydantic request/response contracts (empty) |
| `app/api/v1/endpoints/` | One router per resource (empty) |
| `app/services/` | Business logic and workflow (empty) |
| `app/repositories/` | The only layer that queries the database (empty) |
| `app/middleware/` | Request correlation and audit middleware (empty) |
| `app/utils/` | Pure helpers, no framework imports (empty) |

## Layering rules

* Endpoints call services. Endpoints do not build queries.
* Services call repositories. Services do not import routers.
* Repositories own the SQLAlchemy session and are the only ORM consumers.
* `utils` imports nothing from `api`, `services`, or `repositories`.

## Database & migrations

`alembic.ini` leaves `sqlalchemy.url` blank on purpose — `alembic/env.py`
injects `DATABASE_URL` from the environment at runtime, so no connection
string ever appears in source control.

Two migrations exist: `3da4b7ee8167_core_schema_...` (baseline — every
table, enum type, foreign key, index, and constraint) and
`e8a5cea2ccc6_database_hardening_...` (a corrective follow-up from a Phase 2
self-review: two missed indexes and a database-level default for
`notifications.is_read` — see `docs/database/schema.md` §1 "ORM deletion
behavior" and §6 "Indexes"). Both are described in `docs/database/schema.md`.

```bash
alembic upgrade head       # apply both, in order
alembic downgrade base     # fully reverse — drops all tables and enum types
alembic current            # show the applied revision
alembic history            # list both revisions
```

`alembic revision --autogenerate -m "description"` currently reports "no
changes detected" against these models — confirmed locally against a real
PostgreSQL 17 instance — so the migration and the models are in sync as of
this phase. Run it again whenever a model changes in a later phase.

**Never point `DATABASE_URL` at a real departmental database** — always a
disposable local/dev instance. See `docs/database/README.md` for how to set
one up, and for the separate test-database setup used by `pytest`.

## Configuration

Every setting is read from the environment via `app/core/config.py`. Required
keys are listed in `.env.example`. `SECRET_KEY` and `DATABASE_URL` have no
usable defaults — the application fails loudly rather than falling back to an
insecure value.

`CORS_ORIGINS` uses `NoDecode` on its field annotation so pydantic-settings
doesn't try to JSON-parse the plain comma-separated string documented in
`.env.example` before the field's own validator runs — without it, copying
`.env.example` verbatim crashed settings loading (and therefore `alembic`
and `uvicorn`) on startup. Fixed during Phase 2 validation since it broke
this document's own setup instructions; see `docs/PROJECT_STATUS.md` for the
record of the fix.

## Tests

```bash
pytest
```

`tests/integration/test_models.py` covers the Phase 2 model layer (creation,
relationships, constraints, FK `RESTRICT`/`CASCADE` behavior, and database
defaults for every entity) against a real local PostgreSQL test database —
see `docs/database/README.md`, "Providing a local test database". If none
is reachable, these tests are **skipped**, not failed, so `pytest` still
exits cleanly in an environment without PostgreSQL.

`tests/unit/test_imports.py` needs no database — it runs `from app.models
import X` in fresh subprocesses to guard against the circular-import
regression fixed in this phase (see `docs/database/schema.md` §1). It
always runs.
