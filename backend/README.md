# LRS Backend

FastAPI service for the Letter Registry System. **Phase 4B: Letter
Registry Core — implemented, with a pre-commit hardening pass applied on
top. Phase 4C: Registry Operations & Search — implemented. Phase 4D:
Document Management — implemented, on top of this phase's own
architecture review. Phase 4E: Operational Activity, Notifications &
Audit — implemented, on top of this phase's own architecture
review.** This backend is now the complete, authoritative V1
implementation — Phase 5 reviewed the frontend that will eventually
expose it (no backend file was touched; see
`docs/architecture/frontend.md`). Builds on Phase 4A's architecture
review and the
fully-delivered Phase 3B (Roles & Access Management: authentication,
RBAC/department isolation, department management, Admin management, User
management). Full design in `docs/architecture/authentication.md` (auth),
`docs/architecture/authorization.md` (RBAC/department isolation),
`docs/architecture/department-management.md` (department CRUD),
`docs/architecture/admin-management.md` (Admin lifecycle),
`docs/architecture/user-management.md` (User lifecycle),
`docs/architecture/letter-registry.md` (the six finalized business
decisions and the resulting Letter/Category/Classification design — a
department-scoped Letter registry with recipient/source department
separation, required sender details, a required reference number (no
uniqueness constraint — its scope was never confirmed and was removed
after an initial global-uniqueness assumption; see §14 of that doc),
exactly three seeded Categories, and a real, documented-as-provisional
classified-access authorization boundary),
`docs/architecture/registry-search.md` (Phase 4C: pagination, explicit
whitelisted sorting, and seven case-insensitive text-search filters on
`GET /api/v1/letters`, implemented only after fixing a real architectural
risk that phase's own review found first — the letter list used to
filter classified records out in Python *after* fetching them, which
would have let a paginated `total` leak how many inaccessible records
existed; the fix moved that check into the SQL query itself before any
pagination code was written), and `docs/architecture/document-management.md`
(Phase 4D: `LetterDocument` upload/list/download —
`POST`/`GET /api/v1/letters/{letter_id}/documents`,
`GET .../{document_id}` — with a server-generated, UUID-based storage
path that never trusts client input, layered file-type/size validation
(extension allowlist then an authoritative magic-byte content
signature), and an authorization chain that reuses
`assert_letter_access`/`LetterService.get_letter` rather than a new
document-level check, so classified-letter protection extends to its
documents automatically. No schema change was needed; there is still no
document deletion endpoint of any kind — a deliberate scope decision,
not a gap. See §33 of that doc for the full implementation record), and
`docs/architecture/audit-notifications.md` (Phase 4E: `AuditLog`
generation — append-only, mandatory/same-transaction, targeted old/new
field pairs, never a full row snapshot — wired into Letter/Document/
User/Admin/Department/Category/Classification/Authorization lifecycle
events; `Notification` generation for the one confirmed V1 trigger
("letter registered"), best-effort via a database `SAVEPOINT` so a
failure there can never block the letter itself, with deliberately
generic message text; `GET/PATCH /api/v1/notifications*` scoped
unconditionally to the caller's own notifications. No schema change was
needed; there is still no audit-viewing API — a deliberate scope
decision, not a gap. See §31 of that doc for the full implementation
record). Dashboards and an audit read API are still not implemented —
see `docs/architecture/overview.md` §4 for exactly what is and isn't in
place.

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
to `assert_letter_access`), the document endpoints
(`/api/v1/letters/{letter_id}/documents*` — upload/list/download, any
role that can already access the parent Letter, including SYSTEM_ADMIN
cross-department; no deletion endpoint), Category/Classification
management endpoints (`/api/v1/categories*`, `/api/v1/classifications*`,
SYSTEM_ADMIN only), the notification endpoints (`/api/v1/notifications*` —
any authenticated role, always scoped to the caller's own notifications),
five verification-only authorization endpoints under
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
| `app/models/` | SQLAlchemy models — 9 core entities (see `docs/database/schema.md`); `Letter`/`Classification` extended in Phase 4B; `LetterDocument` unchanged since Phase 2 — Phase 4D needed no schema change |
| `app/schemas/auth.py` | Signup/login/token/current-user request-response contracts |
| `app/schemas/department.py` | Department create/update/response/list-envelope contracts — no server-controlled field (`id`/`status`/timestamps) is ever accepted from a client |
| `app/schemas/admin.py` | Admin-authorization/response/list-envelope/department-transfer contracts — same no-server-controlled-field guarantee |
| `app/schemas/user.py` | User-authorization/response/list-envelope contracts (Phase 3B.4) — `UserAuthorizationCreate` has no `department_id` field at all (always derived from the calling Admin), unlike `AdminAuthorizationCreate` |
| `app/schemas/letter.py` | Letter create/update/response/list-envelope contracts (Phase 4B) — no `recipient_department_id`/`recorded_by`/`status` field on `LetterCreate` |
| `app/schemas/category.py`, `app/schemas/classification.py` | Category/Classification create/update/response/list-envelope contracts (Phase 4B) — same no-server-controlled-field guarantee; `Classification` additionally carries `restricts_access` |
| `app/schemas/document.py` | `DocumentResponse`/`DocumentListResponse` (Phase 4D) — no `storage_path` field exists on the response at all, `LetterDocument`'s equivalent of never serializing `password_hash`; no `DocumentCreate` schema (upload is a multipart file field, not a JSON body) |
| `app/schemas/notification.py` | `NotificationResponse`/`NotificationListResponse`/`UnreadCountResponse` (Phase 4E) — no `recipient_user_id` field anywhere a client could set; no request schema at all (generation is always server-side, triggered by a business event) |
| `app/api/deps.py` | `get_current_user` (authentication) plus `require_system_admin`/`require_admin`/`require_admin_or_system_admin`/`require_user_or_admin`/`require_department_access` (authorization) |
| `app/api/v1/router.py` | Aggregate v1 router |
| `app/api/v1/endpoints/auth.py` | `/auth/signup`, `/auth/login`, `/auth/me` |
| `app/api/v1/endpoints/departments.py` | `/departments*` — SYSTEM_ADMIN only |
| `app/api/v1/endpoints/admins.py` | `/admins*` — SYSTEM_ADMIN only |
| `app/api/v1/endpoints/users.py` | `/users*` — ADMIN only, scoped to the caller's own department (Phase 3B.4); includes the project's first authorization-revocation endpoint |
| `app/api/v1/endpoints/letters.py` | `/letters*` (Phase 4B) — `POST` is USER/ADMIN only; every other route accepts any authenticated role, with the actual department/classified-access decision made inside `LetterService`, not the route dependency |
| `app/api/v1/endpoints/categories.py`, `app/api/v1/endpoints/classifications.py` | `/categories*`, `/classifications*` (Phase 4B) — SYSTEM_ADMIN only, mirroring `departments.py` exactly |
| `app/api/v1/endpoints/documents.py` | `/letters/{letter_id}/documents*` (Phase 4D) — nested under Letter on purpose, so the letter-first authorization chain is structurally unavoidable; every route uses `get_current_user` only (no `require_user_or_admin`), since the real decision is `LetterService.get_letter`'s `assert_letter_access`, exactly the same one-check-not-two principle `letters.py` already established. No delete route |
| `app/api/v1/endpoints/notifications.py` | `/notifications*` (Phase 4E) — `get_current_user` only, unconditionally scoped to `current_user` for every role including SYSTEM_ADMIN (ownership, not role/department, is the whole access rule); no `recipient_user_id` query parameter exists anywhere |
| `app/api/v1/endpoints/dev_authz_test.py` | `/auth/test/*` — verification-only, not business functionality (see `docs/architecture/authorization.md` §7) |
| `app/services/auth_service.py` | Signup and login business logic — role now derived from `UserAuthorization.purpose` (Phase 3B.3) |
| `app/services/bootstrap_service.py` | First-System-Admin creation logic (called by `app/cli.py`) |
| `app/services/authorization.py` | `assert_department_access` — the one framework-agnostic department-isolation rule, reused by `app/api/deps.py`, genuinely exercised as a resource-level check first in Phase 3B.4 (User) and again in Phase 4B (Letter). Extended in Phase 3B.2 to require the caller's department be `ACTIVE`; extended in Phase 4B with `assert_letter_access`/`can_view_letter` (single-resource classified-access check) and in Phase 4C with `letter_visibility_filter` (the same rule, re-expressed as a SQL predicate for `list_letters` — see `app/repositories/letter_repository.py`) |
| `app/services/department_service.py` | Department CRUD business logic, including race-safe duplicate-name/code handling |
| `app/services/admin_service.py` | Admin authorization/approval/lifecycle/department-transfer business logic |
| `app/services/user_service.py` | User authorization/approval/lifecycle/revocation business logic, scoped to the calling Admin's own department (Phase 3B.4) |
| `app/services/letter_service.py` | Letter create/read/update/archive business logic (Phase 4B) — `recorded_by`/`recipient_department_id` always derived from the caller; reference-number/source-department/category/classification validation. `list_letters` (Phase 4C) adds pagination/sorting/search, raising `InvalidDateRangeError` for a reversed `received_from`/`received_to` |
| `app/services/category_service.py`, `app/services/classification_service.py` | Category/Classification CRUD business logic (Phase 4B), mirroring `department_service.py` |
| `app/services/document_service.py` | Upload/list/get business logic (Phase 4D) — reuses `LetterService.get_letter` for authorization rather than a parallel check; write-then-commit-with-compensation ordering (file written before the DB row is committed; a DB failure after a successful write deletes the now-orphaned file) |
| `app/services/audit_service.py` | `AuditService.record` (Phase 4E) — the single, reusable audit-write mechanism; only `flush()`es, never `commit()`s/`rollback()`s, so a failure surfaces inside the caller's own transaction and fails the whole operation (mandatory, by design) |
| `app/services/notification_service.py` | `NotificationService` (Phase 4E) — `notify_letter_registered` (the one confirmed V1 trigger; recipient department's ACTIVE Admins, a PROVISIONAL default), wrapped in a database `SAVEPOINT` so a failure can never block the Letter transaction it rides alongside; plus recipient-scoped list/unread-count/mark-read/mark-all-read |
| `app/services/document_storage.py` | Server-controlled filesystem paths (Phase 4D) — `STORAGE_PATH` resolved to an absolute path fresh on every call (never cached), `<letter_uuid>/<document_uuid>.<ext>` built entirely from server-generated UUIDs and a fixed MIME-to-extension map, atomic temp-file-then-rename writes |
| `app/services/document_validation.py` | Layered file-type/size validation (Phase 4D) — extension allowlist, size limit, then an authoritative magic-byte content-signature check (hand-rolled, no `python-magic`/libmagic dependency); client-supplied `Content-Type` is never consulted |
| `app/services/exceptions.py` | Service-layer domain errors, mapped to HTTP responses in the endpoint layer |
| `app/repositories/user_repository.py` | The only code that queries `User` — extended in Phase 3B.3 with `find_admin_by_id`/`list_admins`/`update_status`/`update_department`, and in Phase 3B.4 with `find_user_by_id`/`list_users`, rather than a new repository each time |
| `app/repositories/user_authorization_repository.py` | The only code that queries `UserAuthorization`, including the race-safe `SELECT ... FOR UPDATE` signup consumes, (Phase 3B.3) `create`/`find_unresolved`, and (Phase 3B.4) `find_by_id`/`list_by_department`/`revoke` |
| `app/repositories/department_repository.py` | The only code that queries `Department` |
| `app/repositories/letter_repository.py` | The only code that queries `Letter` (Phase 4B). `find_by_id` eagerly loads `classification` for `assert_letter_access`. `list_letters` (Phase 4C) builds one filtered `stmt` and derives both the `COUNT` and the paginated `items` query from it — never two independently-built queries that could disagree about which rows are visible; `SORTABLE_COLUMNS` is the explicit sort-field whitelist |
| `app/repositories/category_repository.py`, `app/repositories/classification_repository.py` | The only code that queries `Category`/`Classification` (Phase 4B) |
| `app/repositories/letter_document_repository.py` | The only code that queries `LetterDocument` (Phase 4D). `find_by_id_and_letter` is scoped by *both* ids at once, so a document that exists under a different letter 404s identically to one that doesn't exist |
| `app/repositories/audit_log_repository.py` | The only code that queries `AuditLog` (Phase 4E) — insert-only: no `update`/`delete` method exists, and none should ever be added |
| `app/repositories/notification_repository.py` | The only code that queries `Notification` (Phase 4E) — every method except `create` is scoped by `recipient_user_id`, so recipient isolation lives here once rather than being re-checked ad hoc per endpoint |
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

Six migrations exist: `3da4b7ee8167_core_schema_...` (baseline — every
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
rows), `c887ab35e4a3_remove_premature_reference_number_...` (a
same-phase hardening-pass correction: drops
`uq_letters_reference_number` — the finalized decision confirmed
reference numbers "must be unique" but never confirmed the scope, and
global was an unconfirmed guess that a real multi-department registry
could easily violate legitimately; see
`docs/architecture/letter-registry.md` §2.3/§14), and
`9fa970ffa560_add_letters_reference_number_index_...` (Phase 4C: re-adds
a plain, non-unique index on `reference_number` — lost when its unique
constraint was dropped — since reference-number search is a real Phase
4C requirement). All six are described in `docs/database/schema.md`.
**None of Phase 3A (authentication), 3B.1 (RBAC/department authorization),
3B.2 (department management), 3B.4 (User management), 4D (document
management), or 4E (audit/notification) required a schema change** —
every column either needed already existed from Phase 2, or (Phase 3B.4)
from Phase 3B.3's `purpose` column and Phase 2's own
`AuthorizationStatus.REVOKED` enum value, which simply had no endpoint
setting it until now, or (Phase 4D) already existed on `LetterDocument`
since the Phase 2 baseline, or (Phase 4E) `AuditLog`/`Notification` were
both already fully structured for this since the Phase 2 baseline —
Phase 4E is the first phase to actually write rows to either table.
Phase 3B.2 did fix a constraint-*naming* inconsistency in
`app/models/department.py` (see `docs/database/schema.md` §2.1) — a
Python-model-only change, not a migration, since the real database
already had the correct name. Phase 3B.3, Phase 4B (two migrations), and
Phase 4C (one migration) are the only phases since Phase 2's hardening
pass to need one; `alembic check` confirms zero drift after all six, and
still confirms zero drift after Phase 4D and Phase 4E (no seventh
migration was ever added).

```bash
alembic upgrade head       # apply all six, in order
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
pytest tests/
```

458 tests total (277 baseline + 67 in Phase 4B + 43 in Phase 4C + 38 in
Phase 4D + 33 new in Phase 4E). `SECRET_KEY` must be set (via `.env`) for
the JWT-dependent tests to run — copy `.env.example` to `.env` first if
you haven't. Scope the invocation to `tests/` (not a bare `pytest`) —
`app/api/v1/endpoints/dev_authz_test.py`'s
filename incidentally matches pytest's default `*_test.py` discovery
pattern, and a bare `pytest` run from `backend/` will also try (and fail)
to collect its route-handler functions as test functions. This is a
pre-existing environment quirk, not a Phase 4D regression — confirmed by
running the identical bare `pytest` invocation against the tree before
this phase's changes and observing the same collection error.

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
  `test_department_management.py`'s shape; `restricts_access` toggling
  is covered in the Classification file, its actual *enforcement*
  against real Letters (single-get) in `test_letter_registry.py` and
  (search/list, including the count-leakage regression) in
  `test_letter_search.py`.

**Registry Operations & Search (Phase 4C)**:

* `tests/integration/test_letter_search.py` (43 tests) — real JWTs,
  real database-backed Letters (via the `make_letter` factory, not the
  HTTP create endpoint, for efficient multi-row setup), real HTTP
  requests through `GET /api/v1/letters`. Covers pagination (defaults,
  custom page/page_size, out-of-range rejection, beyond-last-page),
  sorting (all four whitelisted fields, both directions, invalid-field
  rejection, stable ordering via the secondary id-sort), all seven
  text-search filters (case-insensitive contains, no-result case), the
  three exact filters, inclusive date-range filtering (including
  reversed-range rejection), multi-filter `AND` combination, department
  isolation (including that a client-supplied `department_id` is
  silently ignored for USER/ADMIN, never expanding their scope), and —
  highest priority — the classified-access query-level fix:
  `test_classified_record_excluded_from_total_count` and
  `test_classified_record_excluded_across_all_pages` directly prove an
  inaccessible letter can no longer inflate `total` or occupy a page
  slot, the exact regression this phase's own architecture review
  identified as the reason to fix the query *before* adding pagination.

**Document management (Phase 4D)**:

* `tests/integration/test_document_management.py` (38 tests) — real
  JWTs, real database-backed Letters, real HTTP requests through
  `/api/v1/letters/{letter_id}/documents*`. An autouse `storage_root`
  fixture redirects `STORAGE_PATH` to a per-test `tmp_path`, the
  filesystem equivalent of `db_session`'s per-test rollback isolation —
  no test ever writes into the real `storage/letters/` tree. Covers file
  acceptance (PDF/JPEG/PNG/TXT) and rejection (bad extension, HTML, MIME
  spoofing, malformed content, oversized, empty), path security (five
  malicious-filename variants plus a direct containment-check test),
  authorization (USER/ADMIN own vs. other department, SYSTEM_ADMIN
  cross-department, classified-letter recorder vs. non-recorder,
  wrong-letter/document pairing, nonexistent letter/document), historical
  integrity (deactivated uploader still represented, archived letters
  keep their documents and stay downloadable), storage guarantees
  (UUID-based server-controlled path, no `storage_path` in any response,
  no static route exposes storage), and failure handling (a simulated
  DB failure after a successful write deletes the orphaned file; a
  simulated storage failure creates no DB row; a normal upload leaves
  exactly one file).

**Audit / notifications (Phase 4E)**:

* `tests/integration/test_audit.py` (21 tests) — real JWTs, real
  database-backed Letters/Users/Departments/Admins/Categories/
  Classifications, real HTTP requests through the existing endpoints.
  Verifies `AuditLog` rows are actually created with the correct actor/
  target/values for Letter (created/updated/archived/classification-
  changed/category-changed), Document (uploaded), User (approved/
  deactivated/reactivated), Admin (department-changed), Department
  (created/activated/deactivated), Category/Classification (created/
  deactivated), and Authorization (created/revoked) events; that the
  actor is always the caller, never the target; that only targeted old/
  new field pairs are stored, never a full row snapshot or sensitive
  values (`text_content`, `password_hash`); that a simulated audit
  failure rolls back the entire business operation; and that no
  audit-mutation endpoint exists anywhere.
* `tests/integration/test_notifications.py` (12 tests) — same pattern,
  through `/api/v1/letters` (registration) and `/api/v1/notifications*`.
  Verifies the "letter registered" trigger creates one notification per
  ACTIVE Admin in the recipient department (and none for an inactive
  Admin, another department's Admins, or the plain-User recorder);
  strict recipient isolation on every read/write (a mismatched id 404s;
  unread counts and `read-all` never cross users); a simulated failure
  *inside* the notification's `SAVEPOINT` is logged and does not block
  the Letter's own commit; the generated `message` never contains Letter
  content; and a deactivated recipient's notification remains in the
  database but becomes unreachable (not deleted).

`tests/unit/test_imports.py` needs no database — it runs `from app.models
import X` in fresh subprocesses to guard against the circular-import
regression fixed in Phase 2 (see `docs/database/schema.md` §1). It always
runs.
