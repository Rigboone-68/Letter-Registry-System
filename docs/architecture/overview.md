# Architecture Overview — Roles, Hierarchy, and Department Isolation

**Status:** Phase 2 complete (database layer only). This document explains
the roles and hierarchy the *database schema* is built to support. No
authentication, authorization middleware, or API endpoints exist yet — see
§4, "What is implemented vs. deferred", below.

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
system-wide.

### Admin

Bound to exactly one department (`users.department_id` is required for this
role, same constraint). Will eventually manage that department's Users and
be able to edit that department's Letter records. Also the role required to
authorize new signups via `UserAuthorization` (see
`docs/database/schema.md` §2.3) — though that permission check is a
service-layer rule, not a database constraint, since it depends on *who is
calling*, not on the row's own column values.

### User

Also bound to exactly one department. Will eventually be able to register
letters for their own department and edit their own letter records — but
not another department's, and not another user's letters.

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

This is why the brief for this phase explicitly says "do not rely on
frontend filtering to enforce department isolation" — the schema is designed
so backend-level enforcement (a `WHERE department_id = :current_user_department`
clause added by the service/repository layer, always, not optionally) is
straightforward to add later, but nothing in Phase 2 adds it yet.

## 4. What is implemented vs. deferred

### Implemented (Phase 2)

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

### Explicitly deferred (not this phase)

* Authentication (JWT, login, signup, password hashing logic).
* Authorization/RBAC middleware — nothing currently checks a request's role
  or department against anything; there are no requests yet.
* Department-isolation query filtering (the "derive `department_id` from the
  authenticated user" enforcement described in §3) — there is no service or
  repository layer yet for this to live in.
* Any API endpoint, Pydantic schema, dashboard, notification generation,
  file upload handling, or audit-log auto-generation.
* Frontend functionality of any kind.

See `docs/PROJECT_STATUS.md` for the current phase-by-phase plan and what's
pending S&IT confirmation before some of these can be designed.

## 5. Layering rule (unchanged from Phase 1)

```text
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. Phase 2 adds the bottom of this stack
(the ORM models Repositories will eventually use) but does not add any
Service, Repository, or API code — those layers remain empty until Phase 3.
