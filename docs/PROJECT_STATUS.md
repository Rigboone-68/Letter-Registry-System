# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Current Phase

**Phase 3B.4 — User Management & Approval.** Complete — the fourth and
final slice of Phase 3B (Roles & Access Management), which is now fully
delivered.

Phase 3B.4 delivered Admin-only User lifecycle management, scoped to the
Admin's own department: authorizing a candidate email, the candidate
signing up through the *existing* signup workflow, the Admin's approval,
deactivate/reactivate, and — the project's first — explicit authorization
**revocation**. This is also the first phase where a department-scoped
role (`ADMIN`, not the global `SYSTEM_ADMIN`) is the caller for every
endpoint, so cross-department isolation (`assert_department_access`,
Phase 3B.1) is exercised as a genuine resource-level check for the first
time. Full design in `docs/architecture/user-management.md`.

**Not in scope for this phase, and not added:** letter CRUD, file uploads,
dashboards, notification generation, frontend functionality, System Admin
handover, or a revoke endpoint for ADMIN-purpose authorizations — see
"Pending" below and `docs/architecture/user-management.md` §12.

## Completed

### Phase 3B.4 — User management

* **User authorization, ADMIN only** — `POST /api/v1/users/authorizations`.
  Unlike Admin authorization, the request has no `department_id` field at
  all — it is always derived from the calling Admin's own department.
  Validates the Admin's own department is `ACTIVE`, the email doesn't
  already belong to an active User, and no unresolved USER authorization
  already exists for it.
* **User signup reuses the existing `/auth/signup` endpoint** — no third
  authentication workflow. Race-safety (`SELECT ... FOR UPDATE`) is
  unchanged from Phase 3A/3B.3 and re-verified for an Admin-issued
  USER-purpose authorization specifically with a genuine two-thread
  concurrency test.
* **User approval** — `POST /api/v1/users/{id}/approve`. Not idempotent,
  same one-time-event reasoning as Admin approval (Phase 3B.3).
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's *own* department to be `ACTIVE`, re-checked on
  every call. Deactivation is unconditional — allowed even if the Admin's
  department has itself been deactivated, a deliberate design decision
  (see "Three isolation strengths" below) since lock-down actions must
  stay possible precisely when a department is in a bad state.
* **Three different isolation strengths, not interchangeable** — read and
  lock-down actions (list/get/deactivate/revoke) require only that the
  target belong to the Admin's own department; state-elevating actions
  (authorize/approve/reactivate) additionally require the Admin's own
  department to be `ACTIVE`. Documented and tested explicitly, not just an
  incidental side effect — see `docs/architecture/user-management.md` §5.
* **The project's first authorization revocation endpoint** —
  `DELETE /api/v1/users/authorizations/{id}`. `AuthorizationStatus.REVOKED`
  has existed since Phase 2 but had no endpoint setting it until now.
  Creator-scoped (only the Admin who created an authorization may revoke
  it — stricter than the department-wide visibility of the listing
  endpoint), idempotent for an already-revoked row, rejected (`409`) for
  an already-used one, and never deletes the row.
* **Cross-department isolation exercised against a real resource for the
  first time** — every prior phase's caller (`SYSTEM_ADMIN`) was global,
  so `assert_department_access` had only ever run against
  verification-only endpoints or short-circuited via the SYSTEM_ADMIN
  bypass. An Admin in Department A gets an identical `404` (not `403`)
  attempting to view, approve, deactivate, or reactivate a User in
  Department B — indistinguishable from that id not existing at all,
  hiding cross-department existence, not merely blocking action on it.
* **User self-protection requires no special-case code** — the same
  structural pattern Phase 3B.3 used for System Admin protection:
  `find_user_by_id` filters by role `USER`, so an Admin's own id (role
  `ADMIN`) 404s on every lifecycle endpoint without a dedicated
  "is this the caller's own id" check.
* **53 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Listing/
  Details/Approval/Deactivation/Reactivation/Revocation/Cross-Department-
  Security/Self-Protection/Lifecycle/Race-Safety lists, plus a full
  live-server verification against `lrs_dev` (authorize → signup →
  pending login rejected → approve → login → access → deactivate → stale
  JWT rejected → reactivate → same stale JWT works again; cross-department
  rejection; revoked authorization cannot sign up).
* **Documentation**: `docs/architecture/user-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3B.3 — Admin management (see previous entries below for detail)

* **Admin authorization, SYSTEM_ADMIN only** —
  `POST /api/v1/admins/authorizations`. Validates the destination
  department exists and is `ACTIVE`, the email doesn't already belong to
  an active Admin, and no unresolved ADMIN authorization already exists
  for it. `authorized_by` is always the caller's own id.
* **Admin signup reuses the existing `/auth/signup` endpoint** — no second
  authentication workflow. Role is derived from whichever authorization is
  found (`purpose=ADMIN` → role `ADMIN`, otherwise role `USER`) — a USER
  authorization can never produce an ADMIN and vice versa, by
  construction. Race-safety (`SELECT ... FOR UPDATE`) is unchanged from
  Phase 3A and re-verified for the ADMIN path specifically with a genuine
  two-thread concurrency test.
* **Admin approval** — `POST /api/v1/admins/{id}/approve`. Not idempotent
  (unlike every other status-changing endpoint in this project so far):
  approving an already-`ACTIVE` or `DEACTIVATED` Admin is rejected with
  `409`, since approval is a one-time event, not a toggle.
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's department to be `ACTIVE`, re-checked on every
  call (even the already-`ACTIVE` idempotent case), since an Admin can end
  up `ACTIVE` while their department is `INACTIVE` (Phase 3B.2
  deactivation never touches `User` rows).
* **Multiple Admins per department, deliberately unbounded** — no
  `department_id UNIQUE` constraint added, per the brief's explicit
  instruction.
* **Admin department transfer, proven historically safe** —
  `Letter.department_id` is independently stored (Phase 2 design), never
  re-derived from the recording user, so moving an Admin between
  departments cannot retroactively change any letter they already
  recorded. Verified directly (row-level assertion after a real transfer),
  not just asserted from the schema.
* **System Admin accounts are structurally unreachable through
  `/api/v1/admins/*`** — a `user_id` resolving to `SYSTEM_ADMIN` gets the
  same `404` as a nonexistent id, via the same repository method
  (`find_admin_by_id`) that filters by role.
* **Admin self-protection requires no special-case code** — every
  Admin-management endpoint is `require_system_admin`-only (reused
  unchanged from Phase 3B.1, no new dependency), so an Admin can never
  reach any of these endpoints regardless of which `user_id` they target,
  including their own.
* **47 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Approval/
  Lifecycle/Multiple-Admins/Department-Transfer/Self-Protection/System-
  Admin-Protection/Race-Safety lists, plus a full live-server verification
  against `lrs_dev` (authorize → signup → pending → approve → login →
  escalation attempts rejected → department transfer → deactivate → old
  token rejected).
* **Documentation**: `docs/architecture/admin-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, and `docs/database/schema.md`.

### Phase 3B.2 — Department management (see previous entries below for detail)

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

### Validation performed — Phase 3B.4 hardening pass

A follow-up pass after Phase 3B.4's own report, scoped to exactly three
things: (1) fix the one flaky test noted in that report, (2) assess
whether the documented "no ADMIN-purpose authorization revocation" gap is
an actual vulnerability, (3) verify the "`AuthorizationStatus.REVOKED`
existed since Phase 2" claim against real git/migration history. No
Letter functionality, frontend, System Admin handover, or new business
functionality was touched.

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **277 passed**, 0 failed, 0 skipped (274 baseline + 3 new regression tests proving the revocation-scope questions below) |
| Full suite re-run 5 times consecutively | 277/277 passed every time — no flakiness |
| `test_me_with_tampered_token_is_rejected` alone, 20 consecutive isolated runs | 20/20 passed — deterministic (was previously observed to fail ~6% of the time) |
| `alembic check` | "No new upgrade operations detected" — this pass touched only test code and documentation, no models or schema |
| `git log` / `git log -p` on `app/models/enums.py` and `backend/alembic/versions/*.py` | Confirmed `AuthorizationStatus.REVOKED` was present in the very first Phase 2 baseline migration (`3da4b7ee8167`, `down_revision=None`) — both the Python enum and the actual PostgreSQL native enum type. Never modified by the hardening migration (`e8a5cea2ccc6`) or the Phase 3B.3 migration (`a223396c9eac`). The Phase 3B.4 report's claim was **accurate**; no documentation correction needed |
| ADMIN-purpose authorization revocation security assessment (7 questions, see `docs/architecture/user-management.md` §13) | **No vulnerability found.** Absence of an ADMIN-purpose revoke endpoint is a documented capability gap, not an exploitable hole — see that section for the full reasoning. Left unimplemented, as instructed |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` was already empty from the prior pass (no new manual
`lrs_dev` verification was needed for this hardening pass, since nothing
it touched is only reachable via a running server).

### Validation performed — Phase 3B.4

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **274 passed**, 0 failed, 0 skipped at the time of the original 3B.4 report. A subsequent hardening pass found and fixed one pre-existing flaky test (`test_me_with_tampered_token_is_rejected`, Phase 3A) — see "Validation performed — Phase 3B.4 hardening pass" below for the corrected, deterministic result (277 passed, 5/5 consecutive full-suite runs) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.4 required no schema change; `AuthorizationStatus.REVOKED` already existed on the enum since Phase 2, this phase is simply the first to set it |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2/3B.3 tests re-run as part of the full suite | All still pass — no regression |
| Full User lifecycle, run for real against `lrs_dev` via real HTTP with real minted JWTs, two departments and two Admins | Authorize (department correctly derived from the Admin, not client-supplied) → `201`; candidate signup → role `USER`, status `PENDING_APPROVAL`; login while pending → `403`; Admin approves → `200`, status `ACTIVE`; login → valid JWT; protected access → `200`; Admin deactivates → `200`; same stale JWT → `401`; Admin reactivates → `200`; same stale JWT → `200` again (status re-checked live, no re-login needed) |
| Cross-department rejection, run for real | Admin A: `GET`/`approve`/`deactivate` on a Department B User all → `404` (not `403` — existence hidden); Admin A's user listing excludes Department B entirely |
| Revocation, run for real | Admin A creates an authorization → Admin B (different department) attempts revoke → `404`; Admin A revokes own authorization → `200`, `REVOKED`; signup attempt against the revoked authorization → `403` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.3

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1/3B.2 (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **221 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic upgrade` → `downgrade` → `upgrade` → `alembic check` | New migration `a223396c9eac` (adds `user_authorizations.purpose`) round-trips cleanly; zero drift afterward |
| Migration backfill, tested against an actual pre-existing row (not just an empty table) | A row inserted via raw SQL *before* the migration ran was correctly backfilled to `purpose='USER'` after `upgrade` |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2 tests re-run as part of the full suite | All still pass — no regression |
| Full Admin lifecycle, run for real against `lrs_dev` via `curl` with real minted JWTs | Authorize → `201`; candidate signup → role `ADMIN`, status `PENDING_APPROVAL`; login while pending → `403`; approve → `200`, status `ACTIVE`; login → valid JWT; Admin attempting to create a department → `403`; Admin attempting to deactivate self → `403`; System Admin department-transfer → `200`; deactivate → `200`; deactivated Admin's still-unexpired token on a subsequent request → `401` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

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

Nothing — Phase 3B.4 is complete, Phase 3B (Roles & Access Management) is
now fully delivered end-to-end, and the project is paused pending explicit
instruction to begin Phase 4, per the standing project rule that phases
are reviewed before the next begins.

## Pending (Phase 4 and later)

* **Letter CRUD and any other real departmental business resource (Phase
  4)** — the first phase that will call `assert_department_access`
  against something other than a management resource (Departments,
  Admins, Users). The isolation pattern itself is now proven end-to-end
  against a real resource (Phase 3B.4); see
  `docs/architecture/authorization.md` §4 and
  `docs/architecture/user-management.md` §5-6 for the pattern Phase 4
  should reuse.
* **A revoke endpoint for ADMIN-purpose `UserAuthorization` rows** — Phase
  3B.4 added revocation only for the USER-purpose path
  (`DELETE /api/v1/users/authorizations/{id}`); a System Admin still
  cannot revoke a still-`ACTIVE`, non-expired ADMIN-purpose authorization.
  The repository layer is already purpose-agnostic
  (`find_by_id`/`list_by_department`/`revoke`), so this needs only a new
  endpoint plus a creator/department check mirroring
  `docs/architecture/user-management.md` §9 — see that section's "Known
  limitations".
* **System Admin handover workflow** — see
  `docs/architecture/authentication.md` §9.
* **Automatic audit logging** of authorization-sensitive actions,
  including the four department events (Phase 3B.2), five Admin events
  (Phase 3B.3), and five User events (Phase 3B.4,
  `USER_AUTHORIZATION_CREATED`/`REVOKED`/`APPROVED`/`DEACTIVATED`/
  `REACTIVATED`) — see `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13, and
  `docs/architecture/user-management.md` §12 for the full list.
* **Department/Admin/User list pagination** — deliberately not
  implemented in any phase so far, but every response envelope
  (`{"items": [...], "total": N}`) was shaped so adding it later needs no
  redesign; see `docs/architecture/department-management.md` §3.
* **Clearing an already-set department `code` back to `null`** — not
  possible through `PATCH /api/v1/departments/{id}` today; see
  `docs/architecture/department-management.md` §3, "Known limitation".
* **The same `unique=True` constraint-naming issue fixed for Department
  in Phase 3B.2** still exists on `categories.name` and
  `classifications.name`. Not fixed, since nothing currently depends on
  either constraint's name — the same technique applies if a future
  Category/Classification management phase ever needs it.
* **An email can be authorized as an Admin (or User) candidate while it
  already belongs to an active User (or Admin)** — a narrow, accepted edge
  case in both directions, not a security issue (the existing
  duplicate-email check at signup already prevents any real
  inconsistency); see `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **Frontend authentication/authorization/department/Admin/User-
  management UI** — login/signup pages, protected routing, token storage,
  role-based show/hide. See `docs/architecture/authentication.md` §15 for
  why this remains deliberately deferred.

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
* **`UserAuthorization` records no longer require direct database access
  to create** (resolved: ADMIN-purpose via Phase 3B.3, USER-purpose via
  Phase 3B.4) — both now go through `/api/v1/admins/authorizations` and
  `/api/v1/users/authorizations` respectively. Kept here for history: this
  entry described a real gap during Phase 3A, when manual verification of
  the signup flow had to create an authorization directly via the ORM.
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
  themselves), and Phase 3B.4 finally exercised
  `assert_department_access` as a genuine cross-department, resource-level
  check (User accounts) rather than only the Phase 3B.1 verification-only
  endpoints. Departments/Admins/Users are all still *management*
  resources, though — no Letter or other departmental *business* resource
  exists yet. Not a defect — see `docs/architecture/authorization.md` §7,
  `docs/architecture/user-management.md` §5-6, and Phase 4 in "Pending"
  above.
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
* **No way to revoke a still-`ACTIVE`, non-expired ADMIN-purpose
  `UserAuthorization`** (Phase 3B.3 gap, still open after Phase 3B.4) — no
  endpoint sets one to `REVOKED`. The equivalent USER-purpose gap was
  closed in Phase 3B.4 (`DELETE /api/v1/users/authorizations/{id}`); the
  repository layer behind it is already purpose-agnostic, so an
  Admin-management equivalent needs only a new endpoint. See
  `docs/architecture/user-management.md` §12, "Known limitations".
* **An email can be authorized as an Admin candidate while already
  belonging to an active User, and vice versa** (Phase 3B.3/3B.4) —
  narrow, accepted edge case in both directions; see
  `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for Phase 3B.1/3B.2/3B.3/3B.4 (brief
  §15/§21/§25, and this phase's own scope boundary); see
  `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13, and
  `docs/architecture/user-management.md` §12 for the full list scoped for
  when the relevant actions exist.
* **RESOLVED (Phase 3B.4 hardening pass) — `test_me_with_tampered_token_is_rejected`
  (Phase 3A) was occasionally flaky on a full-suite run.** Root cause
  confirmed empirically (5,000-trial script): the old technique flipped
  the *last base64 character* of a 32-byte HMAC-SHA256 signature to a
  fixed value ('A', or 'B' if already 'A'). That character's low 2 bits
  are base64 padding, discarded on decode; 'A' (`000000`) and 'B'
  (`000001`) differ only in that discarded bit. Whenever the signature's
  real trailing 4 bits already happened to be `0000` (the last char
  already 'A', ~1/16 of random signatures — measured 6.10% empirically),
  the "fall back to B" branch silently produced a byte-identical
  signature, so the server correctly accepted it and the test's `401`
  assertion failed. This was a **test-construction bug, not a JWT
  verification weakness** — `app/core/security.py:decode_access_token`
  was never modified. The test now decodes the signature to raw bytes,
  XORs one real byte, and re-encodes (`_tamper_signature`,
  `tests/integration/test_auth_current_user.py`) — verified deterministic
  across 5,000 trials and 20 consecutive isolated test runs.

## Next Recommended Phase

**Phase 4 — Letter Registry Core.** Phase 3B (Roles & Access Management)
is now fully delivered end-to-end: System Admin manages departments
(3B.2) and Admins (3B.3); Admins manage Users within their own department
(3B.4). A complete, tested population of `ACTIVE` Users, Admins, and
departments can now be built entirely through the API, with no direct
database access required for any account-lifecycle step. Phase 4 is
recommended next because it is the first phase that adds a real
departmental *business* resource (the Letter itself) for
`assert_department_access` to protect — see
`docs/architecture/authorization.md` §4 and
`docs/architecture/user-management.md` §5-6 for the isolation pattern it
should reuse, now proven end-to-end against a real resource rather than
only verification-only endpoints or other management resources.
