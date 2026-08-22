# User Management & Approval — Phase 3B.4

**Status: complete.** Admin-controlled (not System-Admin-controlled) User
lifecycle, scoped to the calling Admin's own department: authorize a
candidate email, candidate signs up through the *existing* signup
workflow, the Admin approves, then deactivate/reactivate — plus the
project's first authorization **revocation** endpoint. This document does
not cover Letter CRUD, uploads, dashboards, notifications, or System Admin
handover — see §12.

## 1. User lifecycle

```text
ADMIN (own department only)
    ↓
POST /api/v1/users/authorizations   (email — department is always the Admin's own)
    ↓
UserAuthorization(purpose=USER, department_id=<admin's own>, status=ACTIVE)
    ↓
Candidate signs up — POST /api/v1/auth/signup (same endpoint every role uses)
    ↓
User(role=USER, department_id=<from authorization>, status=PENDING_APPROVAL)
    ↓
ADMIN approves — POST /api/v1/users/{user_id}/approve
    ↓
ACTIVE USER
    ↓
(reversible) deactivate ⇄ reactivate
```

Same non-negotiable rule as Admin management (Phase 3B.3): a User account
is **never created with a password by the Admin** — only ever through the
candidate's own signup. There is no second signup endpoint; see §2.

## 2. Why the caller is ADMIN, not SYSTEM_ADMIN — and why that changes everything

Every previous phase's business-resource caller (`Department`,
`Admin`) has been `SYSTEM_ADMIN` — a **global** role with no department of
its own, so `assert_department_access` always short-circuits (`if
user.role == SYSTEM_ADMIN: return`) and none of Phase 3B.1's
department-isolation machinery was ever actually exercised against a real
resource. `app/api/deps.py:require_admin` (strictly `ADMIN`, unlike
`require_admin_or_system_admin`) is used for every route in
`app/api/v1/endpoints/users.py` — a `SYSTEM_ADMIN` caller gets `403` here,
the same as a `USER`, because System Admin has no department to scope
these endpoints to.

This makes Phase 3B.4 the first phase where `app/services/user_service.py`
must genuinely check "does this target belong to *my* department" for
every operation — see §5 for the three different isolation strengths used
and why they differ.

## 3. `UserAuthorizationCreate` has no `department_id` field

Unlike `AdminAuthorizationCreate` (`app/schemas/admin.py`, Phase 3B.3),
where a `SYSTEM_ADMIN` picks a target department by id,
`app/schemas/user.py:UserAuthorizationCreate` has **no `department_id`
field at all** — an Admin does not choose; it is always
`current_user.department_id`, read server-side in
`app/services/user_service.py:authorize_user`:

```python
authorization = self.authorizations.create(
    email=normalized_email,
    department_id=admin.department_id,   # never client-supplied
    authorized_by=admin.id,
    purpose=AuthorizationPurpose.USER,
)
```

A client attempting to send `department_id` (or `role`, `status`,
`authorized_by`) is rejected with `422` — `extra="forbid"`, same pattern
as every request schema in this codebase.

## 4. User authorization — `POST /api/v1/users/authorizations`

ADMIN only. Request: `{"email": "..."}` — nothing else. Validation, in
order:

1. `email` required, normalized (`normalize_email`, shared with every
   other signup-adjacent flow).
2. The calling Admin's own department must be `ACTIVE`
   (`assert_department_access(admin, admin.department_id)` — a
   tautological self-check; see §5) — `403` otherwise.
3. The email must not already belong to an **ACTIVE** User (`409`).
4. The email must not already have an **unresolved** USER-purpose
   authorization (`409`) — same "not expired" definition as
   `docs/architecture/admin-management.md` §8; unchanged reasoning,
   reused as-is via
   `app/repositories/user_authorization_repository.py:find_unresolved`.

The same narrow, accepted edge case from Phase 3B.3 applies in the mirror
direction here: step 3 checks specifically for an ACTIVE **User**, so an
email already belonging to an active **Admin** can still be authorized as
a User candidate — the pre-existing `users.email` uniqueness constraint
rejects the resulting signup with `DuplicateEmailError` → `409` if it's
ever attempted, so no inconsistency results.

## 5. Three isolation strengths (not interchangeable)

`app/services/user_service.py` uses `assert_department_access`
(`app/services/authorization.py`, Phase 3B.1) as a **resource-level**
check — its first real exercise in this codebase, anticipated by that
module's own docstring since Phase 3B.1. Three distinct strengths are used
deliberately:

| Action | Cross-department check | Requires Admin's own dept ACTIVE? |
|---|---|---|
| `list_users`, `get_user`, `list_authorizations` (read) | Yes (scoped query / equality) | **No** |
| `deactivate_user`, `revoke_authorization` (lock-down) | Yes | **No** |
| `authorize_user`, `approve_user`, `reactivate_user` (state-elevating) | Yes | **Yes** |

**Read and lock-down actions never require the Admin's own department to
be `ACTIVE`.** An Admin must always be able to see their team, and must
always be able to shut off access — especially in a department that has
itself just been deactivated. Gating a `deactivate_user` call on
"department currently ACTIVE" would make it impossible to lock accounts
down at exactly the moment you'd most want to; `test_deactivation_allowed_even_with_inactive_admin_department`
(`tests/integration/test_user_management.py`) proves this directly.

**State-elevating actions call `assert_department_access(admin,
admin.department_id)`** — a self-referential check against the caller's
*own* `department_id` — which additionally requires that department to be
`ACTIVE`, mirroring `AdminService.approve_admin`/`reactivate_admin`'s
established precedent of re-validating department health before granting
active access.

**Cross-department target resolution never uses `assert_department_access`
at all** for read/lock-down/approve targets — see §6.

## 6. `get_user` folds "wrong role" and "wrong department" into one 404

```python
def get_user(self, user_id: uuid.UUID, *, admin: User) -> User:
    user = self.users.find_user_by_id(user_id)
    if user is None or user.department_id != admin.department_id:
        raise UserNotFoundError()
    return user
```

A `403` (what calling `assert_department_access` on the *target's*
department would produce) confirms the id belongs to *something*. The
brief requires more than "Admin A cannot act on Department B's Users" — it
requires Admin A to **never learn Department B's User even exists**.
`UserNotFoundError` is raised identically whether `user_id` doesn't exist
at all, belongs to a non-`USER` role, or belongs to a `USER` in a
different department — three failure modes, one response, the same
enumeration-prevention reasoning `AdminNotFoundError` established in Phase
3B.3, extended one further step. `approve_user`/`deactivate_user`/
`reactivate_user` all call `get_user` first, so this protection is
inherited automatically, not re-implemented per endpoint.

`app/repositories/user_repository.py:list_users` takes `department_id` as
a **required** keyword argument (unlike `list_admins`'s optional one) —
an Admin can only ever list one department, so the query is scoped at the
repository call site itself, as defense in depth beneath the service-layer
check.

## 7. Self-protection — structural, not a separate check

Same pattern Phase 3B.3 established for System Admin protection, applied
here for Admin self-protection: **no "is this the caller's own id" check
exists anywhere in this phase's code.**
`app/repositories/user_repository.py:find_user_by_id` filters `role ==
USER`. An Admin's own id is role `ADMIN`, so `get_user` 404s on it by
construction — "an Admin cannot approve/deactivate/reactivate themselves"
holds without a dedicated check, and the same mechanism means a
`SYSTEM_ADMIN` id or another Admin's id passed as `{user_id}` also 404s.
Verified directly: `test_admin_cannot_approve_self`,
`test_admin_cannot_deactivate_self`, `test_admin_cannot_reactivate_self`,
`test_system_admin_cannot_be_targeted_via_users_endpoints`
(`tests/integration/test_user_management.py`).

A `USER`-role caller is excluded even earlier — `require_admin`
(`app/api/deps.py`) rejects them with `403` before any service code runs,
so "can a User approve/deactivate/reactivate themselves" is unreachable by
construction too.

## 8. Approval, deactivation, reactivation

`POST /api/v1/users/{user_id}/approve` — same one-time-event reasoning as
`AdminService.approve_admin` (Phase 3B.3): requires the target `PENDING_
APPROVAL` (`409` otherwise), **not idempotent**.

`POST /api/v1/users/{user_id}/deactivate` / `.../reactivate` — both
**idempotent**, same convention as Department (3B.2) and Admin (3B.3)
activate/deactivate. Deactivation is unconditional (§5). Reactivation
always re-validates the Admin's own department is `ACTIVE`, including in
the already-`ACTIVE` idempotent case — same "ensure ACTIVE, but only when
that's currently valid" reasoning as `AdminService.reactivate_admin`.

## 9. Authorization revocation — `DELETE /api/v1/users/authorizations/{authorization_id}`

**The first revocation endpoint in this project.**
`AuthorizationStatus.REVOKED` has existed on the enum since Phase 2 — this
phase is the first to ever set it. `app/repositories/user_authorization_repository.py:revoke`
does exactly one thing: `authorization.status = AuthorizationStatus.REVOKED`.
The row is never deleted — only its `status` changes, preserving a full
audit trail of who authorized what and what happened to it.

**Creator-scoped, not department-scoped** — deliberately stricter than
`list_authorizations`' department-wide visibility (§10). The brief
requires "only the creating Admin can revoke", so
`app/services/user_service.py:revoke_authorization` checks all four of:
`purpose == USER`, `department_id == admin.department_id`,
`authorized_by == admin.id`, and existence — collapsing all four failure
modes into one `AuthorizationNotFoundError` → `404`, the same
enumeration-prevention reasoning as §6. This means a *different* Admin in
the *same* department who created no authorizations of their own cannot
revoke a colleague's, even though they can see it via `GET
/users/authorizations`. Verified: `test_admin_cannot_revoke_another_admins_authorization`.

**Revocation state transitions:**

| Current status | `DELETE` result |
|---|---|
| `ACTIVE` | → `REVOKED`, `200` |
| `REVOKED` | No-op, stays `REVOKED`, `200` (idempotent — "locked down" is "locked down") |
| `USED` | `409`, `AuthorizationNotRevocableError` — the account it produced already exists; revoking cannot retroactively un-create it |

Revoking an authorization **never touches the `User` row it may have
already produced** — verified directly by
`test_revoking_authorization_does_not_affect_existing_account`, which
signs up against an authorization (flipping it to `USED`), confirms the
`409` on a subsequent revoke attempt, and re-reads the `User` row to prove
its status is untouched.

No department-ACTIVE gate on revocation (§5) — an Admin must be able to
lock down a leaked/mistaken authorization even if their department has
itself been deactivated in the meantime.

## 10. Listing — `GET /api/v1/users`, `GET /api/v1/users/authorizations`

Both ADMIN only, both scoped to the caller's own department, both support
an optional `?status=` filter, both return the thin
`{"items": [...], "total": N}` envelope established in Phase 3B.2/3B.3
(pagination can be added later without a shape change; none is
implemented here).

`GET /api/v1/users/authorizations` is **department-wide, not
creator-scoped** — an Admin sees every USER-purpose authorization issued
in their department, including ones a colleague or predecessor Admin
created, for departmental oversight. This is deliberately *not* the same
scoping as revocation (§9) — visibility and control are different
concerns here, and conflating them would either hide useful oversight
information or let any Admin revoke any colleague's authorization.

## 11. Error behavior

| Situation | Status |
|---|---|
| No/invalid/expired/tampered JWT, or caller's own account not `ACTIVE` | `401` |
| Valid JWT, `ACTIVE`, not `ADMIN` (includes `SYSTEM_ADMIN`) | `403` (generic message, unchanged from Phase 3B.1) |
| Calling Admin's own department is `INACTIVE` (authorize/approve/reactivate only) | `403` (`DepartmentAccessDeniedError`, same generic message — no detail about *why*) |
| `{user_id}` doesn't resolve to a `USER` in the caller's own department (missing, wrong role, or wrong department) | `404`, "User not found." |
| `{authorization_id}` doesn't resolve to a USER-purpose authorization created by the caller in their own department | `404`, "Authorization not found." |
| Email already belongs to an active User, or already has an unresolved USER authorization | `409` |
| Approving a non-`PENDING_APPROVAL` User | `409` |
| Revoking an already-`USED` authorization | `409` |
| Blank/malformed request body, server-controlled field injected (e.g. `department_id`) | `422` |

No PostgreSQL exception, SQL statement, or stack trace is ever exposed —
every failure is caught in `app/services/user_service.py` and translated
into one of the domain exceptions above before it reaches the API layer.

## 12. Explicitly NOT implemented (belongs to later phases)

* **Letter CRUD, document uploads, dashboards, notifications** — untouched,
  per the brief's explicit scope boundary.
* **Frontend User management UI** — none built.
* **System Admin handover** — unrelated to this phase; still deferred.
* **Automatic audit logging** — no automatic audit trail exists yet,
  extending the same list `docs/architecture/admin-management.md` §13
  already scoped, not a second, competing list:
  * `USER_AUTHORIZATION_CREATED`
  * `USER_AUTHORIZATION_REVOKED`
  * `USER_APPROVED`
  * `USER_DEACTIVATED`
  * `USER_REACTIVATED`
* **Email delivery** — an authorized candidate must still be told their
  email is authorized out-of-band; unchanged limitation from Phase 3A.

### Known limitations

* **The equivalent ADMIN-purpose revocation gap from Phase 3B.3 remains
  open** — a System Admin still cannot revoke a still-`ACTIVE`,
  non-expired ADMIN-purpose authorization. Assessed for an actual security
  vulnerability during a Phase 3B.4 hardening pass and found to be a
  capability gap, not an exploitable hole — see §13 for the full
  question-by-question reasoning.
* **The same `categories.name`/`classifications.name` constraint-naming
  issue noted in Phase 3B.2 remains unfixed** — unrelated to this phase's
  changes.

## 13. ADMIN-purpose authorization revocation — security assessment (hardening pass)

This phase (3B.4) added revocation only for USER-purpose authorizations.
A follow-up hardening pass explicitly checked whether the missing
ADMIN-purpose equivalent is an actual vulnerability, rather than assuming
it or silently building it. Findings, by question:

**A. Can an ADMIN-purpose authorization currently be revoked through any
existing endpoint?** No. `app/api/v1/endpoints/admins.py` has no `DELETE`
route at all — grepped and confirmed directly. `DELETE
/api/v1/users/authorizations/{id}` exists, but `revoke_authorization`
(`app/services/user_service.py`) explicitly requires `purpose ==
AuthorizationPurpose.USER` before anything else; an ADMIN-purpose id
passed to it is treated as not found. No code path anywhere can set an
ADMIN-purpose authorization's `status` to `REVOKED`.

**B. Can a departmental Admin revoke an ADMIN-purpose authorization
belonging to another Admin?** No — doubly blocked. `require_admin` lets an
Admin call the revoke endpoint at all, but the `purpose == USER` filter
(A) rejects any ADMIN-purpose id before the creator/department check ever
runs. Even for USER-purpose rows, only the *creating* Admin can revoke
(§9) — a second, independent restriction that would also apply if the
purpose filter didn't exist.

**C. Can a User revoke an ADMIN-purpose authorization?** No —
`require_admin` (`app/api/deps.py`) rejects a `USER`-role caller with
`403` before any service code in `user_service.py` runs at all.

**D. Can a malicious client alter authorization purpose?** No.
`UserAuthorizationCreate` and `AdminAuthorizationCreate` both have no
`purpose` field and both set `extra="forbid"` — a request body containing
`"purpose": "..."` is rejected with `422` before reaching the service
layer. `purpose` is hardcoded server-side in both
`user_service.py:authorize_user` (always `USER`) and
`admin_service.py:authorize_admin` (always `ADMIN`) — never read from
client input anywhere. Verified directly:
`test_client_cannot_inject_purpose_on_user_authorization`
(`tests/integration/test_user_management.py`) and
`test_client_cannot_inject_purpose_on_admin_authorization`
(`tests/integration/test_admin_management.py`).

**E. Can a USER-purpose revocation endpoint accidentally revoke an
ADMIN-purpose authorization?** No — see A. Verified directly (not just
asserted from reading the code):
`test_revoke_endpoint_cannot_touch_admin_purpose_authorization`
(`tests/integration/test_user_management.py`) creates an ADMIN-purpose
authorization owned by the calling Admin in the calling Admin's own
department — the single most favorable case for an accidental match — and
confirms `DELETE /api/v1/users/authorizations/{id}` still returns `404`
and leaves the row's `status` as `ACTIVE`.

**F. Can an ADMIN authorization remain in a dangerous unresolved state
that permits unintended signup?** An ACTIVE ADMIN-purpose authorization
with no `expires_at` (no endpoint in this codebase currently sets one — a
pre-existing characteristic of the whole authorization system, not
specific to ADMIN-purpose or to this phase) does stay consumable
indefinitely if nobody revokes it, since nothing currently can. But
"consumable" only means a candidate can complete *signup* — the resulting
`User` row always starts `PENDING_APPROVAL` (`app/services/auth_service.py:signup`
derives status unconditionally, from nothing client-supplied), and a
`PENDING_APPROVAL` account has no privilege whatsoever: it cannot log in
(`AccountPendingApprovalError` → `403`, checked *after* password
verification but *before* any resource access), so a stray signup grants
no access. The System Admin who could have revoked the authorization
retains full control at the next gate — `approve_admin`
(`app/services/admin_service.py`) is a separate, still-mandatory,
still-SYSTEM_ADMIN-only decision, and `deactivate_admin` can shut down a
PENDING_APPROVAL admin account directly (its role/status filter,
`find_admin_by_id`, doesn't require `ACTIVE`) if a stray signup is ever
noticed. No privilege escalation path exists.

**G. Does the absence of ADMIN-purpose revocation create an actual
security vulnerability?** **No.** Every step in the chain from "authorize"
to "meaningful access" (authorize → candidate signup → `PENDING_APPROVAL`
→ mandatory System-Admin approval → `ACTIVE`) remains fully gated by
`SYSTEM_ADMIN`-only endpoints regardless of whether the authorization step
itself can be undone. The gap is an **operational convenience gap**: a
System Admin who authorizes the wrong email, or changes their mind, must
manage the resulting dormant account after the fact (leave it
un-approved, or deactivate it once signed up) rather than pre-empting it
at the authorization stage. This is the same conclusion Phase 3B.3's own
"Known limitations" reached before revocation existed for either purpose,
and it remains correct now that USER-purpose has an escape hatch and
ADMIN-purpose still doesn't — the two purposes' actual risk profile is
identical because the mitigating control (mandatory approval) applies to
both equally.

**Decision: left unimplemented, as directed.** No code change was made
for this item. If a future phase adds an ADMIN-purpose revoke endpoint,
the repository layer is already purpose-agnostic
(`find_by_id`/`list_by_department`/`revoke` on
`app/repositories/user_authorization_repository.py` all accept any
`AuthorizationPurpose`) — it needs only a new endpoint plus a
creator/department check mirroring §9, not new repository or model code.
