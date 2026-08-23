# Administration & Account Management UI — Architecture Review & Implementation (Phase 5D)

**Status: IMPLEMENTED.** §1-25 below are the original architecture/
requirements review (review only, no code) — kept unchanged as the
design rationale. **See §26, "Implementation record"** for what was
actually built on top of it. Builds on Phase 5A (foundation), Phase 5B
(authentication/account UX), and Phase 5C (core Letter registry UI) —
all implemented and unchanged by this phase.

## 0. How to read this document

Same taxonomy this project has used since Phase 4A/Phase 5:

* **CONFIRMED** — verified directly against current backend source code
  this session (endpoints, schemas, services, repositories, models — all
  re-read fresh, not recalled from an earlier phase's report).
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts and the frontend conventions Phase 5A-5C already established.
  Not implemented.
* **PROVISIONAL** — an explicit judgment call this document had to make
  one way or another, flagged so it is revisited deliberately, not
  mistaken for a backend-confirmed fact.
* **PENDING BUSINESS CLARIFICATION** — genuinely open, not guessed.
* **PENDING BACKEND API** — the frontend capability described would
  require a backend endpoint/field that does not currently exist. Never
  worked around; always named explicitly.

## 0.1 A correction to this phase's own brief

The brief's §1 states the frontend currently has "Document UI,
Notification UI." **This is not accurate, verified directly against the
repository this session** — `frontend/src/routes/index.jsx` still
mounts `PlaceholderPage` at `/app/documents` and `/app/notifications`;
no `documentService.js`/`notificationService.js` exists anywhere under
`frontend/src/services/`. Both remain exactly what Phase 5A/5C's own
scope explicitly deferred (Document UI to Phase 5D-and-later per
`docs/PROJECT_STATUS.md`'s own "Pending" list; Notifications UI
likewise). This review does not rely on that framing and instead
reports what a fresh `git`/glob/read of the repository actually shows —
consistent with this project's standing rule to inspect the current
state rather than trust a prior summary.

---

## 1. Files inspected (this session, fresh)

Backend: `app/api/v1/endpoints/{departments,admins,users,auth}.py`,
`app/api/v1/router.py`, `app/api/deps.py`,
`app/schemas/{department,admin,user,auth}.py`,
`app/services/{department_service,admin_service,user_service,
auth_service,authorization}.py`, `app/services/exceptions.py`,
`app/repositories/{department_repository,user_repository,
user_authorization_repository}.py`, `app/models/{department,user,
user_authorization,enums}.py`, `app/main.py`. Frontend: a full glob of
every `frontend/src/**/*.{jsx,js}` file (confirms the exact current
inventory — see §0.1), `frontend/src/routes/index.jsx`,
`frontend/src/navigation/navigationConfig.js`, plus the already-built
Phase 5A-5C primitives (`LoadingState`, `ErrorState`, `EmptyState`,
`StatusBadge`, `Pagination`, `ArchiveConfirmDialog`, `RoleGuard`,
`ProtectedRoute`, `AuthContext`, `letterService.js`/
`categoryService.js`/`classificationService.js`/`departmentService.js`,
`utils/formValidation.js`) re-examined for reuse fit, not re-designed
from scratch.

## 2. Current backend capabilities (CONFIRMED, re-verified fresh)

### 2.1 Departments — `app/api/v1/endpoints/departments.py`, all `require_system_admin`

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `POST /departments` | `DepartmentCreate {name, code?}` — `extra="forbid"`, no `id`/`status`/timestamps field | `DepartmentResponse` | `201`; `409` (`"A department with this name already exists."` / `"...code already exists."`) |
| `GET /departments` | Query `status` (`ActiveStatus`, optional) | `DepartmentListResponse {items, total}` | `200` — **no pagination, no search, no sort** |
| `GET /departments/{department_id}` | — | `DepartmentResponse` | `200`; `404` `"Department not found."` |
| `PATCH /departments/{department_id}` | `DepartmentUpdate {name?, code?}` — at least one required, `extra="forbid"` | `DepartmentResponse` | `200`; `404`; `409` (same two duplicate messages) |
| `POST /departments/{department_id}/activate` | — | `DepartmentResponse` | `200`, **idempotent** (already-ACTIVE just returns current state, no audit row on a no-op) |
| `POST /departments/{department_id}/deactivate` | — | `DepartmentResponse` | `200`, **idempotent**, same no-op behavior |

`DepartmentResponse`: `id, name, code (nullable), status (ActiveStatus),
created_at, updated_at`. **No admin/user count field of any kind.**
Deactivation never touches `users`/`letters`/any other row — confirmed
directly in `department_service.py`'s own docstring and code: only this
row's own `status` changes.

### 2.2 Admins — `app/api/v1/endpoints/admins.py`, all `require_system_admin`

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `POST /admins/authorizations` | `AdminAuthorizationCreate {email, department_id}` — `extra="forbid"` | `AdminAuthorizationResponse` | `201`; `404` (`"Department not found."`); `409` (`"The destination department is not ACTIVE."`... actually this specific message is only from the *409-not-active* helper, reused for authorize/approve/reactivate/transfer — see below); `409` (`"...already belongs to an active Admin."`); `409` (`"...already has an unresolved Admin authorization."`) |
| `GET /admins` | Query `department_id?`, `status?` (`UserStatus`) | `AdminListResponse {items, total}` | `200` — **no pagination, no search, no sort; `department_id` filter IS supported here** |
| `GET /admins/{user_id}` | — | `AdminResponse` | `200`; `404` `"Admin not found."` (**identical** whether the id doesn't exist, or exists but isn't role ADMIN — including a SYSTEM_ADMIN's own id; see §2.5) |
| `POST /admins/{user_id}/approve` | — | `AdminResponse` | `200`; `404`; `409` `"This Admin is not awaiting approval."` (**not idempotent** — a one-time transition); `409` `"The destination department is not ACTIVE."` (re-validated even on approve) |
| `POST /admins/{user_id}/deactivate` | — | `AdminResponse` | `200`, **idempotent**, always allowed regardless of department status |
| `POST /admins/{user_id}/reactivate` | — | `AdminResponse` | `200`, **idempotent** if already ACTIVE, but **always** re-validates the Admin's department is ACTIVE first (even in the no-op case) — `409` if not |
| `PATCH /admins/{user_id}/department` | `AdminDepartmentUpdate {department_id}` — `extra="forbid"` | `AdminResponse` | `200`; `404` (Admin); `404` (destination Department); `409` (destination not ACTIVE) |

`AdminResponse`: `id, full_name, email, role, department_id (nullable),
status, created_at, updated_at`. No `password_hash`. `authorized_by` is
always the calling SYSTEM_ADMIN's own id (server-derived) — no field
for a client to supply it.

### 2.3 Users — `app/api/v1/endpoints/users.py`, all `require_admin` (strictly ADMIN — not SYSTEM_ADMIN; SYSTEM_ADMIN has no department)

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `POST /users/authorizations` | `UserAuthorizationCreate {email}` — **no `department_id` field at all**; always derived from the calling Admin's own `department_id` | `UserAuthorizationResponse` | `201`; `403` (Admin's own department is not ACTIVE — see §2.6); `409` (`"...already belongs to an active User."`); `409` (`"...already has an unresolved User authorization."`) |
| `GET /users/authorizations` | Query `status?` (`AuthorizationStatus`) | `UserAuthorizationListResponse {items, total}` | `200` — scoped to the Admin's own department, **department-wide** (every authorization created by any Admin in that department, not creator-scoped) — **no pagination, no search, no sort** |
| `DELETE /users/authorizations/{authorization_id}` | — | `UserAuthorizationResponse` | `200`, **idempotent for already-REVOKED**; `404` (not found, wrong department, **or created by a different Admin** — revocation is creator-scoped, stricter than the list's department-wide visibility); `409` `"...already been used and cannot be revoked."` |
| `GET /users` | Query `status?` | `UserListResponse {items, total}` | `200`, scoped to the Admin's own department — **no pagination, no search, no sort, no `department_id` param at all** (there is nothing to filter by; an Admin only ever sees their own department) |
| `GET /users/{user_id}` | — | `UserResponse` | `200`; `404` `"User not found."` (**identical** for nonexistent, wrong-role, *and cross-department* — an Admin cannot learn that an id belongs to any account in another department, not just be blocked from acting on it) |
| `POST /users/{user_id}/approve` | — | `UserResponse` | `200`; `404`; `409` `"This User is not awaiting approval."` (**not idempotent**); `403` (Admin's own department not ACTIVE) |
| `POST /users/{user_id}/deactivate` | — | `UserResponse` | `200`, **idempotent**, always allowed regardless of the Admin's own department status |
| `POST /users/{user_id}/reactivate` | — | `UserResponse` | `200`, **idempotent** if already ACTIVE; `403` if the Admin's own department is not ACTIVE (re-validated even in the no-op case) |

`UserResponse`: identical shape to `AdminResponse` (`id, full_name,
email, role, department_id, status, created_at, updated_at`).

### 2.4 Route-ordering note (CONFIRMED, worth restating for the frontend)

`/users/authorizations*` is declared before `/users/{user_id}` in the
backend router specifically so `GET /users/authorizations` is never
mis-matched as `GET /users/{user_id}` with a literal id of
`"authorizations"`. This has no frontend implication beyond: **the
frontend must call the two endpoints with their exact paths** — there
is no risk of accidental collision from the client side, but a
hand-rolled URL template that inserted a raw string where
`{authorization_id}`/`{user_id}` belongs could still hit the wrong
route; the service layer (§15) removes this risk structurally by never
building URLs from anything but a real id.

### 2.5 System Admin protection (CONFIRMED — structural, not a special-cased check)

There is **no endpoint anywhere that can target a SYSTEM_ADMIN**.
`UserRepository.find_admin_by_id` returns `None` (→ `AdminNotFoundError`
→ `404`) for any id that isn't role `ADMIN` — including a SYSTEM_ADMIN's
own id, or another SYSTEM_ADMIN's id if one existed. This is not a
"you can't act on yourself" rule; it's "this endpoint set cannot resolve
a SYSTEM_ADMIN row at all, regardless of whose id it is." The same
structural pattern protects Admins from targeting themselves or another
Admin via the Users endpoints: `UserRepository.find_user_by_id` returns
`None` unless `role == USER`, so an Admin's own id (role `ADMIN`) 404s
on every User lifecycle endpoint — confirmed directly in
`user_service.py`'s own docstring: **"Self-protection... is not a
separate check anywhere in this file — it holds by construction."**
There is no dedicated backend "self-targeting" error message distinct
from the generic 404 — the frontend must not invent one (§6.4/§16).

### 2.6 The read/lock-down vs. state-elevating distinction (CONFIRMED — must not be flattened)

Re-verified directly in `user_service.py`'s own module docstring, and it
governs which HTTP status a frontend screen must be ready to receive for
each action:

* **Read** (`get_user`, `list_users`, `list_authorizations`) and
  **lock-down** (`deactivate_user`, `revoke_authorization`) only require
  the target to belong to the Admin's own department — **not** that the
  department currently be `ACTIVE`. An Admin whose own department has
  gone `INACTIVE` can still see their team and still deactivate/revoke.
* **State-elevating** actions (`authorize_user`, `approve_user`,
  `reactivate_user`) call `assert_department_access(admin,
  admin.department_id)` — a tautological self-check that additionally
  requires the Admin's **own** department to be `ACTIVE`. These three
  can return `403` for a reason that has nothing to do with the target
  row: the calling Admin's own department went inactive.
* The exact same asymmetry exists on the Admin side, one level up:
  `approve_admin`/`reactivate_admin` re-validate the target Admin's own
  department is `ACTIVE` (`409`, not `403` — see §16), while
  `deactivate_admin` is unconditional.

A frontend that renders one generic "Admin can manage users" screen with
one generic error state would misrepresent this — see §5, §16.

### 2.7 Enums — exact values (CONFIRMED, `app/models/enums.py`)

* `UserStatus`: `PENDING_APPROVAL`, `ACTIVE`, `DEACTIVATED`. No other
  value exists.
* `AuthorizationStatus`: `ACTIVE`, `USED`, `REVOKED`. **There is no
  `PENDING` value and no `EXPIRED` value** — the brief's §19 assumption
  of a `PENDING`/`EXPIRED` pair does not match the actual enum; an
  authorization is `ACTIVE` from the moment it's created until it's
  consumed or revoked. See §2.8 for why "expired" still matters despite
  not being a status value.
* `ActiveStatus` (Department, Category, Classification): `ACTIVE`,
  `INACTIVE`.
* `UserRole`: `SYSTEM_ADMIN`, `ADMIN`, `USER`.
* `AuthorizationPurpose`: `USER`, `ADMIN` — says what role a signup
  against this authorization will produce; **not** a UI-facing status,
  never rendered as one.

### 2.8 `expires_at` exists but is never set (CONFIRMED — a real, worth-flagging nuance)

`UserAuthorization.expires_at` is `Optional[datetime]`, exposed on both
`AdminAuthorizationResponse`/`UserAuthorizationResponse`. Both
`AdminService.authorize_admin` and `UserService.authorize_user` call
`UserAuthorizationRepository.create(...)`, whose signature takes no
`expires_at` argument at all — the column is left at its schema default,
which is `None`. **No code path in this backend ever sets an
expiration.** The repository's own `find_and_lock_active`/
`find_unresolved` queries do check `expires_at > now()` (so the
*mechanism* for expiry exists and would work the instant something
started setting the column), but in the system as it exists today, this
condition is always vacuously true. **Frontend implication**: there is
currently nothing for a Phase 5D screen to expire-badge or countdown —
`expires_at` should be rendered if present (defensively, for forward
compatibility) but never assumed to ever actually be non-null in this
phase. Not `PENDING BACKEND API` (the field and mechanism already
exist) — flagged as `PENDING BUSINESS CLARIFICATION`: whether
authorization expiration is ever going to be a real V1 requirement,
since nothing currently sets it.

### 2.9 No pagination/search/sort on Department, Admin, User, or Authorization lists (CONFIRMED)

Unlike `GET /api/v1/letters` (Phase 4C: `page`/`page_size`/`sort_by`/
`sort_order` + seven text filters), **none** of `GET /departments`,
`GET /admins`, `GET /users`, `GET /users/authorizations` accept any of
those parameters. Each returns its *complete* matching result set in
one response, filtered only by the one or two exact filters each
supports (`status` on all four; `department_id` additionally on
`GET /admins` only). See §11 for the full support matrix and §22 for
whether this is acceptable for V1.

---

## 3. Current frontend capabilities (CONFIRMED, glob + read this session)

Exactly Phase 5A + 5B + 5C, nothing more:

* Auth foundation: `AuthContext`, `apiClient`, `authService`,
  `tokenStorage`, `errorNormalization`, `ProtectedRoute`, `RoleGuard`,
  `LoginPage`, `SignupPage`, `PendingApprovalNotice`,
  `DeactivatedAccountNotice`.
* Chrome: `AppShell`/`Sidebar`/`Topbar`, `navigationConfig.js`.
* Reusable primitives: `LoadingState`, `ErrorState`, `EmptyState`,
  `StatusBadge` (currently a two-tone — `positive`/`neutral` — badge
  keyed by raw value string: `ACTIVE→positive`,
  `ARCHIVED|INACTIVE→neutral`), `Pagination` (built for Letters' real
  backend pagination — **does not apply as-is** to any Phase 5D list;
  see §14.3), `ArchiveConfirmDialog` (Letter-specific wording and a
  single confirm action — a template to generalize from, not to reuse
  directly; see §14.2).
* Core Letter registry: `LetterListPage`/`LetterFormPage`/
  `LetterDetailPage`, `LetterTable`/`LetterFilters`,
  `letterService.js`, plus `categoryService.js`/
  `classificationService.js`/`departmentService.js` — **already
  SYSTEM_ADMIN-only reference-data wrappers around exactly the
  `GET /departments`/`GET /categories`/`GET /classifications` endpoints
  this phase also needs**; `departmentService.js` in particular can be
  reused as-is for the Department list screen's data source (see §15).
* `utils/formValidation.js` — `validateLoginForm`, `validateSignupForm`,
  `validateLetterForm`; no admin/user/department validators exist yet.
* Routes already slotted, still `PlaceholderPage` (`routes/index.jsx`,
  confirmed unchanged): `/app/admin/users` (`RoleGuard: ['ADMIN']`),
  `/app/system/departments`, `/app/system/admins`,
  `/app/system/categories`, `/app/system/classifications` (all
  `RoleGuard: ['SYSTEM_ADMIN']`), plus `/app/documents`,
  `/app/notifications` (no `RoleGuard` — every role sees them).
* `navigationConfig.js` already lists "Departments"/"Administrators"
  (SYSTEM_ADMIN) and "Users" (ADMIN) pointing at those exact paths —
  Phase 5D's navigation work is *filling in* already-designed slots, not
  inventing new ones (see §12).

**No** admin/user/department/authorization service module, page,
component, or test exists yet. **No** Category/Classification
management UI exists yet either (still `PlaceholderPage`) — out of this
phase's own objective list (§2 A-I does not mention Category/
Classification management), so it is **not** designed here; noted as a
remaining gap for a later phase in §22.

---

## 4. System Admin UX architecture

### 4.1 Departments screens

* **List** (`/app/system/departments`, already slotted) — a table:
  Name, Code (or an explicit "—" when null, never blank), Status
  (`StatusBadge`), an implicit "row count" heading (`{total} departments`,
  from the response's own `total`, never a client `.length` recount once
  filters exist). A `status` filter (`ActiveStatus` — matches the one
  real backend filter). **No search box** — the backend has no text
  filter on department name/code; a client-side substring filter over
  the already-fully-fetched list is a legitimate V1 convenience (§14.3)
  but must never be presented as if it were a server-side search.
* **Create** (`/app/system/departments/new`, new route) — `name`
  (required), `code` (optional). New departments are always created
  `ACTIVE` server-side (`DepartmentService.create_department`'s own
  docstring) — **no status field on the form**, nothing for one to bind
  to. On success, navigate to the new department's detail page (mirrors
  `LetterFormPage`'s own create-then-navigate pattern, Phase 5C).
* **Detail / Edit** (`/app/system/departments/:id`, new route) — one
  page, `LetterDetailPage`-style: read view plus an inline or
  route-toggled edit mode for `name`/`code` (`DepartmentUpdate` requires
  at least one of the two — the form must not allow submitting neither).
  Status is **not** edited here — it has its own dedicated
  activate/deactivate actions (§4.1's next bullet), matching the
  backend's own separation (a `PATCH` never touches `status`; only the
  two dedicated endpoints do).
* **Activate / Deactivate** — two buttons on the detail page, each
  calling its own dedicated endpoint. Both are **backend-idempotent**
  (§2.1) — clicking "Deactivate" on an already-`INACTIVE` department is
  a safe no-op server-side. **RECOMMENDED**: still confirm deactivation
  (see §17) because of its *downstream* consequence (every ADMIN/USER in
  that department loses state-elevating and, per §2.6, potentially even
  some read/lock-down capability the instant it takes effect) — the
  idempotency of the status write itself doesn't make the *operational
  impact* of deactivating a department idempotent or low-stakes.
  Activation, by contrast, only ever *restores* capability — **RECOMMENDED
  no confirmation** for activate, matching this project's existing
  "don't confirm a safe, restorative, idempotent action" convention
  (Phase 5C never confirms un-archiving because no un-archive action
  exists at all; Department activation is the closest real analogue and
  the same reasoning applies: nothing is lost by activating).
* **Never**: a delete/remove action of any kind. `Department` has no
  physical-deletion path anywhere in this backend.

### 4.2 Administrators screens

* **List** (`/app/system/admins`, already slotted) — table: Name,
  Email, Department (resolved via the same `departmentService.js`
  lookup map pattern `LetterListPage` already uses for SYSTEM_ADMIN,
  Phase 5C — no new resolution mechanism needed), Status
  (`UserStatus` — a **different** badge domain from Department's
  `ActiveStatus`; see §19), an "Authorize new Admin" action. Filters:
  `status` and `department_id` (**both** real backend filters here,
  unlike the Users list — §2.9) — `department_id` as a `<select>`
  populated from the same department list already loaded for name
  resolution, not a second fetch.
* **Detail** (`/app/system/admins/:id`, new route) — full
  `AdminResponse` fields, current Status, current Department (name
  resolved). Actions present depend on current status:
  - `PENDING_APPROVAL` → **Approve** only (not idempotent — see §17 on
    why this one *does* warrant confirmation despite this project's
    general "don't over-confirm idempotent actions" stance: a rejected
    double-click here doesn't silently no-op, it 409s, which is a worse
    UX than a light confirmation would have been).
  - `ACTIVE` → **Deactivate**, **Transfer to another department**
    (§9).
  - `DEACTIVATED` → **Reactivate**.
  - A `404` reaching this page at all (stale link, or the target
    somehow resolved to a non-Admin id — structurally shouldn't happen
    via this UI's own links, but a manually-typed URL could) renders
    the identical generic "not found" `ErrorState` this project already
    uses for Letters (§7 of the brief; §6.4 below) — never a distinct
    "this account cannot be managed here" message that would leak *why*.
* **Authorize** (`/app/system/admins/authorize`, new route) — `email`
  (required, `EmailStr`), `department_id` (required — **a real
  `<select>`, unlike User authorization, which has none at all**; see
  §10). On success, **RECOMMENDED**: land on the Administrators list
  (not a detail page — the authorization just created is not itself an
  Admin account yet; there is no "Admin" row to view, only a pending
  `UserAuthorization` the candidate hasn't signed up against). Do not
  auto-navigate to a nonexistent Admin detail page.
* **Never**: a "Reject"/"Deny" action for a pending Admin. No such
  endpoint exists — the only ways a `PENDING_APPROVAL` Admin resolves
  are Approve (→ `ACTIVE`) or Deactivate (→ `DEACTIVATED`, which the
  endpoint list confirms is unconditionally callable regardless of
  current status, so it doubles as an effective "reject" — but the UI
  must call it "Deactivate," never invent "Reject" wording for the same
  underlying call, since that would misrepresent what the backend
  actually recorded in the audit trail).

### 4.3 System Admin protection in the UI (RECOMMENDED, grounded in §2.5)

Since no endpoint can ever resolve a SYSTEM_ADMIN id, there is **no
frontend check to build** here — not a missing feature, a structural
non-issue. The one UI-level implication: the Administrators list
(`GET /admins`) can, by construction, never include a SYSTEM_ADMIN row
in its `items` (the repository query itself filters
`role == UserRole.ADMIN`), so there is nothing for the frontend to
filter out either. **The UI must not add a defensive
"hide-if-SYSTEM_ADMIN" check on rows it renders** — that would be
frontend-invented authorization logic for a case the backend has already
made impossible; adding it would only create a false impression that
the frontend is doing security work here, when it is not (§18).

---

## 5. Admin UX architecture

### 5.1 Users list (`/app/admin/users`, already slotted)

Table: Name, Email, Status (`UserStatus`), an "Authorize new User"
action. **One filter only**: `status` (§2.9 — no `department_id`
filter exists or would mean anything here; an Admin's list is always
already scoped to their own department server-side). No department
column — every row is, by construction, the viewing Admin's own
department; showing it would be redundant, not informative.

### 5.2 User detail (`/app/admin/users/:id`, new route)

Full `UserResponse` fields. Actions by status, mirroring §4.2's
Admin-detail pattern exactly but one level down:

* `PENDING_APPROVAL` → **Approve** (confirm — same one-time-transition
  reasoning as Admin approval).
* `ACTIVE` → **Deactivate**.
* `DEACTIVATED` → **Reactivate**.

**Critical distinction from the Admin-detail screen (§2.6, must not be
flattened in the UI)**: Approve and Reactivate here can fail with a
generic `403` (`DepartmentAccessDeniedError` → the *Admin's own*
department went inactive, not anything about the target User) —
**not** the `409` an Admin sees when the *target* isn't in the right
state. These need visibly different messages (§16): a `409` here means
"this User's own state doesn't allow this action right now"; a `403`
here means "your department currently can't perform this class of
action at all" — a `403` on Approve/Reactivate should be phrased around
the Admin's own department status, not the target User, e.g. "You do
not currently have permission to perform this action — this may be
because your department is not active." (mirrors the phrasing Phase 5
already recommended for the analogous Letter-side case,
`docs/architecture/frontend.md` §13). **Deactivate never returns this
403** (§2.6) — its error surface is limited to `404`/network/`500`; the
UI must not pre-emptively show a department-inactive warning banner on
an action that can't actually be blocked by it.

### 5.3 Pending User authorizations (`/app/admin/users/authorizations`, new route)

A separate list from the Users list itself — `GET /users/authorizations`
returns `UserAuthorization` rows (candidates who haven't signed up yet
or whose authorization was consumed/revoked), not `User` rows. Table:
Email, Status (`AuthorizationStatus` — **a third, distinct badge
domain**, §19), Created date, an inline **Revoke** action for
`ACTIVE` rows only. Filter: `status`. **RECOMMENDED**: default the view
to `status=ACTIVE` (the operationally relevant subset — a candidate
still waiting to sign up) with an explicit control to widen to "All"
(`USED`/`REVOKED` included) for department oversight, rather than
showing every historical row by default — a judgment call, not a
backend requirement (**PROVISIONAL**).

### 5.4 Revoke behavior (CONFIRMED, must be represented precisely)

`DELETE /users/authorizations/{id}` is **creator-scoped**, stricter than
this list's own department-wide visibility (§2.3) — an Admin can *see*
every authorization in their department but can only *revoke* the ones
they personally created. **RECOMMENDED**: the Revoke button/action is
present on every row (the list has no field telling the frontend up
front who created a given row without inspecting `authorized_by`, which
`UserAuthorizationResponse` does **not** expose — confirmed, that field
is absent from the response schema entirely), and a revoke attempt on a
row the Admin didn't create simply 404s like any other creator-mismatch
— rendered as the same generic "not found," never a distinguishing
"you didn't create this one" message (§18 — that would let an Admin
enumerate which authorizations belong to a colleague vs. themselves,
information this backend deliberately doesn't expose). This is the
correct application of §20's "prefer showing the action and handling a
backend rejection" instruction: hiding the button for rows the Admin
didn't create isn't possible without a field the API doesn't return, so
showing it and handling the 404 honestly is the only option, not a
shortcut.

### 5.5 Which actions survive an inactive department (RECOMMENDED table, directly derived from §2.6)

| Action | Requires Admin's own dept ACTIVE? | Backend evidence |
|---|---|---|
| List/view Users | No | `get_user`/`list_users` — no `assert_department_access` call |
| Deactivate User | No | unconditional |
| Revoke authorization | No | unconditional (creator-scope check only) |
| List authorizations | No | unconditional |
| Authorize new User | **Yes** (`403`) | `authorize_user` calls `assert_department_access(admin, admin.department_id)` |
| Approve User | **Yes** (`403`) | same call, added explicitly in `approve_user` |
| Reactivate User | **Yes** (`403`) | same call |

The Users screen should **not** disable the state-elevating buttons
pre-emptively based on a locally-cached notion of "my department is
inactive" — `UserPublic`/`AdminResponse` for the *calling* Admin
themselves has no live department-status field the frontend holds
outside of a fresh `/auth/me` (Phase 5's own confirmed gap,
`docs/architecture/frontend.md` §13, unchanged). **RECOMMENDED**: show
every action; let a genuine `403` surface the real state reactively,
exactly as Phase 5's review already concluded for the Letter side of
this same gap. Do not build a second, frontend-only prediction of
department status.

---

## 6. User management UX architecture (Admin's view — expands §5)

### 6.1 Authorization form (`/app/admin/users/authorize`, new route)

**Single field: `email`.** `UserAuthorizationCreate` has *no*
`department_id` field at all (§2.3) — there is nothing to select,
nothing to omit-to-avoid-leaking; the form cannot expose a department
picker because the schema has no slot for one to bind to even if the
UI tried. **This is the strongest possible structural guarantee against
department-injection for this specific form** — worth stating plainly
rather than merely "the frontend won't render one": there is no code
path, correct or malicious, by which a submitted department value could
reach this endpoint.

### 6.2 Duplicate / already-existing-user handling (CONFIRMED)

* Authorizing an email that already belongs to an `ACTIVE` User → `409`
  `"This email already belongs to an active User."` — render inline,
  field-level if practical (`errorNormalization.js` already extracts a
  plain-string `detail` into `message`, not `fieldErrors`, for this kind
  of `409` — same shape Phase 5C's Letter create/edit already handles,
  reused as-is).
* Authorizing an email with an existing unresolved (still-`ACTIVE`,
  §2.8 unexpired-in-practice) authorization → `409`
  `"This email already has an unresolved User authorization."`
* **Neither case distinguishes further** (e.g., doesn't say *whose*
  active authorization it is, or which department the existing User
  belongs to) — the frontend must render the message verbatim, never
  elaborate on it with information the backend didn't supply.

### 6.3 Fields that must never be injectable (CONFIRMED structural guarantee, not a frontend responsibility to additionally enforce)

Role, department, status, and authorization purpose all have this in
common on every authorization-creation form in this system: **the
request schema has no field for any of them**
(`UserAuthorizationCreate: {email}` only; `AdminAuthorizationCreate:
{email, department_id}` — `department_id` here is legitimate, since a
System Admin genuinely does choose a *destination* department, unlike
an Admin who has only one). `extra="forbid"` on both means even a
crafted request with an extra key gets a `422`, not a silently-ignored
field. **The frontend mirrors this contract by never building a form
field for any of them — it does not additionally "validate against
injection" itself, because there is nothing to validate against; the
absence of the field on the schema already is the enforcement**
(§9 of the brief's own instruction, directly satisfied).

### 6.4 What a `404` on a User-management screen must never say (RECOMMENDED, extending Phase 5C's classified-Letter discipline)

`UserNotFoundError` (§2.3) collapses **four** distinct backend
realities into one `404`: no such id at all, an id that belongs to a
`SYSTEM_ADMIN`, an id that belongs to an `ADMIN` (including the calling
Admin's own id — §2.5's self-protection), and an id that belongs to a
`USER` in a *different* department. A frontend "User not found" state
must render identically regardless of which of these actually happened
— exactly the same discipline `docs/architecture/frontend.md` §12
established for classified Letters, now extended to a second resource.
**Never**: "this account belongs to another department," "you cannot
manage this account type," or any language that would let an Admin
learn more than "not found" about an id they tried.

---

## 7. Department management UX architecture

Covered in full in §4.1. Summarizing the two policy questions the brief
specifically asked (§7):

* **Should related users/admins be displayed on a Department's detail
  page?** No count or list is available from `GET /departments/{id}`
  (§2.1 — the response has no such field, and there is no
  `GET /departments/{id}/users` or equivalent endpoint). Marked
  `PENDING BACKEND API` explicitly — **not** calculated by having the
  frontend separately call `GET /admins?department_id=...` and
  `GET /users` (which isn't even department-parameterizable for a
  System Admin caller — §2.3's `GET /users` is Admin-only, scoped to
  the caller's *own* department, so a SYSTEM_ADMIN cannot call it for
  an arbitrary department at all) and count client-side. That would be
  exactly the "calculate incorrectly on the frontend" the brief warns
  against in §7 — there is no legitimate way to compute this number
  from the current API surface for a SYSTEM_ADMIN viewer, so it is not
  attempted.
* **Should counts appear anywhere?** Same answer, same reason — `PENDING
  BACKEND API` (§22 for the exact form a future endpoint might take).

---

## 8. Authorization/approval lifecycle UX — full state matrix (CONFIRMED)

### 8.1 Admin lifecycle

```
(no row)
   │  POST /admins/authorizations  (SYSTEM_ADMIN, picks department)
   ▼
UserAuthorization{purpose=ADMIN, status=ACTIVE}
   │  candidate signs up against it (POST /auth/signup — Phase 3A, unchanged)
   ▼                                            \
User{role=ADMIN, status=PENDING_APPROVAL}         \  UserAuthorization.status → USED
   │  POST /admins/{id}/approve  (SYSTEM_ADMIN)      (irreversible — AuthorizationNotRevocableError
   ▼                                                  if anyone tries to revoke a USED row)
User{status=ACTIVE}
   │  POST /admins/{id}/deactivate  ⇄  POST /admins/{id}/reactivate  (SYSTEM_ADMIN, both idempotent)
   ▼
User{status=ACTIVE|DEACTIVATED}   (toggles indefinitely)
```

Separately, at any point before signup consumes it:

```
UserAuthorization{status=ACTIVE}
   │  no revoke endpoint exists for ADMIN-purpose authorizations (CONFIRMED —
   │  admins.py has no DELETE route; only users.py's authorizations are revocable)
   ▼
(cannot be revoked through this API — see §22)
```

### 8.2 User lifecycle — identical shape, one level down

```
(no row)
   │  POST /users/authorizations  (ADMIN, own department only)
   ▼
UserAuthorization{purpose=USER, status=ACTIVE}
   │  candidate signs up                              \  status → USED (irreversible)
   ▼                                                    \
User{role=USER, status=PENDING_APPROVAL}
   │  POST /users/{id}/approve  (ADMIN)
   ▼
User{status=ACTIVE}
   │  POST /users/{id}/deactivate  ⇄  POST /users/{id}/reactivate  (ADMIN, both idempotent)
   ▼
User{status=ACTIVE|DEACTIVATED}
```

And, unlike the Admin side, User-purpose authorizations **are**
revocable before use:

```
UserAuthorization{status=ACTIVE}
   │  DELETE /users/authorizations/{id}  (creating ADMIN only)
   ▼
UserAuthorization{status=REVOKED}   ← irreversible; no un-revoke endpoint
```

### 8.3 Which transitions are irreversible (RECOMMENDED UI treatment)

* `ACTIVE → USED` (either purpose) — irreversible, but not a user
  action at all; it happens as a side effect of signup. No UI needed.
* `ACTIVE → REVOKED` (User-purpose only) — **irreversible through this
  API**, a genuine user-initiated action. **RECOMMENDED**: the
  confirmation dialog for Revoke must say so plainly (§17) —
  "This cannot be undone. The candidate will need a new authorization
  to sign up." Never implies re-issuing is impossible (a System
  Admin/Admin can always create a fresh authorization for the same
  email later — confirmed, `find_unresolved`/`find_and_lock_active`
  only ever look at the current `ACTIVE` row, if any) — just that *this
  specific* authorization is spent.
* `PENDING_APPROVAL → ACTIVE` (Approve, either level) — not
  "irreversible" in the sense of losing data, but **not idempotent**
  either (§2.2/§2.3) — a second Approve click 409s rather than
  no-opping. **RECOMMENDED**: disable the Approve button immediately on
  click (standard submit-in-flight pattern already used by
  `LoginPage`/`SignupPage`/`LetterFormPage`) so a double-click can't
  even reach the backend twice, rather than relying on the 409 as the
  only guard.
* `ACTIVE ⇄ DEACTIVATED` (either level) — fully reversible, both
  directions idempotent. **RECOMMENDED**: Deactivate warrants
  confirmation (operational impact: an account loses access
  immediately); Reactivate does not (purely restorative — same
  reasoning as Department activation, §4.1, §17).

### 8.4 Which UI screens show each state

| State | Shown on |
|---|---|
| `UserAuthorization.status` (`ACTIVE`/`USED`/`REVOKED`) | The authorizations list only (§5.3) — never conflated with `UserStatus` on the account list |
| `UserStatus` (`PENDING_APPROVAL`/`ACTIVE`/`DEACTIVATED`) | The Admin/User list and detail pages |
| `ActiveStatus` (`ACTIVE`/`INACTIVE`) | The Department list and detail page only |

No screen in this design ever needs to show two of these three enums
side by side for the *same* row — each resource has exactly one status
domain, which is what keeps §19's "do not merge these enums" tractable
in practice, not just in principle.

---

## 9. Admin transfer UX (`PATCH /admins/{user_id}/department`)

### 9.1 What the backend actually does (CONFIRMED, re-read `change_admin_department` fresh)

Changes **only** `department_id` on the Admin's own `User` row. Nothing
else — no cascading update to any other table. Explicitly verified by
this backend's own docstring and a dedicated integration test
(`tests/integration/test_admin_management.py`, referenced directly in
`admin_service.py`'s module docstring): **historical Letters the Admin
previously recorded keep their original `recipient_department_id`
forever** — `Letter.recipient_department_id` is captured once, at
recording time, from the recorder's *then-current* department, and is
never re-derived from the recorder's row later. A transferred Admin's
past letters do not move with them, and are not retroactively
reassigned to either the old or new department beyond what they already
say.

### 9.2 Validation rules (CONFIRMED)

* Destination department must exist (`404` `"Department not found."`
  otherwise).
* Destination department must be `ACTIVE` (`409`
  `"The destination department is not ACTIVE."` otherwise) — **the
  source department's status is never checked** (an Admin can be
  transferred *out of* a currently-`INACTIVE` department without
  restriction; only the destination is gated).
* The target must resolve as an Admin (§2.5) — same generic `404`
  otherwise.

### 9.3 Recommended UI (`AdminTransferDialog`, on the Admin detail page)

A dialog, not a full-page form (the only input is a single department
selection): current department shown for context, a `<select>` of
`ACTIVE` departments only (populate from `departmentService.js`,
already built; **RECOMMENDED**: filter the dropdown to `ACTIVE` rows
client-side rather than relying on the backend to reject an `INACTIVE`
choice after the fact — a UX nicety, not a security boundary; the
backend's own `409` remains authoritative and still fires if a stale
dropdown briefly showed a department that went inactive between load
and submit). Confirmation copy must state, verbatim in spirit:

> "This changes only this Admin's current department going forward.
> Letters they've already recorded remain attached to the department
> they belonged to when recorded — this action does not move or
> reassign any historical record."

— directly answering §8's "confirm that historical letters are not
reassigned" instruction with the exact backend guarantee, not a
paraphrase that could drift from it. **RECOMMENDED**: this dialog is
the one Phase 5D confirmation that must **never** be skippable/
idempotent-shortcut, even though the write itself has no special
danger — the consequence (an Admin's future actions now apply to a
different department) is significant enough on its own merits (§17).

### 9.4 Effect on the Admin's own future access (CONFIRMED, worth stating in the dialog or a help note)

Immediate — `get_current_user` re-fetches the `User` row fresh on every
request (Phase 3A, unchanged), so a transferred Admin's very next API
call is already scoped to the new department; no re-login is needed or
possible to force. If the Admin has an active browser session showing
stale `department_id` in `AuthContext`'s cached `user`, that's a
**cosmetic** staleness only (Phase 5's own confirmed finding,
`docs/architecture/frontend.md` §13) — not a security gap, since the
backend re-derives authorization from the live row on every request
regardless of what the frontend has cached.

### 9.5 Effect on existing Users in either department

None. Transfer only ever touches the target Admin's own row. Users in
the old department are not reassigned to a different Admin, transferred,
or otherwise affected — there is no "Admin owns these Users" foreign
key anywhere in this schema; an Admin's authority over Users is entirely
derived, at request time, from matching `department_id`, not from any
stored assignment relationship.

---

## 10. Admin authorization UX (System Admin's workflow — expands §4.2's Authorize screen)

* **Required fields**: `email`, `department_id` (both required on
  `AdminAuthorizationCreate`, `extra="forbid"` — no optional fields
  exist on this schema at all).
* **Department selection**: a real `<select>` of departments —
  **RECOMMENDED**: `ACTIVE` only, same reasoning as §9.3's transfer
  dropdown (the backend will `409` an `INACTIVE` selection regardless;
  filtering the options is a UX nicety that reduces the odds of hitting
  that `409` in the first place, not a security measure).
* **Duplicate/existing-Admin handling**: identical shape to §6.2's User
  side — `409` for an email already belonging to an `ACTIVE` Admin,
  `409` for an unresolved existing authorization, both rendered
  verbatim.
* **Distinct concepts the UI must never conflate** (direct response to
  the brief's own §10 instruction):
  - **Authorization** — a `UserAuthorization` row; created by
    `POST /admins/authorizations`; means "this email *may* sign up as
    an Admin in this department." No `User` row exists yet.
  - **Signup** — `POST /auth/signup` (unchanged since Phase 3A); the
    candidate's own action, not anything a System Admin does through
    this UI; produces a `User{status=PENDING_APPROVAL}` and marks the
    authorization `USED`. **There is no "invite" or "signup on their
    behalf" capability anywhere in this backend** — the Authorize screen
    only ever creates the *permission* to sign up, never an account.
  - **Approval** — `POST /admins/{id}/approve`; a *separate*,
    later action against the resulting `User` row, once it exists,
    performed by the System Admin.
  - **Activation** — not a distinct concept for Admin *accounts*
    (`UserStatus` has no `ACTIVE`-vs-something-else step beyond
    Approve/Deactivate/Reactivate) — the word "Activate" in this
    document only ever refers to **Department** activation (`ActiveStatus`),
    a completely different resource and enum. **RECOMMENDED**: the UI
    never uses the word "Activate" as a button label for an Admin or
    User account, to avoid exactly this conflation — use "Approve" for
    the `PENDING_APPROVAL → ACTIVE` transition and "Reactivate" for
    `DEACTIVATED → ACTIVE`, matching the backend's own endpoint names
    precisely.

---

## 11. Lists, filtering & search — support matrix (CONFIRMED)

| Resource | Pagination | Search (text) | Status filter | Department filter | Sort |
|---|---|---|---|---|---|
| `GET /departments` | PENDING BACKEND API | PENDING BACKEND API | SUPPORTED (`ActiveStatus`) | n/a (is the resource) | PENDING BACKEND API (fixed `name asc` order, not client-selectable) |
| `GET /admins` | PENDING BACKEND API | PENDING BACKEND API | SUPPORTED (`UserStatus`) | **SUPPORTED** (`department_id`) | PENDING BACKEND API (fixed `created_at asc`) |
| `GET /users` | PENDING BACKEND API | PENDING BACKEND API | SUPPORTED (`UserStatus`) | n/a (always own department) | PENDING BACKEND API (fixed `created_at asc`) |
| `GET /users/authorizations` | PENDING BACKEND API | PENDING BACKEND API | SUPPORTED (`AuthorizationStatus`) | n/a (always own department) | PENDING BACKEND API (fixed `created_at asc`) |

Contrast with `GET /api/v1/letters` (Phase 4C, unchanged): full
pagination, four-field whitelisted sort, seven text filters. **None of
that exists for any Phase 5D resource.** §22 assesses whether returning
complete lists is acceptable for V1 given realistic data volumes (an
organization's department/admin counts; a single department's user
count) — a judgment call this document does not resolve unilaterally.

**RECOMMENDED, not backend-dependent**: a client-side, already-loaded-
data-only substring filter box on each list (matching against the
fields already present in the response, entirely in the browser, zero
additional requests) is a reasonable V1 convenience **as long as it is
never presented as "search"** in a way that implies server-side
semantics (e.g., no URL-synced `?search=` query parameter that looks
like it's driving a request the way Letters' filters do) — a purely
local, transient UI affordance, off by default in the sense that it
never changes what was fetched, only what's currently displayed from
what already was.

---

## 12. Navigation architecture

**"Navigation is discoverability only; backend authorization is the
security boundary."** — restated verbatim per the brief's own §12
instruction, and already the exact convention `navigationConfig.js`'s
own header comment and `RoleGuard`'s own header comment state today
(Phase 5A, unchanged) — Phase 5D does not introduce this principle, it
extends an already-established one.

`navigationConfig.js` (CONFIRMED, unchanged since Phase 5A) already
lists every nav entry Phase 5D needs to point somewhere real:

* `SYSTEM_ADMIN`: Letters, Documents, Notifications, **Departments**
  (`/app/system/departments`), **Administrators**
  (`/app/system/admins`), Categories, Classifications.
* `ADMIN`: Letters, Documents, Notifications, **Users**
  (`/app/admin/users`).
* `USER`: Letters, Documents, Notifications — **no administration
  entry**, confirmed unchanged; nothing in this phase adds one.

**No change to `navigationConfig.js`'s data is needed** — the three
entries this phase implements against (`Departments`, `Administrators`,
`Users`) already exist and already point at the exact paths this review
recommends building real pages at (§13). The only navigation work Phase
5D's eventual implementation performs is making those three links
resolve to real screens instead of `PlaceholderPage`.

---

## 13. Route architecture (RECOMMENDED, extends the already-slotted paths)

```
/app/system/departments                (already slotted — RoleGuard: SYSTEM_ADMIN)
/app/system/departments/new            (NEW)
/app/system/departments/:id            (NEW — detail + inline edit)

/app/system/admins                     (already slotted — RoleGuard: SYSTEM_ADMIN)
/app/system/admins/authorize           (NEW)
/app/system/admins/:id                 (NEW — detail + lifecycle actions + transfer)

/app/admin/users                       (already slotted — RoleGuard: ADMIN)
/app/admin/users/authorize             (NEW)
/app/admin/users/authorizations        (NEW — the separate UserAuthorization list, §5.3)
/app/admin/users/:id                   (NEW — detail + lifecycle actions)
```

Matches Phase 5C's own established shape exactly (`/app/letters`,
`/app/letters/new`, `/app/letters/:id`, `/app/letters/:id/edit`) — a
list route, a `/new` (or here, `/authorize`, since "creating an Admin/
User" is really "creating an authorization for one," a different verb
for a genuinely different action than Letters' `/new`) sibling, and a
`/:id` detail route. `RoleGuard` is applied **only at the existing
top-level route** (`/app/system/*`, `/app/admin/*`) exactly as it
already is for `system/letters` and `admin/users` today — **not**
re-applied on every child route individually, since React Router's
nested-route matching already means a `RoleGuard` on the parent covers
every child beneath it; duplicating the check on `:id`/`authorize`
sub-routes would be redundant code that could drift out of sync with
the parent's own guard, not additional real protection (the backend's
own role dependency is what actually blocks a non-`SYSTEM_ADMIN`/
`ADMIN` caller regardless of what the frontend renders).

**No `/app/system/departments/:id/edit`** — following Phase 5C's own
department-detail pattern recommendation (§4.1: one page, inline edit
mode), not a second route, since the edit surface here (two optional
text fields) is small enough that a route split would be pure ceremony.
This is a deliberate departure from `LetterFormPage`'s separate-route
convention, justified by the difference in form complexity — not an
inconsistency to silently resolve one way project-wide.

---

## 14. Component architecture (RECOMMENDED — only where real reuse exists)

### 14.1 `DataTable` — **not recommended as a new abstraction**

Four list screens (Departments, Admins, Users, Authorizations) each
have a small, fixed, resource-specific column set (2-5 columns) and no
shared sorting/pagination behavior to abstract over (§11 — none of
these lists are paginated or sortable server-side, unlike
`LetterTable`, which genuinely needed `aria-sort`/click-to-sort logic
worth centralizing). **RECOMMENDED**: four small, plain `<table>`
components — `DepartmentTable`, `AdminTable`, `UserTable`,
`AuthorizationTable` — each a thin, purpose-built presentational
component in the same spirit as `LetterTable`, but *not* a shared
generic `DataTable` wrapper. A generic table abstraction over four
tables with almost nothing in common structurally (different columns,
different action sets, no shared sort/paginate behavior to factor out)
would be exactly the "speculative abstraction" §14/§26 of the brief
warns against — reuse must be real, not assumed.

### 14.2 `ConfirmDialog` (generalize from `ArchiveConfirmDialog`) — RECOMMENDED

**Reused by**: Deactivate Department, Deactivate Admin, Deactivate User,
Revoke User authorization, Approve Admin, Approve User, Admin Transfer
(§9.3, as its base with an embedded `<select>` — see below) — at least
six to seven real call sites, a genuine reuse case unlike §14.1.
**Why it belongs in shared components**: `ArchiveConfirmDialog`
(Phase 5C) is already the exact accessible-dialog mechanics (focus
management, `Escape`-to-cancel, Tab-trap, `role="dialog"`/
`aria-modal`/`aria-labelledby`) every one of these needs, with only the
title/body copy and the destructive-vs-safe styling differing per
action. **RECOMMENDED shape**: `ConfirmDialog({title, message,
confirmLabel, onConfirm, onCancel, confirming, tone})` where `tone`
(`'default' | 'caution'`) only affects visual weight (never wording —
copy stays action-specific and precise, e.g. never a generic "Are you
sure?" for Revoke when the real consequence is "this cannot be undone,"
per §8.3/§17). `ArchiveConfirmDialog` itself would become a thin
wrapper passing its own fixed copy into `ConfirmDialog` — **not
required to actually refactor this phase** (review only), but the
shape is chosen so a future implementation phase can do so without
redesigning either component. **Owns**: dialog accessibility mechanics
and the confirm/cancel action pair. **Does not own**: which action is
being confirmed, or what happens after — that stays in each caller,
exactly like `ArchiveConfirmDialog` already keeps archival logic in
`LetterDetailPage`, not in the dialog itself.

### 14.3 `Pagination` — **not reused as-is; not needed this phase**

Built for Letters' real `page`/`page_size`/`total`/`total_pages`
response shape (§11 — none of Phase 5D's four resources have this).
**RECOMMENDED**: do not force-fit it (e.g., by wrapping a fully-loaded
list in fake single-page pagination props) — that would misrepresent
what's actually happening (everything already loaded) as if paging were
occurring. If §22's business question ("do these lists need pagination
for V1 data volumes") is ever answered "yes, and the backend adds it,"
`Pagination` already exists and would need zero changes to reuse
against a future `GET /departments?page=...` shape identical to
Letters' own. Until then, it has no role in Phase 5D.

### 14.4 `StatusBadge` — extend, not replace (RECOMMENDED, see §19 for the full tone table)

Already generic (`{value, label}`) and already used across Letter
status. **RECOMMENDED extension**: broaden `TONE_BY_VALUE` to cover
every value across all three Phase 5D-relevant enums (not just
Department's `ActiveStatus`, which it already half-covers) — see §19
for the exact proposed mapping — and add an optional `domain` prop
purely for an accessible label prefix (e.g., rendering "User status:
Active" for a screen-reader user rather than a bare, ambiguous
"Active"), never for a different visual system per domain (one
consistent badge look across the whole app remains correct — Phase 5's
own §18 recommendation, "one parameterized `StatusBadge` component so
the three never visually blend into each other," is satisfied by the
distinct *labels*/*context*, not by three different-looking badge
components).

### 14.5 `AuthorizationForm` — **not recommended as one shared component**

The brief's own example list (§14) suggests this, but the two real
forms (`AdminAuthorizationCreate {email, department_id}` vs.
`UserAuthorizationCreate {email}`) differ by exactly one field — a
department selector that only one of the two forms has at all (§6.1/
§10). **RECOMMENDED**: two small, separate form components
(`AdminAuthorizeForm`, `UserAuthorizeForm`), not one parameterized
component branching on a `hasDepartmentField` prop — the field
difference here isn't incidental styling, it's the exact structural
guarantee against department-injection §6.3 documents; collapsing the
two into one conditionally-rendered component would make that guarantee
harder to see at a glance in the component's own code, for a genuinely
small amount of saved duplication (one email input, one submit button).
A small, real disagreement between two "similar-looking" forms is
better served by two small components than one branching one — matches
this project's own "three similar lines is better than a premature
abstraction" convention.

### 14.6 `DepartmentSelector` — RECOMMENDED, real reuse

**Reused by**: Admin Authorize form (§10), Admin Transfer dialog (§9.3),
the Administrators list's department filter (§4.2), and — already
existing, confirming the pattern — `LetterFormPage`'s own SYSTEM_ADMIN-
only category/classification selects follow the identical shape (Phase
5C). **RECOMMENDED shape**: a `<select>` wrapper taking `departments`
(already-loaded array from `departmentService.js`), `value`, `onChange`,
and an `activeOnly` flag (default `true`, per §9.3/§10's own
recommendation to default to `ACTIVE`-only options) — thin enough that
it may not be worth a dedicated file if only 3-4 call sites end up using
it (a genuine judgment call for whoever implements this — **PROVISIONAL**,
not mandated either way by this review).

### 14.7 `AccountActionMenu` — **not recommended**

The brief's example list suggests this, but every detail screen in this
design (§4.2, §5.2) has at most 2-3 mutually-exclusive actions
determined entirely by the current status (§8.3's table) — a fixed set
of 1-2 visible buttons, not an overflow menu. Introducing a menu
abstraction for 2 buttons is exactly the "do not over-engineer" case
§14 warns against; plain, directly-visible buttons (matching
`LetterDetailPage`'s own Edit/Archive pattern, Phase 5C) are simpler and
more accessible (no extra disclosure interaction needed to reach a
primary action) than a menu would be here.

---

## 15. API service architecture (RECOMMENDED — extends the existing convention exactly)

Following `letterService.js`'s established shape (Phase 5C: named
exports, one function per endpoint, an explicit field allowlist on
every write, no raw Axios calls outside the service layer):

```
departmentService.js  (ALREADY EXISTS — Phase 5C, currently list() only)
  list()                          → GET  /departments               [existing, reused]
  get(id)                         → GET  /departments/:id           [NEW]
  create(fields)                  → POST /departments                [NEW]
  update(id, fields)              → PATCH /departments/:id          [NEW]
  activate(id)                    → POST /departments/:id/activate  [NEW]
  deactivate(id)                  → POST /departments/:id/deactivate[NEW]

adminService.js  (NEW FILE)
  list(params)                    → GET  /admins  (department_id?, status?)
  get(id)                         → GET  /admins/:id
  authorize(fields)               → POST /admins/authorizations
  approve(id)                     → POST /admins/:id/approve
  deactivate(id)                  → POST /admins/:id/deactivate
  reactivate(id)                  → POST /admins/:id/reactivate
  changeDepartment(id, fields)    → PATCH /admins/:id/department

userService.js  (NEW FILE)
  list(params)                    → GET  /users  (status?)
  get(id)                         → GET  /users/:id
  approve(id)                     → POST /users/:id/approve
  deactivate(id)                  → POST /users/:id/deactivate
  reactivate(id)                  → POST /users/:id/reactivate
  authorize(fields)                → POST /users/authorizations
  listAuthorizations(params)      → GET  /users/authorizations  (status?)
  revokeAuthorization(id)         → DELETE /users/authorizations/:id
```

**RECOMMENDED**: extend the existing `departmentService.js` rather than
creating a second department module — it already exists (Phase 5C),
already follows the right shape, and its current single `list()` export
is a strict subset of what Phase 5D needs; the file's own Phase 5C
header comment ("used only by the SYSTEM_ADMIN Letters view... not a
Departments management UI") would need updating to reflect its
broadened role once actually implemented, but the module boundary
itself is already correct. `userService.js`/`adminService.js` are new
because no prior phase touched either resource — following the exact
naming convention `letterService.js` already set, not inventing a new
one. Every write function (`create`/`update`/`authorize`/
`changeDepartment`) uses an explicit field allowlist mirroring
`letterService.js`'s `pickFields`/`CREATE_FIELDS` pattern — so
`role`/`status`/`authorized_by`/`recorded_by`-shaped fields can never
reach a request body from this layer even if a caller's local state
somehow carried one (defense in depth on top of, not instead of, the
backend's own `extra="forbid"` schemas — §18).

---

## 16. Error-handling matrix (CONFIRMED status codes; RECOMMENDED presentation)

| Status | When it occurs here | Presentation |
|---|---|---|
| `401` | Token missing/invalid/expired, or the account is no longer `ACTIVE` | Already handled centrally — `apiClient.js`'s existing 401 handler clears the session and redirects to `/login` (Phase 5A/5B, unchanged); no Phase 5D screen needs its own 401 handling |
| `403` | Role dependency rejection (a `USER` reaching an Admin/System-Admin-only route — should not normally happen given `RoleGuard`, but the backend, not the frontend, is what actually enforces this); **or** a state-elevating action's own-department-inactive check (§2.6, `authorize_user`/`approve_user`/`reactivate_user` only) | Page-level `ErrorState` for the role-rejection case (this shouldn't be reachable via the UI's own links, only via a manually-typed URL — same as any `RoleGuard`-fronted route today); **inline, action-specific** banner for the department-inactive case, phrased around the *caller's* department, never the target (§5.2) |
| `404` | Target id doesn't resolve for this endpoint set — covers nonexistent, wrong-role, and (Users only) cross-department, all identically (§2.5/§6.4) | Generic "not found" — **never** elaborated, **never** distinguished by cause (§18) |
| `409` | A state/business-rule conflict: not-pending-approval (Approve), destination-not-active (Admin authorize/approve/reactivate/transfer), duplicate email/unresolved authorization (both Authorize forms), already-used (Revoke), duplicate name/code (Department create/update) | Inline, verbatim backend message — every one of these is already a specific, human-readable string (§6.2/§10); never remapped to a generic "conflict occurred" |
| `422` | Field validation (blank required field, malformed email, `DepartmentUpdate`'s "at least one of name/code" rule) | Field-level via `errorNormalization.js`'s existing array-`detail` → `fieldErrors` extraction — same mechanism `LetterFormPage`/`SignupPage` already use, unchanged |
| `500` | Unhandled server error | Generic `ErrorState`, `errorNormalization.js`'s existing fallback message — never a raw stack trace or internal detail |
| Network failure (`status: 0`) | Server unreachable | Generic `ErrorState` with `onRetry`, same pattern every Phase 5C list/detail screen already uses |

**Never** (direct response to §16/§18's explicit instructions): convert
a `403` into `404`-shaped copy or vice versa — they mean structurally
different things here (§16's own table shows a `403` is sometimes about
the *caller's* state, never the target's; a `404` is always about
target resolution) and collapsing them would destroy exactly the
distinction §5.2 depends on to phrase the department-inactive case
correctly.

**Which errors trigger what** (RECOMMENDED, matching Phase 5C's
existing per-surface conventions exactly — no new pattern invented):
list-load failures → page-level `ErrorState` with `onRetry` (matches
`LetterListPage`); form-submission failures → inline banner above the
form, field errors inline per field (matches `LetterFormPage`/
`SignupPage`); action-button failures (approve/deactivate/revoke/etc.
from a detail page or list row) → an inline banner near the action,
**not** a full-page error state and **not** a silent toast — the action
context (which row, which button) must remain visible so the user can
immediately retry or understand what failed, mirroring how
`LetterDetailPage`'s own archive-failure handling already keeps the
dialog open with an inline error rather than navigating away (Phase
5C). No refresh is ever triggered automatically on a failure; a refresh
*is* triggered automatically on a **success** that changes the row
being viewed (e.g., after Deactivate succeeds, re-render the same
detail page with the now-current status, exactly as `LetterDetailPage`
already does after a successful archive).

---

## 17. Confirmation / action matrix (RECOMMENDED, direct answer to §17's checklist)

| Action | Confirm? | Reasoning |
|---|---|---|
| Deactivate Department | **Yes** | Idempotent write, but real operational impact on every Admin/User in it (§4.1) |
| Activate Department | No | Purely restorative; nothing lost |
| Deactivate Admin | **Yes** | Same reasoning as Department — immediate loss of access |
| Reactivate Admin | No | Restorative; the backend's own `409` (if the Admin's department isn't ACTIVE) already prevents a broken outcome |
| Transfer Admin | **Yes, and never skippable** | Not idempotent-adjacent at all — a genuine, consequential state change (§9.3) |
| Approve Admin | **Yes** | Not idempotent (§8.3) — confirming prevents an avoidable `409` from a double-click, not just "big decision" theater |
| Authorize Admin | No | Creates an authorization, not an account — low-stakes, reversible in spirit (no endpoint to revoke it, §22, but nothing *irreversible happened to an existing account* either) |
| Deactivate User | **Yes** | Same reasoning as Admin deactivation |
| Reactivate User | No | Same reasoning as Admin reactivation |
| Approve User | **Yes** | Same not-idempotent reasoning as Admin approval |
| Authorize User | No | Same reasoning as Admin authorization |
| Revoke User authorization | **Yes, and state plainly it cannot be undone** | Genuinely irreversible through this API (§8.3) |

**Never** "Delete" wording anywhere in this matrix — confirmed nothing
in this design ever performs or needs to imply physical deletion;
"Deactivate"/"Revoke" are the correct, backend-accurate verbs
throughout, matching Phase 5C's own "Archive, never delete" precedent
exactly.

---

## 18. Security review

Frontend-side review, backend re-verified as the actual boundary in
every case (not re-litigated — see §2 for the citations):

* **Role spoofing** — not possible from this frontend: `user.role`
  always comes from `/auth/me` or the login response's own
  server-derived `UserPublic` (Phase 5A/5B, unchanged); nothing in this
  design reads or trusts a role from `localStorage`, a route param, or
  any client-constructed value. Every Phase 5D screen's `RoleGuard`
  usage (§13) is UX-only, exactly as `navigationConfig.js` already
  documents — the backend's own `require_system_admin`/`require_admin`
  dependencies (§2) are what actually block a mismatched role.
* **Department spoofing** — structurally prevented, not merely
  discouraged, for the User-authorization path (§6.1/§6.3 — the schema
  has no field). For Admin authorization/transfer, where a department
  *is* legitimately selectable, the frontend never lets that selection
  cross a boundary the backend wouldn't already enforce independently
  (§9.2/§10 — the backend validates existence and `ACTIVE` status on
  every write regardless of what the dropdown showed).
* **IDOR** — every id-scoped endpoint in this design (`GET/POST
  /admins/{id}/*`, `GET/POST /users/{id}/*`) is itself the backend's
  own authorization boundary (§2.5/§2.3's collapsed-404 pattern); the
  frontend never assumes a route param it can read (`:id`) implies
  permission to act on it — every action still goes through the real
  request and handles a `404`/`403` honestly.
* **Cross-department access** — `UserNotFoundError`'s 404-collapse
  (§2.3/§6.4) is the actual defense; the frontend adds nothing on top
  and takes nothing away from it — it renders exactly what comes back.
* **System Admin targeting** — structurally impossible (§2.5/§4.3); no
  frontend code needed or added.
* **Admin self-targeting** — structurally impossible (§2.5); same.
* **Pending account exposure** — a `PENDING_APPROVAL` Admin/User is
  visible only to the exact caller already authorized to see it
  (System Admin for Admins; the owning department's Admin for Users) —
  no new exposure surface introduced; the list/detail screens render
  exactly what their existing role-gated endpoint already scopes.
* **Authorization enumeration** — `AuthorizationNotFoundError`'s
  creator-scoped 404 (§5.4) is rendered without elaboration, exactly as
  designed; the frontend never tries to distinguish "doesn't exist" from
  "exists but isn't yours" in what it displays.
* **Inactive department behavior** — §2.6/§5.5's table is the complete,
  correct picture; no frontend-only prediction of department status is
  built (§5.5 explicitly recommends against it).
* **Token handling** — unchanged from Phase 5A/5B; `tokenStorage.js`
  remains the one place a token is read/written; no Phase 5D screen
  introduces a second token-handling path.
* **Sensitive response rendering** — `AdminResponse`/`UserResponse`
  have no `password_hash` field to accidentally render (§2.2/§2.3,
  structural, same guarantee `UserPublic` already has); nothing in this
  design ever displays a password, hash, or raw JWT.
* **Classified record leakage** — not applicable to this phase's
  resources (Departments/Admins/Users/Authorizations carry no
  classification concept); noted only to confirm this phase does not
  reintroduce or interact with Letters' classified-access discipline in
  any way.
* **Stale UI state after deactivation/reactivation** — addressed by
  §16's "refresh on success" convention: every lifecycle action
  re-renders the affected row/detail page from the action's own
  response (the backend returns the updated `AdminResponse`/
  `UserResponse`/`DepartmentResponse` directly — no separate re-fetch
  needed or performed), so the UI can never show a status the backend
  no longer agrees with after a successful action. A *list* screen that
  was open in another tab, or before a colleague's concurrent action,
  can still show a stale row until manually refreshed — **RECOMMENDED**:
  no auto-polling is added for this (no such mechanism exists anywhere
  in this frontend, and inventing one here would be scope creep beyond
  this phase's own objective) — a manual refresh affordance (already
  present as a pattern on `LetterListPage`, Phase 5C) is sufficient and
  consistent.
* **Race conditions around approve/revoke/deactivate** — the backend's
  own idempotency/non-idempotency choices (§8.3) are what actually
  govern outcomes under a race (e.g., two Admins clicking Approve on the
  same pending User simultaneously — the second request 409s, it does
  not corrupt state); the frontend's only job is to surface that 409
  honestly (§16), not to add optimistic locking or a second guard of
  its own.
* **Frontend/backend disagreement** — mitigated by never computing a
  status, permission, or count client-side that the backend itself
  doesn't return (§4.1's explicit refusal to client-count Users/Admins
  per Department; §5.5's explicit refusal to predict department-active
  state) — every displayed fact in this design traces to a field the
  backend actually sent for that exact request.

**The frontend must never** (verbatim from the brief's §18, confirmed
nothing in this design violates any of these): decode a JWT to
determine authorization — not done; trust role data from
`localStorage` — not done, `tokenStorage.js` stores only the token
string, never a role/status snapshot; trust route parameters as
permission — not done, every `:id` route still makes a real,
backend-authorized request; infer department access independently —
not done (§5.5); hide security errors by converting `403` to `404` or
vice versa — not done (§16's table keeps them distinct); manufacture
success states — not done, every success state in this design comes
from an actual `2xx` response body, never assumed client-side.

---

## 19. State matrix — three enums, never merged (direct response to §19)

| Enum | Values | Shown on | `StatusBadge` tone (RECOMMENDED extension of §14.4) |
|---|---|---|---|
| `UserStatus` | `PENDING_APPROVAL`, `ACTIVE`, `DEACTIVATED` | Admin list/detail, User list/detail | `PENDING_APPROVAL → warning` (new tone), `ACTIVE → positive` (existing), `DEACTIVATED → neutral` (existing) |
| `AuthorizationStatus` | `ACTIVE`, `USED`, `REVOKED` **(no `PENDING`, no `EXPIRED` — §2.7, correcting the brief's own §19 assumption)** | Authorizations list only (§5.3) | `ACTIVE → positive`, `USED → neutral`, `REVOKED → negative` (new tone) |
| `ActiveStatus` | `ACTIVE`, `INACTIVE` | Department list/detail only | `ACTIVE → positive` (existing), `INACTIVE → neutral` (existing) |

Each enum's `ACTIVE` label means something different in context
("this account can currently be used" vs. "this authorization hasn't
been consumed or revoked yet" vs. "this department is currently
operational") — **RECOMMENDED**: the badge's own visually-adjacent
label text (already how `StatusBadge` is used today — `label` is
always a human phrase, e.g. "Active," never the bare enum token) plus
the surrounding column header/section heading ("Status" in a table
whose other columns already establish it's an Authorization row, an
Admin row, etc.) is sufficient context — **not** three visually
distinct badge *styles* per domain, which would work against the "one
consistent badge look" principle Phase 5's own review already
established (§14.4).

---

## 20. Accessibility / responsive strategy (RECOMMENDED — extends Phase 5C's baseline, no new pattern)

Every element already established and proven across Phase 5A-5C, applied
identically here: semantic `<table>` markup (`scope="col"`/`scope="row"`,
matching `LetterTable`); real `<label htmlFor>` on every form field with
`aria-invalid`/`aria-describedby` field errors (matching
`LetterFormPage`/`SignupPage`); `aria-current="page"` — **not
applicable this phase** (no pagination exists to have a "current page,"
§11/§14.3); `aria-expanded` — **not needed**, no disclosure/expandable
UI is recommended anywhere in this design (§14.7 explicitly rejects the
one candidate, an action menu, that would have needed it);
`role="dialog"`/`aria-modal`/keyboard-trapped/`Escape`-dismissible for
every confirmation (`ConfirmDialog`, §14.2, reusing
`ArchiveConfirmDialog`'s already-accessible mechanics exactly);
`role="alert"` for submission-level errors, `role="status"` for
loading/success, matching `ErrorState`/`LoadingState` unchanged.
**Desktop-first, justified**: this project's frontend has been
desktop-first since Phase 5A's own architecture review concluded it
(internal, government-network, workstation-based usage — unchanged
assumption, not revisited here); administration screens follow the same
responsive floor already proven on the Letter registry — a horizontally
scrollable table container on narrow viewports (`overflow-x: auto`,
matching `LetterTable.module.css`'s existing pattern) rather than
column-dropping or a card-based mobile layout, and single-column forms
below the existing tablet breakpoint (matching `LetterFormPage`/
`LetterFilters`). **No CSS framework** — none exists in this repository
today (Phase 5A's own explicit decision, unrevisited); CSS Modules +
`styles/tokens.css` continue to be the only styling mechanism.

---

## 21. Test strategy (design only — no test code written this phase)

Following the exact test-file-per-page/component convention Phase 5C
established (one `.test.jsx` per real page/component, integration-style
against a mocked service layer, `AuthContext` mocked via the same
`vi.mock('../context/AuthContext', ...)` pattern already used
throughout `LetterListPage.test.jsx`/`LetterFormPage.test.jsx`):

**System Admin (RECOMMENDED ~28-34 tests)**:
Department list (success/empty/error/status-filter — 4), Department
create (validation/success/409-name/409-code — 4), Department detail
+ edit (load/edit-success/422 — 3), Department activate/deactivate
(idempotent success, confirmation-required-for-deactivate-only — 3),
Admin list (success/empty/error/status+department-filter — 4), Admin
authorize (validation/success/404-dept/409-not-active/409-duplicate/
409-unresolved — 6), Admin detail + lifecycle (approve-success/
approve-409-not-pending/deactivate/reactivate-success/reactivate-409-
dept-not-active — 5), Admin transfer (dialog-copy-states-no-
reassignment/success/404-dept/409-not-active — 4), System Admin
protection (a manually-navigated id that resolves to no Admin renders
generic not-found — 1).

**Admin (RECOMMENDED ~22-26 tests)**:
User list (success/empty/error/status-filter — 4), User authorize
(validation/success/409-duplicate/409-unresolved/no-department-field-
in-payload — 5), User detail + lifecycle (approve-success/approve-409/
approve-403-own-dept-inactive/deactivate/reactivate-success/
reactivate-403 — 6), Authorizations list (success/status-filter/
revoke-success/revoke-409-used/revoke-404-not-creator — 5),
cross-department denial (a 404 renders generically, no
department-mismatch language — 1), inactive-department behavior
(deactivate/revoke remain available while authorize/approve/reactivate
correctly show the 403 state — 2), self-targeting protection (same
structural-404 assertion as System Admin's — 1).

**Shared (RECOMMENDED ~14-18 tests)**:
`ConfirmDialog` accessibility (focus/Tab-trap/Escape — reusing
`ArchiveConfirmDialog.test.jsx`-equivalent coverage, adapted — 3-4),
`StatusBadge` tone/label coverage across all three enums (extending the
existing component, if it has no dedicated test file yet — 1 new file,
~3 cases), API error-normalization reuse (no new tests needed — already
covered by `errorNormalization.test.js`, Phase 5A, unaffected by this
phase), navigation visibility per role (extending
`navigationConfig.test.js` only if the data itself changes — it
doesn't, per §12, so likely zero new tests here), route protection
(extending `ProtectedRoute.test.jsx`/adding `RoleGuard` coverage for the
three newly-real routes, if not already generically covered — 2-3),
stale-data-refresh-on-success (one representative test per resource
confirming a detail page re-renders the response body directly rather
than requiring a second fetch — 3), loading/empty/error states
(folded into each page's own test file already counted above, not a
separate suite).

**Total RECOMMENDED range: roughly 64-78 new tests**, bringing the
suite from Phase 5C's 84 to somewhere in the **148-162** range —
comparable in density to Phase 5C's own ratio of tests to screens
(84 tests / 3 pages + 5 components ≈ 10-11 per unit; Phase 5D's 7 new
pages + ~6 new components at a similar density lands in this range).
**Not implemented this phase** — a planning estimate only, to be
revised against whatever the actual implementation phase's component
boundaries turn out to be.

---

## 22. Business/policy gap identification

**CONFIRMED** (re-verified backend facts, not open questions):
§2's entire endpoint/schema/status-code table; §2.5's structural
System-Admin/self-targeting protection; §2.6's read/lock-down vs.
state-elevating asymmetry; §2.7's exact enum values (correcting the
brief's own `PENDING`/`EXPIRED` assumption); §2.8's `expires_at`-never-
set finding; §2.9/§11's no-pagination-anywhere-but-Letters finding;
§9.1's historical-Letters-never-reassigned-on-transfer finding.

**PROVISIONAL** (explicit judgment calls this document made, flagged
for revisiting): §5.3's default-to-`ACTIVE`-authorizations-view choice;
§9.3/§10's default-`ACTIVE`-only department-dropdown filtering;
§14.6's "may not need a dedicated `DepartmentSelector` file" sizing
call; §17's full confirm/no-confirm matrix (a reasoned but not
backend-mandated set of choices).

**PENDING BUSINESS CLARIFICATION**:
* Whether Admin/User/Authorization/Department lists need pagination at
  actual expected V1 data volumes (§11/§22) — this document does not
  know the organization's real department count or per-department user
  count, and does not guess.
* Whether authorization expiration (§2.8) is ever going to be a real
  requirement, given `expires_at` exists structurally but nothing sets
  it today.
* Whether Admin-purpose authorizations should become revocable (§8.1 —
  currently structurally impossible, no endpoint exists, unlike User-
  purpose authorizations) — a real asymmetry between the two lifecycles
  worth a deliberate business decision, not a silently-assumed "should
  probably match."
* Whether account history (a timeline of status changes per Admin/User,
  distinct from the raw `AuditLog` rows Phase 4E already generates but
  doesn't expose through any read API) should ever be user-facing.
* Whether notification behavior should ever expose account-management
  events (e.g., notifying a candidate their account was approved) — no
  such notification type exists in Phase 4E's confirmed trigger set
  (only "letter registered"); not proposed here.

**PENDING BACKEND API**:
* Department-scoped user/admin counts (§7/§22) — no field, no endpoint.
* Pagination/search/sort on any of the four Phase 5D resources (§11) —
  no query parameters exist beyond the one or two exact filters each
  supports.
* A System-Admin-facing audit view (§22, brief's own question) — Phase
  4E's `AuditLog` is populated but has no read endpoint at all
  (`docs/architecture/audit-notifications.md`'s own confirmed, standing
  gap, unrelated to and unresolved by this phase).
* Revocation for Admin-purpose authorizations (§8.1/§22, above).

---

## 23. Explicit confirmation: this review does NOT implement

No frontend page, React component, CSS file, or API service module was
created or modified. No backend endpoint, schema, service, repository,
model, or migration was created or modified. No test code of any kind
was written. No dashboard, audit UI, new authorization rule, or new
business rule was introduced — every rule described above is a
restatement of an already-existing, freshly-re-verified backend
behavior, never an invention. `git status` before and after this
session is unchanged except for this new documentation file and the
supporting `docs/PROJECT_STATUS.md`/`README.md`/`docs/README.md`
updates every prior review-only phase (4A, 4D's review, 4E's review,
Phase 5's review) has also made — no source file under `frontend/src/`
or `backend/app/` was touched.

---

## 24. Recommended implementation sequence for Phase 5D (when instructed)

1. Extend `departmentService.js`; add `adminService.js`/`userService.js`
   (§15) — pure data layer first, no UI, matching how Phase 5C started
   with `letterService.js`.
2. Extend `StatusBadge` (§14.4/§19) and build `ConfirmDialog` (§14.2) —
   the two genuinely shared primitives, before any page needs them.
3. Departments: list → create → detail/edit → activate/deactivate
   (§4.1) — the simplest resource (fewest states, no lifecycle
   asymmetry), a good first vertical slice end-to-end.
4. Users (Admin's own view): list → authorize → authorizations list →
   detail/lifecycle (§5, §6) — before Admins, since it's one level
   simpler (no transfer, no department-selection-on-authorize).
5. Admins (System Admin's view): list → authorize → detail/lifecycle →
   transfer (§4.2, §9, §10) — transfer last, as the most security-
   sensitive single action in this phase.
6. Test suite alongside each vertical slice (§21), not deferred to the
   end — matching every prior implementation phase's own practice.
7. Documentation update (this same file, extended with an
   implementation-record section — matching §34/§35/§36 of
   `docs/architecture/frontend.md`'s own established pattern) once
   built.

---

## 25. Explicit scope confirmation

This phase produced: one new architecture document (this file) and
updates to `docs/PROJECT_STATUS.md`, `README.md`, and `docs/README.md`
recording that this review exists and what it covers — the same
documentation-only footprint every prior review-only phase in this
project has left. It did **not** produce: any file under
`frontend/src/`, any file under `backend/app/` or `backend/alembic/`,
any test file, any migration, any dashboard, any audit UI, any new
authorization rule, or any new business rule. Phase 5D implementation
begins only when explicitly instructed, per this project's standing
rule that phases are reviewed before the next begins.

---

## 26. Implementation record — IMPLEMENTED

Built directly on §1-25's own design — no new architecture decisions,
only the ones already recommended, built. Every item below is
IMPLEMENTED unless marked otherwise (CONFIRMED/PROVISIONAL/PENDING).

### Services (§15, §21) — IMPLEMENTED

`services/departmentService.js` extended from its Phase 5C
single-export shape (`list()` only) to the full data layer:
`list(params)`/`get(id)`/`create(fields)`/`update(id, fields)`/
`activate(id)`/`deactivate(id)` — `list()`'s original zero-arg call
sites (Phase 5C's `LetterListPage`) are unaffected, since `params`
defaults to `{}`. Two new modules, `services/adminService.js` and
`services/userService.js`, map one function per confirmed endpoint
exactly as §15 specified — no method exists for an endpoint that
doesn't exist, and no write function accepts more fields than its
matching backend schema does (`adminService.authorize` destructures
only `{email, department_id}`; `userService.authorize` only `{email}` —
there is no code path by which an extra key could reach either request
body).

### Components (§14) — IMPLEMENTED

`components/ConfirmDialog.jsx` — the generalized dialog §14.2
recommended, reusing `ArchiveConfirmDialog`'s exact accessible-dialog
mechanics (focus management, Tab-trap, `Escape`, `role="dialog"`);
`ArchiveConfirmDialog` itself was left untouched, per this phase's own
"no Letter functionality changes" scope boundary. `components/
AdminTransferDialog.jsx` — a specialized dialog (own department-select
state, its own three-element Tab-trap) rather than built on
`ConfirmDialog`, per §14.2's own reasoning. `components/
DepartmentSelector.jsx` — `forwardRef`-wrapped (needed for
`AdminTransferDialog`'s initial-focus management), reused across the
Admin Authorize form, the Admin Transfer dialog, and the Administrators
list's department filter — three real call sites, matching §14.6.
`components/DepartmentTable.jsx`/`AdminTable.jsx`/`UserTable.jsx`/
`AuthorizationTable.jsx` — four small, purpose-built tables sharing one
stylesheet (`DataTable.module.css`), per §14.1's explicit rejection of
a generic `DataTable` abstraction (no sortable-header logic needed,
unlike `LetterTable` — §11 confirmed none of these four resources
support backend sorting). `components/DepartmentForm.jsx` — fields
only, no `<form>`/submit, reused by `DepartmentCreatePage` and
`DepartmentDetailPage`'s inline edit mode. `StatusBadge` extended
(not replaced) with two new tones (`warning` for `PENDING_APPROVAL`,
`negative` for `REVOKED`) and an optional `domain` prop for an
accessible-name prefix — a global `.sr-only` utility was added to
`styles/global.css` to support it, the one addition to a Phase 5A
foundation file this phase made.

`routes/RoleGuard.jsx` was extended (not replaced) to render
`<Outlet/>` when used with no `children` prop — a backward-compatible
change (every existing call site still passes `children` explicitly)
that lets a whole route group (`/app/system/admins/*`,
`/app/system/departments/*`, `/app/admin/users/*`) share one guard
instance as a layout route, rather than repeating the wrap on every
child route, directly fulfilling §13's own "not re-applied on every
child route individually" instruction.

### Pages and routes (§4-§13) — IMPLEMENTED

| Route | Page | Notes |
|---|---|---|
| `/app/system/departments` | `DepartmentListPage` | status filter only (§11) |
| `/app/system/departments/new` | `DepartmentCreatePage` | |
| `/app/system/departments/:id` | `DepartmentDetailPage` | inline edit mode, not a separate route (§13's own justified departure from `LetterFormPage`'s convention) |
| `/app/system/admins` | `AdminListPage` | status + department filters (§11) |
| `/app/system/admins/authorize` | `AdminAuthorizePage` | |
| `/app/system/admins/:id` | `AdminDetailPage` | approve/deactivate/reactivate/transfer, status-gated per §8.3 |
| `/app/admin/users` | `UserListPage` | status filter only; no department parameter exists (§11) |
| `/app/admin/users/authorize` | `UserAuthorizePage` | single `email` field — no department field exists on the schema at all (§6.1) |
| `/app/admin/users/authorizations` | `UserAuthorizationsPage` | separate `UserAuthorization` resource; defaults to `status=ACTIVE` (PROVISIONAL, §5.3) |
| `/app/admin/users/:id` | `UserDetailPage` | approve/deactivate/reactivate, 403 phrased around the Admin's own department (§5.2) |

`navigationConfig.js` required **no change** — CONFIRMED, verified
fresh this phase: its three relevant entries (`Departments`,
`Administrators`, `Users`) already pointed at these exact paths since
Phase 5A.

### Confirmation matrix (§17) — IMPLEMENTED exactly as designed

Deactivate (Department/Admin/User) and Revoke (User authorization) are
confirmed, with `tone="caution"`; Approve (Admin/User) is confirmed
(`tone="default"`) to avoid an avoidable `409` from a double-click;
Activate (Department) and Reactivate (Admin/User) are not confirmed —
purely restorative actions, matching §17's table exactly. No screen
anywhere in this implementation uses "Delete" — confirmed by grep,
zero matches outside test fixtures/regex patterns checking for its
*absence*.

### The 403-vs-409 distinction (§2.6/§5.2) — IMPLEMENTED, verified by test

`UserDetailPage`'s Approve/Reactivate failure handling phrases a `403`
specifically around the Admin's own department
("You do not currently have permission to perform this action — this
may be because your department is not active."), never the target
User — while Deactivate's failure handling uses the plain backend
message unmodified, since that action can never return this `403`.
Verified directly: `UserDetailPage.test.jsx`'s own test submits a `403`
on Approve and asserts the department-specific phrasing appears.

### Security review (§18) — verified this phase, not merely designed

Grepped the full new/changed file set for `jwt`/`decode`/`localStorage`
— zero matches outside `services/tokenStorage.js` (untouched). Grepped
for a `DELETE` request anywhere in `adminService.js`/`userService.js`/
`departmentService.js` — the only match is
`userService.revokeAuthorization`, the one legitimate
`DELETE /users/authorizations/{id}` call the backend actually exposes;
no `DELETE` exists anywhere for Department/Admin/User account
lifecycle, matching the backend's own contract exactly (deactivation is
always a `POST`). Grepped for a `403`-to-`404` (or reverse) conversion
anywhere in the new pages — none found. `git status` confirms zero
files under `backend/app/` or `backend/alembic/` were touched.

### Tests (§21/§26 of the brief) — IMPLEMENTED

75 new tests across 14 files (up from Phase 5C's 84, total **159**):
`utils/formValidation.test.js` extended (+8, covering the three new
validators), `components/ConfirmDialog.test.jsx` (7 — dialog
accessibility, focus, Escape, backdrop click, Tab-trap),
`routes/RoleGuard.test.jsx` (5, new — both usage modes, including the
`<Outlet/>` layout-route behavior the extension added),
`pages/DepartmentListPage.test.jsx` (5), `pages/
DepartmentCreatePage.test.jsx` (5), `pages/DepartmentDetailPage.test.jsx`
(5), `pages/AdminListPage.test.jsx` (5), `pages/
AdminAuthorizePage.test.jsx` (5), `pages/AdminDetailPage.test.jsx` (8 —
including the transfer flow, the 409-race-on-approve scenario, and the
403-vs-409 department-inactive-on-transfer case), `pages/
UserListPage.test.jsx` (5), `pages/UserAuthorizePage.test.jsx` (6),
`pages/UserAuthorizationsPage.test.jsx` (6 — including the default-
`ACTIVE`-filter behavior and the used-authorization 409 race),
`pages/UserDetailPage.test.jsx` (6 — including the 403-department-
phrasing test). Run 3 consecutive times, identical results each time.

### Validation

`npm run build` succeeds (163 modules, no errors). `npm run test` —
**159 passed**, 0 failed, run 3 consecutive times. Backend regression:
`pytest tests/` — **458 passed**, unaffected, confirming zero backend
impact. `git status` confirms no file under `backend/app/`,
`backend/alembic/`, or `backend/tests/` was touched.

### Known limitations (post-implementation, restating §22's findings — none newly discovered)

* **No pagination/search/sort on Departments/Admins/Users/User-
  authorizations** — unchanged from the review; every list page renders
  the backend's complete result set for the active filter. `PENDING
  BACKEND API`; whether it's needed at real V1 volumes remains `PENDING
  BUSINESS CLARIFICATION`.
* **No department/admin/user counts anywhere** — `DepartmentResponse`
  has no such field; none is computed client-side. `PENDING BACKEND
  API`.
* **Admin-purpose authorizations cannot be revoked** — no such endpoint
  exists; `AdminAuthorizePage` has no revoke-adjacent affordance,
  matching the confirmed backend gap exactly. `PENDING BUSINESS
  CLARIFICATION`.
* **Category/Classification management UI was not built** — out of
  this phase's own objective list (§2 A-I), unchanged from the review.
