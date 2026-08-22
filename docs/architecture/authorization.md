# Authorization — Phase 3B.1

**Status: complete** (first slice of Phase 3B). This document covers the
RBAC foundation and department-isolation enforcement built in this phase.
It does not cover department management, Admin management, user approval,
or any real protected business resource (Letter CRUD, etc.) — those are
later Phase 3B slices; see §11.

> **Phase 3B.2 update**: `assert_department_access` (§3) gained one small,
> additional condition — an ADMIN/USER's own department must also be
> `ACTIVE` — when department deactivation was introduced. The rule
> described below is otherwise unchanged; see
> `docs/architecture/department-management.md` §5 for the addition and why
> it belongs there rather than here.

## Authentication vs. authorization

These are two different questions, answered by two different layers:

| | Question | Answered by | Phase |
|---|---|---|---|
| **Authentication** | "Who are you?" | `get_current_user` (`app/api/deps.py`) — validates the JWT, loads the `User` row from PostgreSQL, confirms `status == ACTIVE` | 3A |
| **Authorization** | "What are you allowed to do?" | `require_system_admin` / `require_admin` / `require_admin_or_system_admin` / `require_user_or_admin` / `require_department_access` (`app/api/deps.py`), and `assert_department_access` (`app/services/authorization.py`) | 3B.1 (this phase) |

Every authorization dependency in this phase is built **on top of**
`get_current_user`, via FastAPI's own `Depends()` composition — none of
them re-implement token decoding or the ACTIVE-status check. There is
exactly one place either happens, unchanged from Phase 3A.

## 1. Role hierarchy

```text
SYSTEM_ADMIN
    ↓
Department
    ↓
ADMIN
    ↓
USER
```

Unchanged from `docs/architecture/overview.md` — this document is about
*enforcing* that hierarchy in code, not redefining it.

## 2. Role permissions (what's enforced now vs. later)

| Role | Enforced in this phase | Not yet implemented (later Phase 3B slices) |
|---|---|---|
| **SYSTEM_ADMIN** | Passes every role check; bypasses department isolation entirely (`assert_department_access` returns immediately for this role — see §3) | Creating/managing departments (3B.2), assigning Admins (3B.3) |
| **ADMIN** | Passes `require_admin`/`require_admin_or_system_admin`; can access only their own `department_id` via `require_department_access`/`assert_department_access` | Managing Users in their department, authorizing signups, approving/deactivating/reactivating Users (3B.3/3B.4) |
| **USER** | Passes `require_user_or_admin`; can access only their own `department_id` | Creating/editing letters (Phase 4) |

No API in this phase performs any of the "not yet implemented" actions —
only the reusable checks that a future endpoint doing so would call are
built here.

## 3. Department isolation

**The rule** (brief §4, §8), implemented in exactly one place —
`app/services/authorization.py:assert_department_access(user, department_id)`:

```text
SYSTEM_ADMIN → always allowed, regardless of department_id (including None)
ADMIN        → allowed only if department_id == user.department_id
USER         → allowed only if department_id == user.department_id
otherwise    → DepartmentAccessDeniedError (→ HTTP 403)
```

This function is framework-agnostic — no FastAPI import, no knowledge of
requests or paths. That is deliberate: it is meant to be called from two
different kinds of places without the rule ever being duplicated between
them (brief §14, "do not duplicate authorization logic across endpoints"):

1. **URL-parameter case** — `app/api/deps.py:require_department_access`, a
   thin FastAPI dependency for endpoints where the department being acted
   on is literally a path parameter (`/department/{department_id}` in this
   phase's test endpoints). FastAPI resolves `department_id` from the path
   the same way it would for the endpoint function itself, because the
   dependency declares a parameter of that name.
2. **Resource-level case** (§4 below) — a future service that has already
   loaded a row (a `Letter`, say) calls
   `assert_department_access(current_user, letter.department_id)` directly,
   with no path parameter involved at all.

### System Admin special case

`SYSTEM_ADMIN.department_id` is always `NULL` (enforced at the database
level since Phase 2 by `ck_users_role_department_pairing`). Because the
role check happens *first* and returns immediately, no line in
`assert_department_access` ever compares `user.department_id` to anything
for a SYSTEM_ADMIN caller — there is no code path here that assumes
`user.department_id` is set. `tests/unit/test_authorization.py::test_system_admin_can_access_a_none_department_target`
exists specifically to pin this down: even a target `department_id` of
`None` must not raise for a SYSTEM_ADMIN.

### Not an existence check

The rule is a plain equality (`department_id == user.department_id`), not
"does this department exist in the database." A fabricated, entirely
made-up UUID is rejected in exactly the same way, with exactly the same
response, as a real department that simply isn't the caller's — see
`tests/integration/test_authorization.py::test_user_cannot_gain_access_via_fabricated_nonexistent_department_uuid`.
This is intentional: distinguishing "that department doesn't exist" from
"that department isn't yours" would leak which department UUIDs are real.

## 4. Resource-level authorization pattern (for future phases)

No protected business resource exists yet in this phase (brief explicitly
excludes Letter CRUD). The pattern future resources should use, once one
exists, is:

```python
# inside a future service, e.g. app/services/letter_service.py
letter = self.letters.find_by_id(letter_id)
if letter is None:
    raise LetterNotFoundError()
assert_department_access(current_user, letter.department_id)
# ... proceed
```

The department to check comes from the **loaded row**, not from any
client-supplied field — see §5. `assert_department_access` is exactly the
same function `require_department_access` calls for the path-parameter
case in this phase; a future resource reuses it rather than reimplementing
the SYSTEM_ADMIN-bypass/equality rule a second time.

## 5. Do not trust client-provided department (brief §7)

**For ADMIN and USER, `user.department_id` — the value on the
authenticated caller's own row, loaded from PostgreSQL — is the only
authoritative department context**, except for an explicit System-Admin
operation. A client can send whatever it wants in a request body or query
string; nothing in this phase (or the pattern it establishes for later
phases) ever treats a client-supplied `department_id` as the department to
*act as*, only, at most, as a value to *check* against the caller's own.

Concretely, once a future endpoint like `POST /letters` exists:

* The letter's `department_id` must be derived from `current_user.department_id`
  server-side — never read from the request body, the way
  `AuthService.signup` (Phase 3A) already derives a new User's
  `department_id` from the `UserAuthorization` row, never from the signup
  request. **Not implemented yet** — no letter-creation endpoint exists in
  this phase; this is the pattern it must follow when it does.
* Where a client-supplied `department_id` legitimately appears at all (a
  path parameter identifying *which* department's resources to list, say),
  it is only ever used to *check* access via `assert_department_access`,
  never accepted as-is to *establish* ownership of a new or existing row.

## 6. Error behavior (brief §12)

| Situation | Status | Detail |
|---|---|---|
| No/invalid/expired/tampered JWT | `401` | `"Could not validate credentials."` (unchanged from Phase 3A) |
| Valid JWT, account not `ACTIVE` | `401` | Same as above — deliberately indistinguishable from "no token at all" (Phase 3A decision, reused here) |
| Valid JWT, `ACTIVE`, wrong role | `403` | `"You do not have permission to perform this action."` |
| Valid JWT, `ACTIVE`, correct role, wrong department | `403` | Same generic message |

**One fixed 403 message for every role and department failure** — see
`app/api/deps.py:_FORBIDDEN_ERROR`. It never names the role that was
required, the department that was requested, or the caller's own
department. This is what brief §12's "do not expose unnecessary
information such as 'Department ABC exists but you cannot access it'"
means in practice:
`tests/integration/test_authorization.py::test_department_access_denial_response_is_generic`
asserts the response body contains neither department's id nor name.

## 7. Protected development/verification endpoints

`app/api/v1/endpoints/dev_authz_test.py` — **not business functionality**.
There is no real protected resource in this phase for the authorization
dependencies to attach to (no Letter CRUD, no department/Admin/User
management endpoints), so five minimal routes exist solely to exercise the
full dependency chain over real HTTP with real JWTs:

```text
GET /api/v1/auth/test/system-admin
GET /api/v1/auth/test/admin
GET /api/v1/auth/test/admin-or-system-admin
GET /api/v1/auth/test/user-or-admin
GET /api/v1/auth/test/department/{department_id}
```

Each does nothing but apply one dependency and echo the caller's own
profile. Tagged `dev-authorization-test` (not `auth`) in the OpenAPI
schema so `/docs` visually separates them from the real authentication
endpoints. No frontend exists or is planned for them.

**These should be deleted or repurposed once Phase 4 adds a real
protected resource** (e.g. Letter CRUD) — at that point, tests should
target the real endpoint instead, and these five stop serving a purpose.

## 8. Architecture

```text
API (app/api/v1/endpoints/)
        ↓
Dependencies / Authorization (app/api/deps.py, app/services/authorization.py)
        ↓
Services (app/services/)
        ↓
Repositories (app/repositories/)
        ↓
SQLAlchemy → PostgreSQL
```

Same layering as Phase 3A (`docs/architecture/overview.md` §5), extended
rather than replaced. Role checks live directly in `app/api/deps.py` as
FastAPI dependency functions (they're a single attribute comparison on the
already-authenticated `User`, with no business logic worth extracting).
The department-isolation *rule* lives in `app/services/authorization.py`,
framework-agnostic, precisely so it is reusable from both a FastAPI
dependency (this phase) and a plain service function (a future phase) —
see §3, §4.

## 9. Security assumptions

* **The frontend is never a security boundary.** Every check in this
  document runs server-side, in the backend, unconditionally — nothing
  here depends on what a client sends beyond the credentials/parameters
  needed to make the decision. There is no frontend code in this phase at
  all (brief §16).
* **Role and department come from the database, not the client or the
  token's claims.** `get_current_user` loads a fresh `User` row from
  PostgreSQL on every request; every dependency in this phase reads
  `current_user.role`/`current_user.department_id` from that freshly
  loaded row. The JWT does carry `role`/`department_id` claims (Phase 3A,
  for a possible future fast-path), but nothing in this phase trusts them
  — see `app/api/deps.py`'s module docstring.
* **No hard-coded user identities or department IDs anywhere in
  application code.** Every example in this document and its tests
  creates its own department/user data; nothing references a fixed UUID.

## 10. What is explicitly NOT implemented yet

* Department CRUD (create/rename/deactivate a department).
* Admin management (System Admin assigning/managing Admins).
* User management/approval APIs (an Admin approving a `PENDING_APPROVAL`
  account, deactivating/reactivating a User, issuing `UserAuthorization`
  records).
* Letter CRUD or any other real protected resource — §4's pattern is
  documented for when one exists, not implemented against one now.
* File uploads, dashboards, notification generation.
* Frontend functionality of any kind (brief §16).
* System Admin handover.
* Automatic audit logging of authorization-sensitive actions — see §12.

## 11. Future authorization work (Phase 3B.2+)

Per the brief's phase breakdown:

* **Phase 3B.2 — Department Management**: System Admin CRUD for
  departments, using `require_system_admin`.
* **Phase 3B.3 — Admin Management**: System Admin assigning/managing
  Admin accounts.
* **Phase 3B.4 — User Management & Approval**: Admin approving
  `PENDING_APPROVAL` accounts into `ACTIVE`, deactivating/reactivating
  Users, issuing `UserAuthorization` records — using
  `require_admin_or_system_admin` plus `require_department_access`/
  `assert_department_access` so an Admin can only act on their own
  department's Users.
* **Phase 4 — Letter CRUD**: the first real consumer of §4's
  resource-level pattern, and of §5's "derive department server-side"
  rule for letter creation.

## 12. Audit logging — not implemented, but scoped

Brief §15 is explicit: no automatic audit logging in this phase. The
`AuditLog` table already exists (Phase 2) with nothing writing to it yet.
Actions that will eventually need an audit event, once the operations that
perform them exist:

* Admin authorization of a User (issuing a `UserAuthorization`)
* User approval (`PENDING_APPROVAL` → `ACTIVE`)
* User deactivation
* User reactivation
* Admin assignment (System Admin granting/revoking the ADMIN role)
* Department creation
* Department deactivation
* System Admin handover

None of these operations exist yet (see §10), so there is nothing to wire
audit logging into in this phase.
