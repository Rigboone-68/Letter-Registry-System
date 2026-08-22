# Department Management — Phase 3B.2

**Status: complete.** System Admin-controlled department lifecycle: create,
list, retrieve, update, activate, deactivate. This document does not cover
Admin assignment, Admin management, or User management/approval — those
are Phase 3B.3/3B.4, not implemented here; see §11.

## 1. Department lifecycle

```text
SYSTEM ADMIN
    ↓
Create Department  →  ACTIVE
    ↓
(later) Admin(s) assigned — Phase 3B.3, not implemented yet
    ↓
Admins manage their department — Phase 3B.3/3B.4, not implemented yet
    ↓
SYSTEM ADMIN may Deactivate  →  INACTIVE  (reversible — Activate  →  ACTIVE)
```

A department is **never physically deleted** through normal application
functionality — this was already true of the Phase 2 schema (`Department`
rows have no delete endpoint and the model's foreign keys are all
`RESTRICT`, see `docs/database/schema.md`) and this phase adds no delete
operation. `INACTIVE` is the only "removal" a department can undergo, and
it's fully reversible.

## 2. System Admin authority

Every department-management endpoint requires `require_system_admin`
(`app/api/deps.py`, Phase 3B.1) — ADMIN and USER receive `403` for all six
operations, with the same generic message every other authorization
failure in this codebase uses. See
`docs/architecture/authorization.md`, "Error behavior" — unchanged here,
not reinvented.

## 3. Create / list / retrieve / update behavior

### Create — `POST /api/v1/departments`

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Trimmed; blank (after trimming) rejected; max 255 chars |
| `code` | No | Trimmed; empty string becomes `None`; max 50 chars; **no format assumed** — S&IT has not confirmed a coding convention (`docs/database/schema.md` §7), so this schema doesn't invent one |

`id`, `status`, `created_at`, `updated_at` have **no field at all** on the
request schema (`app/schemas/department.py:DepartmentCreate`) — not merely
ignored if sent. The schema additionally sets `extra="forbid"`, so a
request that tries to inject any of them is rejected outright with `422`,
the same pattern `SignupRequest` (Phase 3A) established. A new department
is always created `ACTIVE` — the brief asked for a "strong documented
reason" to use any other default, and none exists.

### List — `GET /api/v1/departments`

Returns every department (both `ACTIVE` and `INACTIVE`) unless narrowed
with `?status=ACTIVE` or `?status=INACTIVE`. Response shape:

```json
{"items": [ {"id": "...", "name": "...", "code": "...", "status": "...", "created_at": "...", "updated_at": "..."}, ... ], "total": N}
```

An envelope (`items`/`total`), not a bare array — this is the "structure
the response so pagination can be added later without redesigning the
domain layer" requirement (brief §6): adding `page`/`page_size`/
`next_cursor` later only ever means new fields on this same model, never a
change to the response's fundamental shape. **No pagination is implemented
in this phase** — the brief said not to unless the existing architecture
already required it, and it doesn't yet at this data volume.

### Retrieve — `GET /api/v1/departments/{department_id}`

Returns the same six fields as list; `404` if no department has that id.
Does **not** return associated `users`/`letters`/etc. — that's explicitly
later administrative functionality (brief §7), not this phase's concern.

### Update — `PATCH /api/v1/departments/{department_id}`

Only `name` and `code` are editable here; `status` is **not** — it has its
own dedicated endpoints (§4) so a status change is always an explicit,
separately-authorized action, never a side effect of an unrelated rename.
At least one of `name`/`code` must be supplied (`422` otherwise).

**Known limitation**: `name`/`code` of `None` means "leave unchanged", not
"clear the field" — there is currently no way to clear an already-set
`code` back to `null` through this endpoint (only to overwrite it with a
different, non-empty value). This is a deliberate simplicity tradeoff, not
an oversight; see `app/services/department_service.py:update_department`'s
docstring. Extending this would mean distinguishing "field omitted" from
"field explicitly set to null" in the request schema, a small but real
complexity increase not justified without a concrete need for it yet.

## 4. Activation / deactivation

`POST /api/v1/departments/{department_id}/activate` and `.../deactivate`
are the **only** way to change a department's `status` — the generic
update endpoint above cannot. Both are **idempotent** (brief §9's
preferred option): activating an already-`ACTIVE` department, or
deactivating an already-`INACTIVE` one, returns `200` with the
department's current state rather than an error. A caller never needs to
check current status first.

Deactivation:

* Does **not** delete the `Department` row, or any `User`, `UserAuthorization`,
  `Letter`, `LetterDocument`, `Notification`, or `AuditLog` row that
  references it.
* Does **not** reassign, deactivate, or otherwise touch any User (regular
  or Admin) belonging to that department.
* **Does** change what department-bound ADMIN/USER accounts can do while
  it's `INACTIVE` — see §5. This is an authorization-time effect, not a
  data change; nothing about the affected Users' own rows is modified.

## 5. Inactive department: security behavior (brief §11)

This is the one place this phase touches Phase 3B.1's authorization layer,
and the change is deliberately small:
`app/services/authorization.py:assert_department_access` now checks two
things for ADMIN/USER (SYSTEM_ADMIN is unaffected — see below), not one:

1. The requested `department_id` matches the caller's own
   `user.department_id` (unchanged from Phase 3B.1).
2. **New in this phase**: that department's `status` is `ACTIVE`.

```python
if user.role == UserRole.SYSTEM_ADMIN:
    return
if user.department_id is None or user.department_id != department_id:
    raise DepartmentAccessDeniedError()
if user.department is not None and user.department.status != ActiveStatus.ACTIVE:
    raise DepartmentAccessDeniedError()
```

`user.department` is read via the `User.department` SQLAlchemy
relationship that already existed (Phase 2) — no new repository method, no
session parameter added to this function's signature, no second query
built by hand. This is the "small extension… do not redesign the entire
authorization system" the brief asked for.

**Consequences:**

* An ADMIN or USER whose department becomes `INACTIVE` gets the same
  generic `403` from `require_department_access` (and, later, from any
  resource-level check built on `assert_department_access` — see
  `docs/architecture/authorization.md` §4) as someone trying to access a
  department that was never theirs. **Not distinguished** — deliberately,
  same reasoning as every other authorization denial in this codebase
  (`docs/architecture/authorization.md`, "Error behavior"): the response
  never reveals whether the department doesn't exist, isn't theirs, or is
  theirs-but-inactive.
* **They cannot work around this by supplying a different `department_id`**
  — that was already rejected before this phase (a different id is never
  their own), and remains rejected for an unrelated reason now too. There
  is no combination of client-supplied values that regains access.
* **SYSTEM_ADMIN is completely unaffected.** The role check returns
  immediately, before either of the two conditions above is evaluated —
  SYSTEM_ADMIN can still reach `GET /api/v1/departments/{id}` (the
  management endpoint) and any future departmental resource for an
  `INACTIVE` department, which is exactly what "existing records remain
  accessible to SYSTEM_ADMIN for historical/administrative purposes"
  (brief §11) requires.
* **Reactivating restores access immediately** — there is no cached
  decision anywhere; the very next request re-evaluates `user.department.status`
  fresh. Verified in
  `tests/integration/test_department_management.py::test_reactivating_department_restores_operational_access`
  and manually, live, against `lrs_dev` (see `docs/PROJECT_STATUS.md`,
  "Validation performed").
* **User account status is untouched.** A User in an `INACTIVE` department
  is not deactivated, not logged out, and can still authenticate
  (`get_current_user` only checks the User's *own* `status`, unrelated to
  their department's) — they simply fail any department-scoped
  authorization check until either they're moved to a different active
  department or their department is reactivated. This is deliberate: the
  brief was explicit that deactivating a department must not delete or
  modify User records, and changing `user.status` would have been exactly
  that.

No real protected resource exercises this yet beyond the same Phase 3B.1
verification-only endpoint
(`GET /api/v1/auth/test/department/{department_id}`,
`app/api/v1/endpoints/dev_authz_test.py`) — see
`docs/architecture/authorization.md` §7 for why that endpoint exists and
when it should be retired.

## 6. Validation and duplicate detection

`name`/`code` normalization happens once, in
`app/schemas/department.py` (`_normalize_name`/`_normalize_code`), the
single place either rule is defined — not duplicated between create and
update.

**Duplicate detection does not pre-check.** `DepartmentService` never
calls `find_by_name` before inserting or updating; it always attempts the
write and lets PostgreSQL's own unique constraints
(`uq_departments_name`, `uq_departments_code`) be the single source of
truth, catching the resulting `IntegrityError`. A check-then-insert would
have the same TOCTOU race window Phase 3A's `UserAuthorization`
consumption was written to specifically avoid (brief §5, "handle race
conditions where two requests attempt to create the same department
simultaneously") — two concurrent requests could both pass a pre-check
before either commits. Relying on the database's own constraint, which
PostgreSQL enforces atomically regardless of concurrency, is both simpler
and actually race-safe.

`app/services/department_service.py:_raise_for_integrity_error` inspects
*which* constraint fired (via psycopg2's `IntegrityError.orig.diag.constraint_name`)
to raise a specific, accurate exception —
`DuplicateDepartmentNameError` or `DuplicateDepartmentCodeError` — mapped
to `409` with a message naming the actual conflicting field. Unlike
login/signup (Phase 3A), where deliberately vague errors defend against
account enumeration on a public-facing form, this is an internal,
System-Admin-only administrative tool: naming which field conflicted is
normal, expected UX with no comparable security cost.

### A schema bug found and fixed while building this

`Department.name`/`Department.code` used SQLAlchemy's `unique=True` column
shorthand (Phase 2), which lets the DDL backend auto-name the resulting
constraint however it prefers. `Base.metadata.create_all()` (builds the
`lrs_test` schema used by the automated test suite) and the original Phase
2 Alembic migration (builds `lrs_dev` and any real deployment) picked
*different* auto-generated names for the same constraint — harmless until
this phase started reading the constraint name to report which field
conflicted, at which point duplicate-detection tests failed against
`lrs_test` while passing against `lrs_dev`. Fixed by naming both
constraints explicitly in `app/models/department.py`'s `__table_args__`
(`uq_departments_name`, `uq_departments_code` — matching the migration's
existing names exactly), so `create_all()` and the migration now produce
byte-identical DDL. `alembic check` still reports zero drift against the
real, migration-built schema. The identical latent issue still exists on
`categories.name` and `classifications.name` (both still use the
`unique=True` shorthand) — **not fixed here**, since nothing in this phase
depends on their constraint names; the same technique applies if a future
phase (Category/Classification management) ever needs it there.

## 7. API endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/departments` | SYSTEM_ADMIN | Create |
| `GET` | `/api/v1/departments` | SYSTEM_ADMIN | List, optional `?status=` filter |
| `GET` | `/api/v1/departments/{id}` | SYSTEM_ADMIN | Retrieve |
| `PATCH` | `/api/v1/departments/{id}` | SYSTEM_ADMIN | Update name/code |
| `POST` | `/api/v1/departments/{id}/activate` | SYSTEM_ADMIN | Idempotent |
| `POST` | `/api/v1/departments/{id}/deactivate` | SYSTEM_ADMIN | Idempotent |

## 8. Error handling

| Situation | Status |
|---|---|
| No/invalid/expired/tampered JWT | `401` |
| Valid JWT, not SYSTEM_ADMIN | `403` (generic message, unchanged from Phase 3B.1) |
| Department id doesn't exist (retrieve/update/activate/deactivate) | `404` |
| Duplicate name or code (create/update) | `409`, names the conflicting field |
| Blank name / no fields on update / server-controlled field injected | `422` |

No PostgreSQL exception, SQL statement, or stack trace is ever exposed —
every database-level failure is caught in
`app/services/department_service.py` and translated into one of the
domain exceptions above before it reaches the API layer.

## 9. Transactions

Create/update/activate/deactivate each run inside one transaction: the
service flushes, and on `IntegrityError` explicitly rolls back before
raising a clean domain exception — no partial write is ever committed. On
success, the service commits once and refreshes the ORM object so the
response reflects exactly what PostgreSQL now has stored. Same pattern
`app/services/auth_service.py`/`bootstrap_service.py` established in
Phase 3A; not a new transaction-handling approach.

## 10. Audit events — planned, not implemented (brief §21)

No automatic audit logging exists in this phase, matching the brief's
explicit instruction. The `AuditLog` table (Phase 2) has nothing writing
to it yet. Once a later phase adds automatic audit generation, department
management is expected to produce these events:

* `DEPARTMENT_CREATED`
* `DEPARTMENT_UPDATED`
* `DEPARTMENT_ACTIVATED`
* `DEPARTMENT_DEACTIVATED`

This extends the list already scoped in
`docs/architecture/authorization.md` §12 — not a second, competing list.

## 11. Explicitly NOT implemented (belongs to later phases)

* **Admin assignment / Admin management (Phase 3B.3)** — no endpoint here
  lets a SYSTEM_ADMIN attach an ADMIN to a department, or manage Admin
  accounts at all.
* **User management / approval (Phase 3B.4)** — no endpoint here approves
  a `PENDING_APPROVAL` account, deactivates/reactivates a User, or issues
  a `UserAuthorization`.
* **Automatic reassignment of Users when a department is deactivated** —
  never happens; see §4.
* **Frontend department management UI** — brief §24 explicitly excludes
  it; none was built.
* **Pagination** — see §3, "List".
* **Clearing an already-set `code` back to `null` via `PATCH`** — see §3,
  "Update", "Known limitation".
* **System Admin handover** — unrelated to this phase; still deferred per
  `docs/architecture/authentication.md` §9.
