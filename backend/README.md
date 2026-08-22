# LRS Backend

FastAPI service for the Letter Registry System. **Phase 3B.2: department
management**, built on Phase 3B.1's RBAC/department-isolation foundation
and Phase 3A's authentication. Full design in
`docs/architecture/authentication.md` (auth),
`docs/architecture/authorization.md` (RBAC/department isolation), and
`docs/architecture/department-management.md` (department CRUD). Admin
management, user approval, letter CRUD, uploads, dashboards, and
notifications are not implemented yet — see `docs/architecture/overview.md`
§4 and `docs/architecture/department-management.md` §11 for exactly what
is and isn't in place.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in local values; never commit .env
alembic upgrade head                # creates the Phase 2 schema
uvicorn app.main:app --reload
python -m app.cli create-system-admin   # first run only — see below
```

Available now: `GET /health`, `POST /api/v1/auth/signup`,
`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, the department
management endpoints (`/api/v1/departments*`, SYSTEM_ADMIN only), five
verification-only authorization endpoints under `/api/v1/auth/test/*` (not
business functionality — see `docs/architecture/authorization.md` §7),
plus `/docs` and `/redoc`.

## Bootstrapping the first System Admin

```bash
python -m app.cli create-system-admin
```

Interactive (name/email typed, password masked via `getpass` — never a
command-line argument, so it never lands in shell history). Refuses to run
if an active System Admin already exists. See
`docs/architecture/authentication.md` §8.

> **Windows note:** `getpass.getpass()` reads directly from the console and
> does not accept piped/redirected stdin — run this command in an actual
> terminal, not via `echo ... | python -m app.cli ...`.

## Package layout

| Path | Responsibility |
|---|---|
| `app/main.py` | Application factory: logging, CORS, versioned API router mounting |
| `app/cli.py` | `python -m app.cli create-system-admin` — server-side bootstrap only, no HTTP endpoint |
| `app/core/config.py` | Environment-based settings (single source of truth) |
| `app/core/security.py` | Password hashing (Argon2id) and JWT creation/validation — the one place either lives |
| `app/core/logging.py` | Uniform log format and level |
| `app/database/base.py` | Declarative `Base` only — deliberately does not import `app.models` (see its docstring, and `docs/database/schema.md` §1) |
| `app/database/session.py` | Lazy engine, session factory, `get_db()` dependency |
| `app/models/` | SQLAlchemy models — 9 core entities (see `docs/database/schema.md`) |
| `app/schemas/auth.py` | Signup/login/token/current-user request-response contracts |
| `app/schemas/department.py` | Department create/update/response/list-envelope contracts — no server-controlled field (`id`/`status`/timestamps) is ever accepted from a client |
| `app/api/deps.py` | `get_current_user` (authentication) plus `require_system_admin`/`require_admin`/`require_admin_or_system_admin`/`require_user_or_admin`/`require_department_access` (authorization) |
| `app/api/v1/router.py` | Aggregate v1 router |
| `app/api/v1/endpoints/auth.py` | `/auth/signup`, `/auth/login`, `/auth/me` |
| `app/api/v1/endpoints/departments.py` | `/departments*` — SYSTEM_ADMIN only |
| `app/api/v1/endpoints/dev_authz_test.py` | `/auth/test/*` — verification-only, not business functionality (see `docs/architecture/authorization.md` §7) |
| `app/services/auth_service.py` | Signup and login business logic |
| `app/services/bootstrap_service.py` | First-System-Admin creation logic (called by `app/cli.py`) |
| `app/services/authorization.py` | `assert_department_access` — the one framework-agnostic department-isolation rule, reused by `app/api/deps.py` and (eventually) resource-level services. Extended in Phase 3B.2 to also require the caller's department to be `ACTIVE` |
| `app/services/department_service.py` | Department CRUD business logic, including race-safe duplicate-name/code handling |
| `app/services/exceptions.py` | Service-layer domain errors, mapped to HTTP responses in the endpoint layer |
| `app/repositories/user_repository.py` | The only code that queries `User` |
| `app/repositories/user_authorization_repository.py` | The only code that queries `UserAuthorization`, including the race-safe `SELECT ... FOR UPDATE` signup consumes |
| `app/repositories/department_repository.py` | The only code that queries `Department` |
| `app/utils/email.py` | `normalize_email` — the one place "same email" is defined |
| `app/middleware/` | Request correlation and audit middleware (empty) |

## Layering rules

* Endpoints call services. Endpoints do not build queries.
* Services call repositories. Services do not import routers.
* Repositories own the SQLAlchemy session and are the only ORM consumers.
* `utils` imports nothing from `api`, `services`, or `repositories`.

Populated end-to-end by the authentication module (Phase 3A:
`app/api/v1/endpoints/auth.py` → `app/services/auth_service.py` →
`app/repositories/user_repository.py`), a "Dependencies / Authorization"
layer sitting between API and Services (Phase 3B.1: role checks directly
in `app/api/deps.py`, the department-isolation rule in
`app/services/authorization.py`), and now a second full vertical slice
(Phase 3B.2: `app/api/v1/endpoints/departments.py` →
`app/services/department_service.py` →
`app/repositories/department_repository.py`) — all using this same
structure rather than a second, competing one.

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
**None of Phase 3A (authentication), 3B.1 (RBAC/department authorization),
or 3B.2 (department management) required a schema change** — every column
either needs (`users.password_hash`, `users.role`, `users.department_id`,
`user_authorizations.status`/`expires_at`, `departments.name`/`code`/
`status`, etc.) already existed from Phase 2; `alembic check` confirms
zero drift after all three. Phase 3B.2 did fix a constraint-*naming*
inconsistency in `app/models/department.py` (see
`docs/database/schema.md` §2.1) — a Python-model-only change, not a
migration, since the real database already had the correct name.

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

`SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` (already
present in `app/core/config.py` since Phase 1 as placeholders) are now
actually used to sign and verify JWTs — see
`docs/architecture/authentication.md` §12. `SECRET_KEY` has no usable
default and is checked lazily, the first time a token is created or
decoded, mirroring `DATABASE_URL`'s existing lazy-check pattern in
`app/database/session.py:get_engine`.

## Tests

```bash
pytest
```

174 tests total. `SECRET_KEY` must be set (via `.env`) for the
JWT-dependent tests to run — copy `.env.example` to `.env` first if you
haven't.

**Model layer (Phase 2)** — `tests/integration/test_models.py`: creation,
relationships, constraints, FK `RESTRICT`/`CASCADE` behavior, and database
defaults for every entity, against a real local PostgreSQL test database —
see `docs/database/README.md`, "Providing a local test database". If none
is reachable, these tests are **skipped**, not failed, so `pytest` still
exits cleanly in an environment without PostgreSQL.

**Authentication (Phase 3A)**:

* `tests/unit/test_security.py`, `test_email_utils.py` — password hashing,
  password policy, JWT creation/validation/tampering/expiry, email
  normalization. No database; always run.
* `tests/integration/test_auth_bootstrap.py`, `test_auth_signup.py`,
  `test_auth_login.py`, `test_auth_current_user.py` — against the same
  PostgreSQL test database as the model tests, via a `client` fixture
  (`tests/conftest.py`) that wires FastAPI's `TestClient` to the same
  transactional `db_session` the test itself uses.
  `test_auth_signup.py::test_concurrent_signup_attempts_consume_authorization_exactly_once`
  is the one test that opens its own independent database connections (a
  real race needs two) and cleans up its own committed rows explicitly.

**Authorization (Phase 3B.1)**:

* `tests/unit/test_authorization.py` — `assert_department_access` and the
  four role-check dependencies, called directly with in-memory `User`
  objects (never persisted). No database; always runs.
* `tests/integration/test_authorization.py` — the same rules again, this
  time end-to-end: real JWTs, real database-backed Users across every
  role/department/status combination, real HTTP requests through the
  `/api/v1/auth/test/*` endpoints via the `client` fixture. Covers every
  scenario in the brief's Role/Department/Deactivation/Negative-security
  test lists, including the two explicit "attacker changes the department
  UUID in the request" cases.

**Department management (Phase 3B.2)**:

* `tests/integration/test_department_management.py` — real JWTs, real
  database-backed Users, real HTTP requests through `/api/v1/departments*`.
  Covers every item in the brief's Authorization/Creation/Retrieval/
  Update/Status/Security lists, including the deactivate → blocked →
  reactivate → restored cycle checked directly against the Phase 3B.1
  verification endpoint, and row-level assertions (not just status codes)
  proving deactivation never touches a User or Letter row.

`tests/unit/test_imports.py` needs no database — it runs `from app.models
import X` in fresh subprocesses to guard against the circular-import
regression fixed in Phase 2 (see `docs/database/schema.md` §1). It always
runs.
