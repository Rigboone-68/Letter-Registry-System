# Admin Management — Phase 3B.3

**Status: complete.** System-Admin-controlled Admin lifecycle: authorize a
candidate email, candidate signs up through the *existing* signup
workflow, System Admin approves, then deactivate/reactivate/department-
transfer. This document does not cover User management/approval (Phase
3B.4) or any later-phase functionality — see §14.

## 1. Admin lifecycle

```text
SYSTEM ADMIN
    ↓
POST /api/v1/admins/authorizations   (email, department_id)
    ↓
UserAuthorization(purpose=ADMIN, status=ACTIVE)
    ↓
Candidate signs up — POST /api/v1/auth/signup (same endpoint as USER signup)
    ↓
User(role=ADMIN, department_id=<from authorization>, status=PENDING_APPROVAL)
    ↓
SYSTEM ADMIN approves — POST /api/v1/admins/{user_id}/approve
    ↓
ACTIVE ADMIN
    ↓
(reversible) deactivate ⇄ reactivate; (reversible) move between departments
```

An Admin account is **never created with a password by the System
Admin** — only ever through the candidate's own signup, exactly like a
regular User (brief §2's core requirement). There is no second
authentication workflow; see §2.

## 2. Why this reuses the existing signup workflow, not a new one

`UserAuthorization` gained one new column, `purpose`
(`AuthorizationPurpose`: `USER` | `ADMIN` — Phase 3B.3), rather than a
parallel `AdminAuthorization` table. Every other column on that table
means exactly the same thing regardless of purpose — department, expiry,
race-safe consumption via `SELECT ... FOR UPDATE` — so duplicating the
whole table would only have duplicated that machinery for no benefit. See
`app/models/user_authorization.py`'s docstring for the full reasoning.

`AuthService.signup` (`app/services/auth_service.py`, unchanged endpoint:
`POST /api/v1/auth/signup`) now derives the created `User`'s `role` from
**whichever authorization it finds**: `purpose == ADMIN` → `role=ADMIN`,
anything else → `role=USER`. This is the *only* signup path for both —
there is no `/admins/signup` or equivalent. Concretely:

```python
authorization = self.authorizations.find_and_lock_active(normalized_email)
...
role = UserRole.ADMIN if authorization.purpose == AuthorizationPurpose.ADMIN else UserRole.USER
```

**A USER-purpose authorization can never produce an ADMIN, and an
ADMIN-purpose authorization can never produce a USER** — not because of a
separate check, but because role is read from exactly this one field and
nothing else. `tests/integration/test_admin_management.py::test_user_authorization_cannot_create_admin`
and `::test_admin_authorization_cannot_create_user` prove both directions
against a real signup request.

`find_and_lock_active` (the race-safe consumption query, unchanged from
Phase 3A except for this note) deliberately does **not** filter by
`purpose` in its `WHERE` clause — it can't: at signup time the system
doesn't yet know whether the caller is a USER or ADMIN candidate, which is
exactly what the found row's own `purpose` tells it. The existing "oldest
active authorization wins" tie-break (Phase 3A) is unchanged and now
applies across purposes too — there is no basis for treating ADMIN
authorizations as higher-priority than USER ones.

## 3. Admin authorization — `POST /api/v1/admins/authorizations`

SYSTEM_ADMIN only. Request: `{"email": "...", "department_id": "..."}` —
nothing else. `role`, `status`, authorization `status`, `created_at`,
`used_at`, and `authorized_by` all have **no field** on
`AdminAuthorizationCreate` (`app/schemas/admin.py`) — not merely ignored
if sent; the schema additionally sets `extra="forbid"`, so any attempt to
inject one of them is rejected outright with `422`. `authorized_by` is
always the calling SYSTEM_ADMIN's own id, taken from `current_user`
server-side.

Validation, in order:

1. `email` required, normalized (same `normalize_email` used everywhere
   else in this codebase).
2. Destination department must exist (`404` otherwise).
3. Destination department must be `ACTIVE` (`409` otherwise).
4. The email must not already belong to an **ACTIVE** Admin (`409`).
5. The email must not already have an **unresolved** ADMIN-purpose
   authorization (`409`) — see §8 for exactly what "unresolved" means and
   why.

### A narrow, accepted edge case

Step 4 checks specifically for an *ACTIVE Admin*, not "any active
account" — an email belonging to an ACTIVE **User** can still be
authorized as an Admin candidate. If that candidate then attempts signup,
the pre-existing `users.email` global uniqueness constraint (Phase 2)
rejects it with the same `DuplicateEmailError` → `409` any duplicate
signup already gets — so no security hole results, only a
System-Admin-facing authorization that can never be consumed. Not fixed
with extra validation here, since the brief's own wording ("must not
already belong to an active Admin") is this narrow, and the existing
safety net already prevents any real inconsistency.

## 4. Admin signup

Goes through `POST /api/v1/auth/signup`, completely unmodified from Phase
3A except for the role-derivation change in §2. `role` and `department_id`
have no field on `SignupRequest` at all (Phase 3A) — a client attempting
to inject either is rejected with `422` before ever reaching the service
layer, exactly as already true for USER signups.

## 5. Admin approval — `POST /api/v1/admins/{user_id}/approve`

SYSTEM_ADMIN only. Requires, in order:

1. `user_id` resolves to a `User` with role `ADMIN` (`404` otherwise —
   see §11 for why this is the same response whether the id doesn't exist
   at all or belongs to a non-Admin).
2. That Admin's status is `PENDING_APPROVAL` (`409` otherwise).
3. That Admin's department is `ACTIVE` (`409` otherwise).

Then: status → `ACTIVE`. **Not idempotent** — unlike Department
activate/deactivate (Phase 3B.2) or this phase's own Admin deactivate/
reactivate (§6), approving an already-`ACTIVE` (or `DEACTIVATED`) Admin is
rejected, not silently accepted. Approval is a one-time event tied to a
specific decision ("I am approving this candidate now"), not a status
toggle a caller might reasonably re-issue.

## 6. Deactivation / reactivation

`POST /api/v1/admins/{user_id}/deactivate` and `.../reactivate` — SYSTEM_
ADMIN only, both **idempotent** (consistent with Department activate/
deactivate, Phase 3B.2): deactivating an already-`DEACTIVATED` Admin, or
reactivating an already-`ACTIVE` one, returns `200` with current state
rather than erroring.

Deactivation is unconditional — always allowed, regardless of the Admin's
department status. It changes only this one `User` row's `status`; no
letter, audit-log entry, or any other row is touched, deleted, or
reassigned.

**Reactivation additionally requires the Admin's department to be
`ACTIVE`** (brief §10's preferred behavior), checked on *every* call —
including the already-`ACTIVE` idempotent case, not skipped just because
no status change is actually needed. Why the idempotent case still
re-validates: an Admin can end up `ACTIVE` while their department is
`INACTIVE` (Phase 3B.2 deactivation never touches `User` rows — see that
phase's docs), and this endpoint's contract is "ensure `ACTIVE`, but only
when that's currently a valid state to be in", not merely "ensure
`ACTIVE`". Department-scoped authorization
(`assert_department_access`, Phase 3B.1/3B.2) would block that Admin's
department-scoped actions either way, but this endpoint doesn't pretend
the account is in a fully safe state when it verifiably isn't.

## 7. Multiple Admins per department

**Deliberately unbounded** — a department may have 0, 1, or many Admins.
No unique constraint exists (or was added) on `users.department_id`; the
relationship is a plain one-to-many (`Department 1 → N Admins`), matching
Phase 2's original schema design and the brief's explicit instruction not
to add a `department_id UNIQUE` constraint. Deactivating one Admin has no
effect on any other Admin in the same department —
`tests/integration/test_admin_management.py::test_deactivating_one_admin_does_not_affect_another`
proves this directly, not just by absence of a shared-state bug.

## 8. Admin authorization repository details

`app/repositories/user_authorization_repository.py:find_unresolved(email, purpose)`
— used only when *creating* a new authorization (§3, step 5), never at
signup — checks for an authorization matching this email **and purpose**
whose `status` is `ACTIVE` **and** whose `expires_at` (if set) hasn't
passed. Deliberately the same "not expired" condition as
`find_and_lock_active`'s: nothing in this schema ever flips an
authorization's `status` away from `ACTIVE` when it expires (expiry is
checked only at consumption time), so treating an expired-but-still-
`ACTIVE`-status row as "unresolved" would block re-authorizing that email
**forever**, with no way to clear it — there is no revoke endpoint in this
phase. Excluding expired rows from the "unresolved" check avoids that
dead end. See §14, "Known limitations" for the resulting gap this
leaves (no way to explicitly revoke a still-`ACTIVE`, non-expired
authorization either).

No row-locking on this check (unlike `find_and_lock_active`): the race it
would guard against — two System Admins simultaneously authorizing the
same email — is far lower-stakes than signup consumption. Worst case, two
`ACTIVE` authorization rows exist for one email/purpose momentarily;
`find_and_lock_active` already resolves that safely at signup time (picks
one, locks it; the other simply goes unused).

## 9. Historical data preservation (brief §24 — critical)

**Moving an Admin between departments cannot retroactively change any
historical record's department, and this required no special handling to
guarantee** — the Phase 2 schema already makes it structurally impossible
to violate:

* `Letter.department_id` is its own, independently-stored column (see
  `app/models/letter.py`) — set once, at recording time, from the
  recording user's department at that moment. It is **never re-derived**
  from `letters.recorded_by`'s *current* department at query time; there
  is no live join or computed value involved.
* `app/services/admin_service.py:change_admin_department` touches exactly
  one column on exactly one row: the target `User`'s own `department_id`.
  It has no code path that reads or writes anything on `Letter`,
  `LetterDocument`, `Notification`, or `AuditLog`.

So when an Admin who recorded letters in Department A is later moved to
Department B, every letter they already recorded keeps
`department_id = Department A`'s id, exactly as it was the moment it was
recorded — confirmed directly, not just asserted, in
`tests/integration/test_admin_management.py::test_transfer_does_not_rewrite_historical_records`
(loads the letter after the transfer and asserts its `department_id` is
unchanged) and `::test_historical_records_remain_intact_after_deactivation`
(same idea for deactivation).

`UserAuthorization.authorized_by` and `LetterDocument.uploaded_by` are
plain foreign keys to `users.id` — unaffected by any later change to that
user's `department_id` for the same reason (an FK by id doesn't care what
else changes on the referenced row).

**No migration, snapshot column, or special-case code was needed for
this** — it is a direct, load-bearing consequence of a Phase 2 design
decision (letters store their own department, not a derived one), and
this phase's own docs record why that decision matters here, specifically
because the brief asked to "STOP and document the issue" if the schema
made this impossible — the opposite turned out to be true.

## 10. Admin list / detail

`GET /api/v1/admins` (optional `?department_id=`, `?status=` filters) and
`GET /api/v1/admins/{user_id}` — SYSTEM_ADMIN only. Return `id`,
`full_name`, `email`, `role`, `department_id`, `status`, `created_at`,
`updated_at`. Never `password_hash` — `AdminResponse`
(`app/schemas/admin.py`) has no such field, the same structural guarantee
`UserPublic` (Phase 3A) and `DepartmentResponse` (Phase 3B.2) already
rely on. List responses use the same thin envelope
(`{"items": [...], "total": N}`) Phase 3B.2 established for exactly the
same reason — pagination can be added later without a shape change; none
is implemented in this phase.

## 11. Self-protection and System Admin protection (brief §14, §15)

**No special "is this the caller's own id" check exists anywhere in this
phase's code** — and that's deliberate, not an oversight. Every
Admin-management endpoint requires `require_system_admin`
(`app/api/deps.py`, reused unchanged from Phase 3B.1 — no new
`require_admin_manager()` dependency was created, since System Admin is
the only authority for Admin management and a second dependency would
decide nothing a plain role check doesn't already decide). Since an
`ADMIN`-role caller can never satisfy `require_system_admin`, every
scenario the brief lists under "Admin self-protection" — approve self,
deactivate self, reactivate self, change own department, change own role,
authorize another Admin, create another Admin — is already unreachable
for an Admin caller *before* the target id is ever inspected. This is
tested directly (`test_admin_cannot_approve_self` and siblings,
`tests/integration/test_admin_management.py`), not just implied by the
absence of a bug report.

**A `SYSTEM_ADMIN` id passed as `{user_id}` is never a valid target**,
protecting System Admin accounts from being acted on through this API
even by another System Admin. This is enforced by
`app/repositories/user_repository.py:find_admin_by_id`, which returns
`None` — indistinguishable from "no such user exists at all" — for any id
that resolves to a role other than `ADMIN`. Every endpoint in
`app/api/v1/endpoints/admins.py` maps that `None` (via
`AdminNotFoundError`) to a plain `404`, never a `403` and never a
distinguishable error: a caller learns only "no Admin with this id", the
same response for a genuinely nonexistent id, a `USER`-role id, or a
`SYSTEM_ADMIN`-role id. System Admin handover remains explicitly out of
scope for this phase (unchanged from `docs/architecture/authentication.md`
§9) — there is no code path here that could be mistaken for it.

## 12. Error behavior

| Situation | Status |
|---|---|
| No/invalid/expired/tampered JWT, or caller's own account not `ACTIVE` | `401` |
| Valid JWT, `ACTIVE`, not `SYSTEM_ADMIN` | `403` (generic message, unchanged from Phase 3B.1) |
| `{user_id}` doesn't resolve to an `ADMIN`-role user (missing, wrong role, or `SYSTEM_ADMIN`) | `404`, "Admin not found." |
| Destination/target department doesn't exist | `404`, "Department not found." |
| Destination/target department exists but is `INACTIVE` | `409` |
| Email already belongs to an active Admin, or already has an unresolved ADMIN authorization | `409` |
| Approving a non-`PENDING_APPROVAL` Admin | `409` |
| Blank/malformed request body, server-controlled field injected | `422` |

No PostgreSQL exception, SQL statement, or stack trace is ever exposed —
every failure is caught in `app/services/admin_service.py` and translated
into one of the domain exceptions above before it reaches the API layer.

## 13. Audit events — planned, not implemented (brief §25)

No automatic audit logging exists in this phase, matching the brief's
explicit instruction — same as Phase 3B.1/3B.2. Extends the list already
scoped in `docs/architecture/authorization.md` §12 and
`docs/architecture/department-management.md` §10, not a second, competing
list:

* `ADMIN_AUTHORIZATION_CREATED`
* `ADMIN_APPROVED`
* `ADMIN_DEACTIVATED`
* `ADMIN_REACTIVATED`
* `ADMIN_DEPARTMENT_CHANGED`

## 14. Explicitly NOT implemented (belongs to later phases)

* **User management / approval (Phase 3B.4)** — no endpoint here approves
  a regular `USER`, deactivates/reactivates one, or issues a
  `USER`-purpose `UserAuthorization` via API (that still requires direct
  database access, unchanged from Phase 3A/3B.1/3B.2).
* **Letter CRUD, uploads, dashboards, notifications** — untouched, per the
  brief's explicit scope boundary.
* **Frontend Admin management UI** — none built.
* **System Admin handover** — unrelated to this phase; still deferred.
* **Automatic audit logging** — see §13.
* **Revoking a `UserAuthorization`** — no endpoint exists to explicitly
  set one to `REVOKED`; see "Known limitations" below.

### Known limitations

* **No way to revoke a still-`ACTIVE`, non-expired Admin authorization.**
  If a System Admin authorizes the wrong email, or changes their mind,
  there is no endpoint to revoke it — the candidate could still sign up
  against it. Mitigated only by the fact that approval is a separate,
  required step the System Admin still controls (a wrongly-signed-up
  candidate stays `PENDING_APPROVAL` forever unless explicitly approved).
  A revoke endpoint is natural Phase 3B.4-adjacent work, not added here to
  stay within this phase's scope.
* **An email can be authorized as an Admin candidate while it already
  belongs to an active `USER`.** See §3, "A narrow, accepted edge case" —
  not a security issue (the subsequent duplicate-email check at signup
  prevents any actual inconsistency), just an authorization that can never
  be consumed if this happens.
* **The same `categories.name`/`classifications.name` constraint-naming
  issue noted in Phase 3B.2 remains unfixed** — unrelated to this phase's
  changes, still not depended on by anything built so far.
