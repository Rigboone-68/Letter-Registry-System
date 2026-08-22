# LRS Backend

FastAPI service for the Letter Registry System. **Phase 4B: Letter
Registry Core — implemented, and a pre-commit hardening pass applied on
top.** Builds on Phase 4A's architecture review and the fully-delivered
Phase 3B (Roles & Access Management: authentication, RBAC/department
isolation, department management, Admin management, User management).
Full design in `docs/architecture/authentication.md` (auth),
`docs/architecture/authorization.md` (RBAC/department isolation),
`docs/architecture/department-management.md` (department CRUD),
`docs/architecture/admin-management.md` (Admin lifecycle),
`docs/architecture/user-management.md` (User lifecycle), and
`docs/architecture/letter-registry.md` (the six finalized business
decisions and the resulting Letter/Category/Classification design — a
department-scoped Letter registry with recipient/source department
separation, required sender details, a required reference number (no
uniqueness constraint — its scope was never confirmed and was removed
after an initial global-uniqueness assumption; see §14 of that doc),
exactly three seeded Categories, and a real, documented-as-provisional
classified-access authorization boundary). File upload/download,
dashboards, and notifications are still not implemented — see
`docs/architecture/overview.md` §4 and
`docs/architecture/letter-registry.md` §12-14 for exactly what is and
isn't in place.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in local values; never commit .env
alembic upgrade head                # creates the full current schema
uvicorn app.main:app --reload
python -m app.cli create-system-admin   # first run only — see below
```

Available now: `GET /health`, `POST /api/v1/auth/signup`,
`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, the department
management endpoints (`/api/v1/departments*`, SYSTEM_ADMIN only), the
Admin management endpoints (`/api/v1/admins*`, SYSTEM_ADMIN only), the
User management endpoints (`/api/v1/users*`, ADMIN only, scoped to the
caller's own department), the Letter registry endpoints (`/api/v1/letters*`,
USER/ADMIN create; any authenticated role reads/updates/archives subject
to `assert_letter_access`), Category/Classification management
endpoints (`/api/v1/categories*`, `/api/v1/classifications*`,
SYSTEM_ADMIN only), five verification-only authorization endpoints under
`/api/v1/auth/test/*` (not business functionality — see
`docs/architecture/authorization.md` §7), plus `/docs` and `/redoc`.

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
| `app/models/` | SQLAlchemy models — 9 core entities (see `docs/database/schema.md`); `Letter`/`Classification` extended in Phase 4B |
| `app/schemas/auth.py` | Signup/login/token/current-user request-response contracts |
| `app/schemas/department.py` | Department create/update/response/list-envelope contracts — no server-controlled field (`id`/`status`/timestamps) is ever accepted from a client |
| `app/schemas/admin.py` | Admin-authorization/response/list-envelope/department-transfer contracts — same no-server-controlled-field guarantee |
| `app/schemas/user.py` | User-authorization/response/list-envelope contracts (Phase 3B.4) — `UserAuthorizationCreate` has no `department_id` field at all (always derived from the calling Admin), unlike `AdminAuthorizationCreate` |
| `app/schemas/letter.py` | Letter create/update/response/list-envelope contracts (Phase 4B) — no `recipient_department_id`/`recorded_by`/`status` field on `LetterCreate` |
| `app/schemas/category.py`, `app/schemas/classification.py` | Category/Classification create/update/response/list-envelope contracts (Phase 4B) — same no-server-controlled-field guarantee; `Classification` additionally carries `restricts_access` |
| `app/api/deps.py` | `get_current_user` (authentication) plus `require_system_admin`/`require_admin`/`require_admin_or_system_admin`/`require_user_or_admin`/`require_department_access` (authorization) |
| `app/api/v1/router.py` | Aggregate v1 router |
| `app/api/v1/endpoints/auth.py` | `/auth/signup`, `/auth/login`, `/auth/me` |
| `app/api/v1/endpoints/departments.py` | `/departments*` — SYSTEM_ADMIN only |
| `app/api/v1/endpoints/admins.py` | `/admins*` — SYSTEM_ADMIN only |
| `app/api/v1/endpoints/users.py` | `/users*` — ADMIN only, scoped to the caller's own department (Phase 3B.4); includes the project's first authorization-revocation endpoint |
| `app/api/v1/endpoints/letters.py` | `/letters*` (Phase 4B) — `POST` is USER/ADMIN only; every other route accepts any authenticated role, with the actual department/classified-access decision made inside `LetterService`, not the route dependency |
| `app/api/v1/endpoints/categories.py`, `app/api/v1/endpoints/classifications.py` | `/categories*`, `/classifications*` (Phase 4B) — SYSTEM_ADMIN only, mirroring `departments.py` exactly |
| `app/api/v1/endpoints/dev_authz_test.py` | `/auth/test/*` — verification-only, not business functionality (see `docs/architecture/authorization.md` §7) |
| `app/services/auth_service.py` | Signup and login business logic — role now derived from `UserAuthorization.purpose` (Phase 3B.3) |
| `app/services/bootstrap_service.py` | First-System-Admin creation logic (called by `app/cli.py`) |
| `app/services/authorization.py` | `assert_department_access` — the one framework-agnostic department-isolation rule, reused by `app/api/deps.py`, genuinely exercised as a resource-level check first in Phase 3B.4 (User) and again in Phase 4B (Letter). Extended in Phase 3B.2 to require the caller's department be `ACTIVE`; extended in Phase 4B with `assert_letter_access`/`can_view_letter` — the classified-access authorization boundary layered on top, not a competing mechanism |
| `app/services/department_service.py` | Department CRUD business logic, including race-safe duplicate-name/code handling |
| `app/services/admin_service.py` | Admin authorization/approval/lifecycle/department-transfer business logic |
| `app/services/user_service.py` | User authorization/approval/lifecycle/revocation business logic, scoped to the calling Admin's own department (Phase 3B.4) |
| `app/services/letter_service.py` | Letter create/read/update/archive business logic (Phase 4B) — `recorded_by`/`recipient_department_id` always derived from the caller; reference-number/source-department/category/classification validation |
| `app/services/category_service.py`, `app/services/classification_service.py` | Category/Classification CRUD business logic (Phase 4B), mirroring `department_service.py` |
| `app/services/exceptions.py` | Service-layer domain errors, mapped to HTTP responses in the endpoint layer |
| `app/repositories/user_repository.py` | The only code that queries `User` — extended in Phase 3B.3 with `find_admin_by_id`/`list_admins`/`update_status`/`update_department`, and in Phase 3B.4 with `find_user_by_id`/`list_users`, rather than a new repository each time |
| `app/repositories/user_authorization_repository.py` | The only code that queries `UserAuthorization`, including the race-safe `SELECT ... FOR UPDATE` signup consumes, (Phase 3B.3) `create`/`find_unresolved`, and (Phase 3B.4) `find_by_id`/`list_by_department`/`revoke` |
| `app/repositories/department_repository.py` | The only code that queries `Department` |
| `app/repositories/letter_repository.py` | The only code that queries `Letter` (Phase 4B) — every read eagerly loads `classification`, since `assert_letter_access` needs `restricts_access` without a second query at each call site |
| `app/repositories/category_repository.py`, `app/repositories/classification_repository.py` | The only code that queries `Category`/`Classification` (Phase 4B) |
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
`app/services/authorization.py`), a second full vertical slice (Phase
3B.2: `app/api/v1/endpoints/departments.py` →
`app/services/department_service.py` →
`app/repositories/department_repository.py`), a third (Phase 3B.3:
`app/api/v1/endpoints/admins.py` → `app/services/admin_service.py`) that
deliberately reuses the existing `UserRepository`/
`UserAuthorizationRepository` rather than adding a fourth repository —
Admin accounts are `User` rows and Admin authorizations are
`UserAuthorization` rows, so a dedicated `AdminRepository` would have
queried the same two tables a second way — and a fourth (Phase 3B.4:
`app/api/v1/endpoints/users.py` → `app/services/user_service.py`) that
extends the same two repositories again for the same reason, rather than
adding a fifth. All of it uses this same structure rather than a second,
competing one.

## Database & migrations

`alembic.ini` leaves `sqlalchemy.url` blank on purpose — `alembic/env.py`
injects `DATABASE_URL` from the environment at runtime, so no connection
string ever appears in source control.

Five migrations exist: `3da4b7ee8167_core_schema_...` (baseline — every
table, enum type, foreign key, index, and constraint),
`e8a5cea2ccc6_database_hardening_...` (a corrective follow-up from a Phase 2
self-review: two missed indexes and a database-level default for
`notifications.is_read` — see `docs/database/schema.md` §1 "ORM deletion
behavior" and §6 "Indexes"), `a223396c9eac_admin_management_...`
(Phase 3B.3: adds `user_authorizations.purpose`, backfilling any existing
row to `USER` before tightening the column to `NOT NULL` — tested against
an actual pre-existing row, not just an empty table),
`48ec742d9e8f_letter_registry_core_...` (Phase 4B: renames
`letters.department_id`/`received_from` to `recipient_department_id`/
`source_name` — data-preserving renames, not recreated columns — adds
sender-detail/reference-number/source-department/source-location columns
with the same safe backfill pattern, adds
`classifications.restricts_access`, and seeds exactly three `categories`
rows), and `c887ab35e4a3_remove_premature_reference_number_...` (a
same-phase hardening-pass correction: drops
`uq_letters_reference_number` — the finalized decision confirmed
reference numbers "must be unique" but never confirmed the scope, and
global was an unconfirmed guess that a real multi-department registry
could easily violate legitimately; see
`docs/architecture/letter-registry.md` §2.3/§14). All five are described
in `docs/database/schema.md`.
**None of Phase 3A (authentication), 3B.1 (RBAC/department authorization),
3B.2 (department management), or 3B.4 (User management) required a schema
change** — every column either needed already existed from Phase 2, or
(Phase 3B.4) from Phase 3B.3's `purpose` column and Phase 2's own
`AuthorizationStatus.REVOKED` enum value, which simply had no endpoint
setting it until now. Phase 3B.2 did fix a constraint-*naming*
inconsistency in `app/models/department.py` (see `docs/database/schema.md`
§2.1) — a Python-model-only change, not a migration, since the real
database already had the correct name. Phase 3B.3 and Phase 4B (two
migrations) are the only phases since Phase 2's hardening pass to need
one; `alembic check` confirms zero drift after all five.

```bash
alembic upgrade head       # apply all five, in order
alembic downgrade base     # fully reverse — drops all tables and enum types
alembic current            # show the applied revision
alembic history            # list all revisions
```

`alembic revision --autogenerate -m "description"` currently reports "no
changes detected" against these models — confirmed locally against a real
PostgreSQL 17 instance — so the migrations and the models are in sync as
of this phase. Run it again whenever a model changes in a later phase.

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

344 tests total (277 baseline + 67 new in Phase 4B). `SECRET_KEY` must be
set (via `.env`) for the JWT-dependent tests to run — copy
`.env.example` to `.env` first if you haven't.

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

**Admin management (Phase 3B.3)**:

* `tests/integration/test_admin_management.py` — real JWTs, real
  database-backed Users, real HTTP requests through `/api/v1/admins*` and
  `/api/v1/auth/signup`. Covers every item in the brief's Authorization/
  Workflow/Approval/Lifecycle/Multiple-Admins/Department-Transfer/Self-
  Protection/System-Admin-Protection/Race-Safety lists, including a
  genuine two-thread/two-connection concurrency test for the ADMIN-purpose
  signup path (mirroring Phase 3A's USER-purpose one) and row-level
  assertions proving a department transfer never rewrites a historical
  Letter's `recipient_department_id`.

**User management (Phase 3B.4)**:

* `tests/integration/test_user_management.py` — real JWTs, real
  database-backed Users, real HTTP requests through `/api/v1/users*` and
  `/api/v1/auth/signup`. Covers every item in the brief's Authorization/
  Workflow/Listing/Details/Approval/Deactivation/Reactivation/Revocation/
  Cross-Department-Security/Self-Protection/Lifecycle/Race-Safety lists —
  the first test file in this project where the caller is a
  department-scoped `ADMIN` rather than a global `SYSTEM_ADMIN`, so
  cross-department rejection is exercised against a real resource for the
  first time (`test_admin_cannot_get_user_in_another_department` and
  siblings), alongside a genuine two-thread/two-connection concurrency
  test for the USER-purpose signup path issued by an Admin.

**Letter registry / Category / Classification (Phase 4B)**:

* `tests/integration/test_letter_registry.py` (50 tests) — real JWTs,
  real database-backed Users/Departments/Categories/Classifications, real
  HTTP requests through `/api/v1/letters*`. Covers every lettered item
  (A-X) in the brief's test list: field mapping, recipient-department
  derivation, optional source department, required sender details,
  reference-number handling, category/classification validation,
  `recorded_by` protection, department isolation (including that a
  cross-department `GET` returns `404`, not `403`), the classified-access
  boundary exercised across recorder/same-department-non-recorder/Admin/
  SYSTEM_ADMIN, full CRUD, and a row-level proof that
  `recipient_department_id` survives a recording Admin's later department
  transfer (mirroring the Phase 3B.3/3B.4 historical-preservation tests).
  A pre-commit hardening pass replaced the three reference-number
  *uniqueness-rejection* tests with tests proving the opposite
  (duplicates currently succeed, `201` not `409`) after the global
  uniqueness constraint they exercised was found to be an unconfirmed
  assumption and removed — see
  `docs/architecture/letter-registry.md` §14.
* `tests/integration/test_category_management.py` (8),
  `test_classification_management.py` (9) — SYSTEM_ADMIN-only CRUD
  authorization and essentials, mirroring
  `test_department_management.py`'s shape; `restricts_access`
  toggling is covered in the Classification file, its actual
  *enforcement* against real Letters in `test_letter_registry.py`.

`tests/unit/test_imports.py` needs no database — it runs `from app.models
import X` in fresh subprocesses to guard against the circular-import
regression fixed in Phase 2 (see `docs/database/schema.md` §1). It always
runs.
