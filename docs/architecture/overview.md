# Architecture Overview — Roles, Hierarchy, and Department Isolation

**Status:** Phase 3A complete. This document explains the roles and
hierarchy the database schema is built to support, and (as of Phase 3A)
how a caller's identity is established. Authorization decisions based on
that identity — role/department checks on specific actions — are not yet
implemented; see §4, "What is implemented vs. deferred", and
[`authentication.md`](authentication.md) for the full authentication
design.

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
Will eventually be able to access and manage records across every
department, and to manage Departments, Categories, and Classifications
system-wide. As of Phase 3A, the first System Admin is created by a
server-side CLI bootstrap command, never through public signup — see
[`authentication.md`](authentication.md) §8.

### Admin

Bound to exactly one department (`users.department_id` is required for this
role, same constraint). Will eventually manage that department's Users and
be able to edit that department's Letter records. Also the role required to
authorize new signups via `UserAuthorization` (see
`docs/database/schema.md` §2.3) — though that permission check is a
service-layer rule, not a database constraint, since it depends on *who is
calling*, not on the row's own column values. As of Phase 3A, there is no
API for an Admin to actually create a `UserAuthorization` — that is Phase
3B, "Admin management" (see §4 below).

### User

Also bound to exactly one department. Will eventually be able to register
letters for their own department and edit their own letter records — but
not another department's, and not another user's letters. As of Phase 3A,
a User account is created via signup against an Admin-issued
`UserAuthorization`, starting `PENDING_APPROVAL` and requiring a (not yet
implemented) Admin approval step to become usable — see
[`authentication.md`](authentication.md) §5.

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

**Phase 3A adds the piece this depended on, but not the enforcement
itself.** `get_current_user` (`app/api/deps.py`) now reliably answers "who
is calling, and what is their `department_id`" for any authenticated
request — that identity is exactly what a future Letter/User endpoint
would filter on. Signup already applies the same underlying principle in
its own narrow scope (a new User's `department_id` comes from their
`UserAuthorization`, never from the signup request body — see
[`authentication.md`](authentication.md) §5) but no endpoint in this phase
reads or writes `Letter` rows at all, so there is nothing yet for a
department-isolation filter to actually apply to. That remains Phase 3B/4
work.

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

### Explicitly deferred (not this phase)

* Role/department **authorization** — deciding what an authenticated
  caller is *allowed to do*, as opposed to *who they are* (which Phase 3A
  now answers). No endpoint in this phase makes such a decision because no
  endpoint in this phase needs to.
* Department-isolation query filtering (the "derive `department_id` from
  the authenticated user" enforcement described in §3) — the identity to
  filter on now exists (`get_current_user`), but no Letter/User-management
  endpoint exists yet to apply it to.
* Admin user-management endpoints (approving `PENDING_APPROVAL` accounts,
  deactivating users, issuing `UserAuthorization` records via the API).
* Department management, dashboards, notification generation, file upload
  handling, or audit-log auto-generation.
* Full frontend authentication UI — deliberately deferred, see
  [`authentication.md`](authentication.md) §15.

See `docs/PROJECT_STATUS.md` for the current phase-by-phase plan and what's
pending S&IT confirmation before some of these can be designed.

## 5. Layering rule (unchanged from Phase 1)

```text
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. Phase 2 added the bottom of this stack
(the ORM models). Phase 3A is the first phase to populate every other
layer — `app/api/v1/endpoints/auth.py` (thin, translates service
exceptions to HTTP), `app/services/auth_service.py` /
`bootstrap_service.py` (business rules, transaction boundaries),
`app/repositories/user_repository.py` /
`user_authorization_repository.py` (the only code that queries `User`/
`UserAuthorization`) — using this same structure rather than inventing a
second one, per the brief's explicit instruction.
