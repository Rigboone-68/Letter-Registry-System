# Architecture Overview — Roles, Hierarchy, and Department Isolation

**Status:** Phase 3B.2 complete. This document explains the roles and
hierarchy the database schema is built to support, how a caller's identity
is established (Phase 3A), how role/department authorization decisions are
enforced on top of that identity (Phase 3B.1), and — as of Phase 3B.2 — the
first real resource that authorization protects: departments themselves.
See §4, "What is implemented vs. deferred",
[`authentication.md`](authentication.md) for authentication,
[`authorization.md`](authorization.md) for the RBAC/department-isolation
design, and [`department-management.md`](department-management.md) for
department CRUD and the inactive-department authorization extension.

## 1. The hierarchy

```text
System Admin
    ↓
Departments
    ↓
Admins
    ↓
Users
    ↓
Letters
```

## 2. Roles

### System Admin

System-wide authority. Not bound to any department —
`users.department_id` is `NULL` for this role (enforced by
`ck_users_role_department_pairing`, see `docs/database/schema.md` §2.2).
As of Phase 3A, the first System Admin is created by a server-side CLI
bootstrap command, never through public signup — see
[`authentication.md`](authentication.md) §8. As of Phase 3B.2, a System
Admin can create, list, retrieve, update, activate, and deactivate
departments (`POST`/`GET`/`PATCH /api/v1/departments...` —
[`department-management.md`](department-management.md)) — the first real
management capability this role has, and the first real resource the
Phase 3B.1 authorization layer protects. Managing Departments' Admins,
Categories, and Classifications remains future work (§4).

### Admin

Bound to exactly one department (`users.department_id` is required for this
role, same constraint). Will eventually manage that department's Users and
be able to edit that department's Letter records. Also the role required to
authorize new signups via `UserAuthorization` (see
`docs/database/schema.md` §2.3) — though that permission check is a
service-layer rule, not a database constraint, since it depends on *who is
calling*, not on the row's own column values. There is still no API for an
Admin to actually create a `UserAuthorization` or manage Users — that is
Phase 3B.3/3B.4 (see §4 below). An Admin is enforced to be able to act
only within their own department — [`authorization.md`](authorization.md)
§3 — and, as of Phase 3B.2, only while that department is `ACTIVE`; see
[`department-management.md`](department-management.md) §5.

### User

Also bound to exactly one department. Will eventually be able to register
letters for their own department and edit their own letter records — but
not another department's, and not another user's letters. A User account
is created via signup against an Admin-issued `UserAuthorization`, starting
`PENDING_APPROVAL` and requiring a (not yet implemented) Admin approval
step to become usable — see [`authentication.md`](authentication.md) §5.
Department-isolation enforcement for a User is in place at the dependency
layer — [`authorization.md`](authorization.md) §3 — ready for Phase 4's
Letter endpoints to use, and, as of Phase 3B.2, also blocks a User's
department-scoped operations whenever their department is `INACTIVE` —
[`department-management.md`](department-management.md) §5 — without
touching the User row itself.

## 3. Department isolation

Department isolation is the core security requirement this schema exists to
support:

* Every departmental entity — `User`, `UserAuthorization`, `Letter` — carries
  a `department_id`.
* A `User`'s own `department_id` is meant to be the **only** source of truth
  for which department's data they can touch, once a service layer exists.
* **This is explicitly not enforced by the database schema itself**, and
  cannot be: nothing stops a single `INSERT` from writing an arbitrary
  `department_id` into `letters`. What the schema *does* guarantee is that
  the column exists, is required (`NOT NULL`), and is indexed
  (`ix_letters_department_id`, plus the composite
  `ix_letters_department_received_at` for the expected "this department's
  letters by date" query) — so that a future service layer has something
  correct and fast to filter on.
* The enforcement point, in a later phase, is: **`department_id` on a new
  Letter (or User, via authorization) is always derived from the
  authenticated caller's own `department_id`, never accepted as client
  input.** A normal User must not be able to pass an arbitrary
  `department_id` in a request body and have it accepted.

This is why the brief for Phase 2 explicitly said "do not rely on frontend
filtering to enforce department isolation" — the schema is designed so
backend-level enforcement (a `WHERE department_id = :current_user_department`
clause added by the service/repository layer, always, not optionally) is
straightforward to add later.

**Phase 3A added the identity this depends on; Phase 3B.1 adds the actual
enforcement mechanism — but still nothing for it to protect yet.**
`get_current_user` (`app/api/deps.py`) reliably answers "who is calling,
and what is their `department_id`" for any authenticated request.
`app/services/authorization.py:assert_department_access` (and its FastAPI
wrapper, `require_department_access`) is now the one reusable place that
turns that identity into an allow/deny decision — SYSTEM_ADMIN bypasses,
ADMIN/USER must match their own `department_id` exactly. Signup already
applies the same underlying principle in its own narrow scope (a new
User's `department_id` comes from their `UserAuthorization`, never from
the signup request body — see [`authentication.md`](authentication.md)
§5), but no endpoint in this phase reads or writes `Letter` rows, so there
is still nothing real for the department-isolation check to be *wired
into* — see [`authorization.md`](authorization.md) §4 for the exact
pattern a future Letter endpoint should call, and §7 for the
verification-only endpoints this phase uses to prove the mechanism works
in the meantime.

## 4. What is implemented vs. deferred

### Implemented (Phase 2 — database)

* Full SQLAlchemy 2.x model layer for all nine core entities (Department,
  User, UserAuthorization, Category, Classification, Letter,
  LetterDocument, Notification, AuditLog) — see `docs/database/schema.md`.
* Two Alembic migrations creating and hardening the complete schema:
  tables, native PostgreSQL enum types, foreign keys, indexes, and
  constraints — see `docs/database/schema.md` §1 and §6 for what the
  second (corrective) migration changed and why.
* Database-level enforcement of: department name/user email/category
  name/classification name uniqueness; the role↔department pairing
  invariant; restrictive foreign keys that prevent orphaning historical
  records, configured so ORM-level deletes surface that restriction
  cleanly rather than attempting to null out dependent rows first (see
  `docs/database/schema.md` §1, "ORM deletion behavior").
* Model-level tests (`backend/tests/integration/test_models.py`, plus
  `backend/tests/unit/test_imports.py` for import-graph regressions), run
  against a real local PostgreSQL instance.

### Implemented (Phase 3A — authentication foundation)

* Local email/password authentication with Argon2id hashing and JWT access
  tokens — no external identity provider. Full design in
  [`authentication.md`](authentication.md).
* `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`,
  `GET /api/v1/auth/me` — the first real API endpoints and the first use
  of the `app/services/` and `app/repositories/` layers.
* `get_current_user` (`app/api/deps.py`) — establishes an authenticated
  request's identity (`User`, freshly loaded and status-checked from the
  database on every call); the foundation Phase 3B's authorization
  decisions will sit on top of, but does not itself make any
  role/department decision.
* Account lifecycle enforcement (`PENDING_APPROVAL`/`ACTIVE`/`DEACTIVATED`)
  at login and on every authenticated request.
* Race-safe signup against `UserAuthorization`, and a CLI bootstrap for the
  first System Admin.

### Implemented (Phase 3B.1 — RBAC & department authorization)

* Role-check dependencies — `require_system_admin`, `require_admin`,
  `require_admin_or_system_admin`, `require_user_or_admin`
  (`app/api/deps.py`) — each composed on top of `get_current_user`, never
  re-deciding authentication.
* Department-isolation enforcement — `assert_department_access`
  (`app/services/authorization.py`, framework-agnostic) and its FastAPI
  wrapper `require_department_access` — SYSTEM_ADMIN bypasses,
  ADMIN/USER must match their own `department_id`. Full design in
  [`authorization.md`](authorization.md).
* Five verification-only endpoints
  (`app/api/v1/endpoints/dev_authz_test.py`) exercising every dependency
  above end-to-end over real HTTP — not business functionality, see
  [`authorization.md`](authorization.md) §7.
* 42 new tests (16 unit, 26 integration against a real PostgreSQL test
  database), including explicit negative-security tests proving a
  client-supplied `department_id` cannot be used to escalate access.

### Implemented (Phase 3B.2 — department management)

* `POST`/`GET`/`PATCH /api/v1/departments`, `.../{id}`,
  `.../{id}/activate`, `.../{id}/deactivate` — SYSTEM_ADMIN only, full
  design in [`department-management.md`](department-management.md).
* `app/services/department_service.py`, `app/repositories/department_repository.py`,
  `app/schemas/department.py` — following the same layered architecture,
  not a second one.
* A small, documented extension to `assert_department_access` (Phase
  3B.1): ADMIN/USER department-scoped operations are now also blocked
  while their department is `INACTIVE`, without modifying any User row —
  [`department-management.md`](department-management.md) §5.
* A schema-level fix (not a migration — see
  [`database/schema.md`](../database/schema.md)): `Department.name`/`code`
  now use explicitly named unique constraints instead of the `unique=True`
  shorthand, so `Base.metadata.create_all()` (test database) and the
  Alembic migration (real database) produce identical constraint names —
  found while building duplicate-detection error messages for this phase.
* 36 new tests against a real PostgreSQL test database, covering every
  item in the brief's Authorization/Creation/Retrieval/Update/Status/
  Security test lists.

### Explicitly deferred (not this phase)

* **Letter CRUD (Phase 4)** is still the first phase that will call
  `assert_department_access` / `require_department_access` against a real
  business resource rather than a verification-only endpoint — Phase
  3B.2's protected resource is departments themselves (a management
  resource), not yet a departmental *business* resource like a Letter.
* Admin management (Phase 3B.3), user approval / `UserAuthorization`
  issuance via API (Phase 3B.4) — the role checks these will use already
  exist (`require_system_admin`, `require_admin_or_system_admin`), but no
  endpoint calling them for these purposes exists yet.
* System Admin handover.
* Dashboards, notification generation, file upload handling, or automatic
  audit-log generation — see [`authorization.md`](authorization.md) §12
  and [`department-management.md`](department-management.md) §10 for
  which future actions will need an audit event once they exist.
* Full frontend authentication/authorization/department-management UI —
  deliberately deferred, see [`authentication.md`](authentication.md) §15;
  unchanged this phase.

See `docs/PROJECT_STATUS.md` for the current phase-by-phase plan and what's
pending S&IT confirmation before some of these can be designed.

## 5. Layering rule (unchanged from Phase 1)

```text
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. Phase 2 added the bottom of this stack
(the ORM models). Phase 3A populated every other layer for the first time
— `app/api/v1/endpoints/auth.py` (thin, translates service exceptions to
HTTP), `app/services/auth_service.py` / `bootstrap_service.py` (business
rules, transaction boundaries), `app/repositories/user_repository.py` /
`user_authorization_repository.py` (the only code that queries `User`/
`UserAuthorization`). Phase 3B.1 added one more layer explicitly named in
the brief — "Dependencies / Authorization", sitting between API and
Services — populated by `app/api/deps.py`'s role-check dependencies and
`app/services/authorization.py`'s framework-agnostic department rule.
Phase 3B.2 adds a second full vertical slice through every layer for a new
resource (`app/api/v1/endpoints/departments.py` →
`app/services/department_service.py` →
`app/repositories/department_repository.py`), reusing the Phase 3B.1
authorization layer rather than duplicating its checks. All of it uses
this same structure rather than inventing a second one, per the brief's
explicit instruction in every phase so far.
