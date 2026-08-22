# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Current Phase

**Phase 3B.2 — Department Management.** Complete (second slice of Phase
3B).

Phase 3B.2 delivered System-Admin-only department CRUD (create, list,
retrieve, update, activate, deactivate) and a small, documented extension
to Phase 3B.1's department-isolation check so an `INACTIVE` department's
Admin/User accounts lose department-scoped access without any change to
their own account rows. Full design in
`docs/architecture/department-management.md`.

**Not in scope for this phase, and not added:** Admin assignment/
management, User management/approval APIs, letter CRUD, file uploads,
dashboards, notification generation, frontend functionality, or System
Admin handover — see "Pending" below and
`docs/architecture/department-management.md` §11.

## Completed

### Phase 3B.2 — Department management

* **Department CRUD, SYSTEM_ADMIN only** — `POST`/`GET`/`PATCH
  /api/v1/departments`, `.../{id}`, `.../{id}/activate`,
  `.../{id}/deactivate`. New departments are always `ACTIVE`; `status` is
  never editable through the generic update endpoint, only through the
  two dedicated, idempotent activate/deactivate endpoints.
* **Race-safe duplicate detection** — no pre-check; every create/update
  attempts the write and relies on PostgreSQL's own unique constraints,
  catching `IntegrityError` and reporting exactly which field
  (`name`/`code`) conflicted via `409`.
* **Historical data preserved on deactivation** — no User, Letter, or any
  other row is deleted, modified, or reassigned when a department becomes
  `INACTIVE`; verified directly (row-by-row) in tests, not just asserted.
* **Inactive-department authorization extension** —
  `assert_department_access` (Phase 3B.1) now also requires an
  ADMIN/USER's own department to be `ACTIVE`; SYSTEM_ADMIN is completely
  unaffected and retains full access to inactive departments for
  historical/administrative purposes. Reactivating a department restores
  access immediately, with no cached decision anywhere.
* **A real schema-naming bug found and fixed** (not a migration —
  `alembic check` still reports zero drift): `Department.name`/`code`'s
  unique constraints were unnamed (`unique=True` shorthand), so the test
  database (`Base.metadata.create_all()`) and the real, migration-built
  database silently used different auto-generated constraint names. Fixed
  by naming both explicitly to match the existing migration. The same
  latent issue remains on `categories.name`/`classifications.name`,
  documented but not fixed (out of this phase's scope).
* **36 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Creation/Retrieval/
  Update/Status/Security lists, plus a full live-server verification
  against `lrs_dev` (creation → duplicate rejection → list/get/update →
  deactivate-blocks-user → reactivate-restores-access).
* **Documentation**: `docs/architecture/department-management.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, `docs/architecture/authorization.md`,
  and `docs/database/schema.md`.

### Phase 3B.1 — RBAC & department authorization

* **Role-check dependencies** (`app/api/deps.py`) —
  `require_system_admin`, `require_admin`, `require_admin_or_system_admin`,
  `require_user_or_admin`, each composed on top of `get_current_user` via
  FastAPI's own `Depends()` mechanism, never re-deciding authentication.
* **Department-isolation enforcement** — `assert_department_access`
  (`app/services/authorization.py`, framework-agnostic — no FastAPI
  import) and its FastAPI wrapper `require_department_access`
  (`app/api/deps.py`). SYSTEM_ADMIN bypasses; ADMIN/USER must match their
  own `department_id` exactly — not an existence check, a made-up UUID is
  rejected identically to a real foreign one.
* **Generic, non-leaking 403s** — one fixed message for every role/
  department authorization failure; never names the role required, the
  department requested, or the caller's own department.
* **Five verification-only endpoints**
  (`app/api/v1/endpoints/dev_authz_test.py`, tagged
  `dev-authorization-test` in OpenAPI, no frontend) — exist solely because
  no real protected resource exists yet in this phase for the
  authorization dependencies to attach to; documented for removal once
  Phase 4 adds one.
* **42 new automated tests**: 16 in `backend/tests/unit/test_authorization.py`
  (pure function/dependency logic, no database) and 26 in
  `backend/tests/integration/test_authorization.py` (real JWTs, real
  database-backed Users, real HTTP requests — including every scenario in
  the brief's Role/Department/Deactivation/Negative-security test lists).
* **Documentation**: `docs/architecture/authorization.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3A — Authentication foundation (see previous entries below for detail)

* **Local email/password authentication** — no external OAuth provider;
  see `docs/architecture/authentication.md` §1.
* **Argon2id password hashing** via `argon2-cffi`, centralized password
  policy (8-128 characters), never a manual hash comparison.
* **JWT access tokens** (PyJWT, HS256, `SECRET_KEY`-signed) — creation,
  validation, expiration, and rejection of tampered/malformed/`alg:none`
  tokens.
* **Bootstrap System Admin** — `python -m app.cli create-system-admin`,
  refuses to run if an active System Admin already exists.
* **Authorized signup** — `POST /api/v1/auth/signup`, race-safe
  consumption of `UserAuthorization` (`SELECT ... FOR UPDATE`), role/
  department/status always derived server-side, never client-supplied.
* **Pending-approval account lifecycle** — new accounts start
  `PENDING_APPROVAL` and cannot log in until (a future phase's) Admin
  approval.
* **Login** — `POST /api/v1/auth/login`, account-enumeration-resistant,
  status-aware (pending/deactivated rejected with distinct messages after
  a correct password, not before).
* **Current-user endpoint** — `GET /api/v1/auth/me`, backed by
  `get_current_user` (`app/api/deps.py`), the identity-establishment
  dependency Phase 3B's authorization checks will build on.
* **65 new automated tests** across `backend/tests/unit/test_security.py`,
  `test_email_utils.py`, and `backend/tests/integration/test_auth_bootstrap.py`,
  `test_auth_signup.py`, `test_auth_login.py`, `test_auth_current_user.py`
  — including a genuine two-thread/two-connection concurrency test proving
  the signup race-condition fix.
* **Documentation**: `docs/architecture/authentication.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 2 — Database architecture (see previous entries below for detail)

* 9 core SQLAlchemy models, two Alembic migrations (baseline + hardening),
  31 model-level tests. Full detail in `docs/database/schema.md`.

### Corrections applied during Phase 2 (self-review hardening pass)

A self-review of the initial Phase 2 implementation found six issues,
addressed as follows — see `docs/database/schema.md` for the technical
detail behind each:

| # | Issue | Fix |
|---|---|---|
| 1 | Order-dependent circular import: `from app.models import X` (or `from app.models.user import X`) could fail in a fresh interpreter depending on what had already been imported | `app/database/base.py` no longer imports `app.models`; consumers that need full metadata (`alembic/env.py`, `tests/conftest.py`) import it themselves. Guarded by `tests/unit/test_imports.py` |
| 2 | ORM-level `session.delete(department)` didn't cleanly hit the database's `RESTRICT` — SQLAlchemy tried to null out dependent users' `department_id` first, which instead tripped an unrelated CHECK constraint | `passive_deletes="all"` added to every `RESTRICT`/`SET NULL`-backed one-to-many relationship (Department, Category, Classification, User, and `Letter.notifications`), so the ORM defers entirely to the database's own FK action |
| 3 | `departments.status` had no index, unlike the equivalent column on Category/Classification | Added (`ix_departments_status`) |
| 4 | `notifications.is_read` had no database-level default — a row written outside the ORM would fail `NOT NULL` | Added `server_default=false()`, alongside the existing ORM-side default |
| 5 | `letter_documents.uploaded_by` had no index, unlike every other User-referencing FK in the schema | Added (`ix_letter_documents_uploaded_by`) |
| 6 | The role/department `CHECK` constraint hardcoded role strings, duplicating `UserRole`'s values | Model-side constraint now built from `UserRole.*.value`; the migration's own copy is deliberately still a literal (migrations are frozen snapshots) — see `app/models/user.py` docstring |

### Validation performed — Phase 3B.2

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1 (`lrs_dev` for manual checks, `lrs_test` for the suite
— never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **174 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.2 required no schema change (the constraint-naming fix changed only how the model declares an existing constraint, not the constraint itself) |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1 tests re-run as part of the full suite | All still pass — no regression |
| Full department CRUD, run for real against `lrs_dev` via `curl` with a real minted SYSTEM_ADMIN JWT | Create → `201`; duplicate name → `409`; list/get/update → correct data; server-controlled-field injection → `422` |
| Full deactivate/reactivate cycle, run for real against `lrs_dev` with a real minted USER JWT in that department | User could access their department (`200`) → SYSTEM_ADMIN deactivated it → same User blocked (`403`) → SYSTEM_ADMIN reactivated it → same User restored (`200`), all against the live server, not `TestClient` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.1

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A (`lrs_dev` for manual checks, `lrs_test` for the suite —
never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **138 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged from Phase 3A) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.1 required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A authentication tests re-run as part of the full suite | All still pass — no regression |
| Full role/department authorization matrix, run for real against `lrs_dev` (SYSTEM_ADMIN/ADMIN/USER × own/other department, via `curl` with real minted JWTs) | Every case matched the documented rule exactly — including the two explicit attack attempts (ADMIN and USER each tried another department's real UUID) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3A

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2 (`lrs_dev` for manual checks, `lrs_test` for the suite — never
a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **96 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — see Known Limitations) |
| `alembic check` | "No new upgrade operations detected" — Phase 3A required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Bootstrap CLI, run for real against `lrs_dev` | Created a SYSTEM_ADMIN with no department, ACTIVE status, hashed password; a second run was correctly refused |
| `POST /auth/login` for the bootstrapped admin | Returned a valid JWT; `GET /auth/me` with it returned the correct profile |
| Full signup flow via real HTTP against `lrs_dev` | Authorized email → `201`, `PENDING_APPROVAL`; unauthorized email → `403`; role-injection attempt → `422`; login while pending → `403` with the correct message; authorization row confirmed `USED` afterward |
| Tampered JWT / missing token via `curl` | Both `401` |
| Frontend build (`npm run build`) | Succeeds — untouched this phase, verified as still working |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 2 (for reference)

| Check | Result |
|---|---|
| `alembic upgrade head` against `lrs_dev` | Both migrations applied cleanly |
| `alembic downgrade base` → `alembic upgrade head` | Full round-trip verified after the hardening migration was added |
| `alembic revision --autogenerate` after upgrading | "No new upgrade operations detected" — migrations match models exactly |
| `pytest` against `lrs_test` | 31 passed, 0 failed, 0 warnings |
| `from app.models import User` / `from app.models.user import User` in fresh interpreters | Both succeed (previously order-dependent) |
| FastAPI app startup + `GET /health` | 200 OK, using the real `lrs_dev` connection string |
| Empirical FK behavior (raw SQL and ORM-level, against `lrs_dev`, transactional/cleaned up) | `RESTRICT` blocks Department/User deletion with a clean FK error; `CASCADE` removes LetterDocument/Notification rows when their Letter is deleted |

## In Progress

Nothing — Phase 3B.2 is complete and the project is paused pending
explicit instruction to begin the next slice, per the standing project
rule that phases are reviewed before the next begins.

## Pending (Phase 3B.3+ and later)

* **Admin management (Phase 3B.3)** — API/UI for System Admin to assign/
  manage Admin accounts. `require_system_admin` already exists for this
  to use.
* **User approval APIs/UI (Phase 3B.4)** — an Admin approving a
  `PENDING_APPROVAL` account into `ACTIVE`, deactivating/reactivating
  Users, and issuing `UserAuthorization` records in the first place (all
  currently require direct database access).
  `require_admin_or_system_admin` + `require_department_access`/
  `assert_department_access` already exist for these to use, so an Admin
  can only be allowed to act on their own department's Users.
* **Letter CRUD and any other real departmental business resource (Phase
  4)** — the first phase that will call `assert_department_access`
  against something other than a management/verification resource; see
  `docs/architecture/authorization.md` §4 for the pattern it should
  follow.
* **System Admin handover workflow** — see
  `docs/architecture/authentication.md` §9.
* **Automatic audit logging** of authorization-sensitive actions,
  including the four department events scoped in Phase 3B.2
  (`DEPARTMENT_CREATED`/`UPDATED`/`ACTIVATED`/`DEACTIVATED`) — see
  `docs/architecture/authorization.md` §12 and
  `docs/architecture/department-management.md` §10 for the full list.
* **Department list pagination** — deliberately not implemented in Phase
  3B.2, but the response envelope (`{"items": [...], "total": N}`) was
  shaped so adding it later needs no redesign; see
  `docs/architecture/department-management.md` §3.
* **Clearing an already-set department `code` back to `null`** — not
  possible through `PATCH /api/v1/departments/{id}` today; see
  `docs/architecture/department-management.md` §3, "Known limitation".
* **The same `unique=True` constraint-naming issue fixed for Department
  in Phase 3B.2** still exists on `categories.name` and
  `classifications.name`. Not fixed, since nothing currently depends on
  either constraint's name — the same technique applies if a future
  Category/Classification management phase ever needs it.
* **Frontend authentication/authorization/department-management UI** —
  login/signup pages, protected routing, token storage, role-based
  show/hide. See `docs/architecture/authentication.md` §15 for why this
  remains deliberately deferred.

## Pending Confirmation (from S&IT)

None of the following are implemented as final requirements — each is a
documented, minimal, reversible assumption. See `docs/database/schema.md`
§7 for the full reasoning behind each.

* **Official letter/reference number** — existence and format unconfirmed.
  No column exists for it.
* **Sender types** (`letters.received_from`) — not assumed to always be a
  government department; stored as free text.
* **Final category list** — nothing seeded; "Budget/Procurement/HR/Legal/
  Infrastructure" were requirements-gathering examples only.
* **Final classification/priority terminology** — "Important/Classified/
  Routine" were examples only; nothing seeded.
* **Departmental code format** (`departments.code`) — left nullable,
  unformatted.
* **`letters.subject` / `letters.reason` requirement-ness** — both left
  nullable pending confirmation of intake requirements.
* **Document retention requirements** — not addressed; no retention/expiry
  field exists on `letter_documents`.

## Known Limitations

* **No PostgreSQL was available in the initial development environment.**
  One was installed and configured specifically to validate this phase (see
  "Validation performed" above) rather than leaving the migration and test
  suite unverified. In an environment where PostgreSQL is genuinely
  unavailable, `pytest` skips (does not fail) the model tests — see
  `docs/database/README.md`, "Providing a local test database".
* **A pre-existing Phase 1 config bug was fixed during this phase's
  validation.** `backend/app/core/config.py`'s `CORS_ORIGINS` setting
  crashed on startup (`pydantic_settings.exceptions.SettingsError`) when
  `.env` was created by copying `.env.example` exactly as the README
  instructs, because pydantic-settings tried to JSON-decode the documented
  comma-separated value before the field's own validator ran. Fixed with a
  one-line `NoDecode` annotation (see `backend/README.md`, "Configuration").
  This was outside Phase 2's nominal scope (database architecture) but was
  fixed because it silently broke this phase's own "verify the app starts"
  validation step and every documented getting-started instruction.
* **`httpx`/Starlette deprecation warning** on `TestClient` import
  (`Using httpx with starlette.testclient is deprecated; install httpx2
  instead`) — pre-existing, noted in `requirements.txt`'s own comment.
  Not addressed in this phase; harmless for now, but will need resolving
  before Phase 3 adds real API tests.
* **No database-level enforcement of department isolation** — by design,
  deferred to a future service layer. See `docs/architecture/overview.md`
  §3 for why this cannot be a schema-level guarantee.
* **`passive_deletes="all"` (added in the hardening pass) has a documented
  SQLAlchemy caveat**: an object already loaded into a session's identity
  map before its row is removed by the database's own `ON DELETE CASCADE`
  is not automatically expunged or refreshed within that same session —
  `session.get(...)` can return a stale copy until the session is expired
  or a fresh one is used. This is inherent to the pattern, not a bug; see
  `docs/database/schema.md` §1, "ORM deletion behavior", and the test that
  demonstrates it. A future service/repository layer needs to be aware of
  this when deleting a Letter in the same session that will keep running.
* **No refresh tokens or token revocation** (Phase 3A) — a token is valid
  until it expires; deactivating the account it belongs to stops it being
  *useful* immediately (re-checked on every request) but doesn't revoke the
  token itself. See `docs/architecture/authentication.md` §16.
* **`UserAuthorization` records currently require direct database access
  to create** (Phase 3A) — there is no Admin-facing API for this yet; it's
  Phase 3B "Admin management" work. Manual verification of the signup flow
  in this phase created one directly via the ORM for exactly this reason.
* **Bootstrap has no race-condition hardening beyond a single transaction**
  (Phase 3A) — an accepted, documented simplification since it's a rare,
  CLI-only, operator-run action, unlike signup which is fully race-safe.
  See `docs/architecture/authentication.md` §8.
* **`getpass.getpass()` does not accept piped/redirected stdin on Windows**
  — confirmed during Phase 3A's manual verification (it reads directly
  from the console). Not a bug: arguably a desirable property, since it
  stops a password from being accidentally scripted into a piped command.
  The automated test suite calls `create_system_admin` directly rather than
  the interactive CLI wrapper for this reason.
* **No real departmental *business* resource exists yet** — Phase 3B.2
  gave `require_system_admin` its first real resource (departments
  themselves), but `require_department_access`/`assert_department_access`
  (the department-isolation check ADMIN/USER will use) is still only
  proven against the Phase 3B.1 verification-only endpoints
  (`app/api/v1/endpoints/dev_authz_test.py`) — no Letter or other
  departmental business resource exists yet. Not a defect — see
  `docs/architecture/authorization.md` §7, and Phase 4 in "Pending" above.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for both Phase 3B.1 and 3B.2 (brief §15/§21);
  see `docs/architecture/authorization.md` §12 and
  `docs/architecture/department-management.md` §10 for the full list
  scoped for when the relevant actions exist.
* **`Department.name`/`code` needed a constraint-naming fix this phase**
  (Phase 3B.2) — see "Known Limitations" entry below and
  `docs/database/schema.md` §2.1 for the full explanation. No migration
  was required; this was a Python-model-only fix.
* **The same constraint-naming issue is still latent on
  `categories.name`/`classifications.name`** (Phase 3B.2 finding, not
  fixed) — see "Pending" above.
* **A department's `code` cannot be cleared back to `null` via `PATCH`**
  (Phase 3B.2) — only overwritten with a different value. Deliberate
  simplicity tradeoff; see `docs/architecture/department-management.md`
  §3.
* **No pagination on `GET /api/v1/departments`** (Phase 3B.2) — not needed
  at current data volumes; the response envelope was shaped so adding it
  later needs no redesign. See `docs/architecture/department-management.md`
  §3.

## Next Recommended Phase

**Phase 3B.3 — Admin Management**, the next slice of Phase 3B: System Admin
endpoints to assign/manage Admin accounts, using `require_system_admin`
(already built) and department data that can now actually be managed
(Phase 3B.2). Recommended next because Phase 3B.4 (User approval) assumes
Admins exist to eventually take over approval duties from System Admin,
and because departments — the prerequisite Phase 3B.3 needs — are now a
real, manageable resource rather than only seed data. See
`docs/architecture/department-management.md` §11 for the full remaining
Phase 3B/4 sequence.
