# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Current Phase

**Phase 3A — Authentication Foundation & Account Lifecycle.** Complete.

Phase 3A delivered local email/password authentication, JWT access tokens,
the account lifecycle (`PENDING_APPROVAL`/`ACTIVE`/`DEACTIVATED`), the
authorized-signup workflow against `UserAuthorization`, and a CLI bootstrap
for the first System Admin. Full design in
`docs/architecture/authentication.md`.

**Not in scope for this phase, and not added:** role/department
authorization decorators, department management, Admin user-management
APIs, letter CRUD, dashboards, document uploads, notification generation,
the System Admin handover workflow, or a full frontend authentication UI —
see "Pending" below and `docs/architecture/authentication.md` §14.

## Completed

### Phase 3A — Authentication foundation

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

### Corrections applied (self-review hardening pass)

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

Nothing — Phase 3A is complete and the project is paused pending explicit
instruction to begin Phase 3B, per the standing project rule that phases
are reviewed before the next begins.

## Pending (Phase 3B and later)

* **Full RBAC enforcement** — role/department authorization decorators or
  dependencies deciding what an authenticated caller may do, not just who
  they are.
* **Department management** — API/UI for System Admin to create, rename,
  or deactivate departments.
* **Admin management** — API/UI for System Admin to manage Admin accounts.
* **User approval APIs/UI** — an Admin approving a `PENDING_APPROVAL`
  account into `ACTIVE`, and issuing `UserAuthorization` records in the
  first place (both currently require direct database access).
* **System Admin handover workflow** — see
  `docs/architecture/authentication.md` §9.
* **Frontend authentication UI** — login/signup pages, protected routing,
  token storage. See `docs/architecture/authentication.md` §15 for why
  this was deliberately not started in Phase 3A.

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
  — confirmed during this phase's manual verification (it reads directly
  from the console). Not a bug: arguably a desirable property, since it
  stops a password from being accidentally scripted into a piped command.
  The automated test suite calls `create_system_admin` directly rather than
  the interactive CLI wrapper for this reason.

## Next Recommended Phase

**Phase 3B — RBAC & Administrative Authorization**, per the brief that
scoped this phase: role/department authorization decorators or
dependencies built on top of `get_current_user`; Admin endpoints to approve
`PENDING_APPROVAL` accounts and issue `UserAuthorization` records; and the
System Admin handover workflow. Recommended before Letter CRUD (Phase 4),
since department-isolation enforcement — the core security requirement the
Phase 2 schema was built around — has an authenticated identity to derive
`department_id` from as of Phase 3A, but nothing yet that *checks* it
against an action, which is exactly what Phase 3B adds.
