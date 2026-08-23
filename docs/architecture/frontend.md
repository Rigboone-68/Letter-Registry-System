# Frontend & Operational UI — Architecture Review & Foundation (Phase 5 / 5A / 5B / 5C)

**Status: CORE REGISTRY UI IMPLEMENTED (Phase 5C); Administration &
Account Management UI also now implemented, recorded separately in
[`administration-ui.md`](administration-ui.md) (Phase 5D).** §1-33
below are the original architecture/UX review (Phase 5) — kept
unchanged as the design rationale. **See §34, "Phase 5A implementation
record"** for the foundation built on top of it (routing, authentication
state, the API client, protected routes, role-derived navigation, the
application shell, a design-token foundation, an accessibility
baseline, and test infrastructure), **§35, "Phase 5B implementation
record"** for the complete login/signup/pending-approval/deactivated-
account/session-restoration/logout experience built on top of that
foundation, and **§36, "Phase 5C implementation record"** for the
complete Letter registry (list/search/sort/paginate/create/view/edit/
archive) built on top of both. Phase 5D's Department/Administrator/User
management UI is now also implemented — its full design and
implementation record live in `administration-ui.md` rather than as a
further section here, since that phase's own review was already a
substantial standalone document. **Documents & Notifications UI is now
also implemented** (Phase 5E — architecture/requirements review, then
implementation, both recorded in
[`document-notification-ui.md`](document-notification-ui.md), §27 has
the full implementation record) — this document's own §14/§15,
written during the original Phase 5 pass, were re-verified fresh
against current source before that implementation and confirmed still
accurate; the newer document adds the implementation-level detail
(exact routes/components/services/tests) this one never went into.
`LetterDetailPage` now has a real Documents section (upload/list/
download); `Topbar` now has a `NotificationBell`; `/app/notifications`
is a real paginated page. Dashboard and audit UI still do not exist as
real screens.

This document originally inspected the actual current frontend (a Phase
1 skeleton) and the actual current backend API surface (42 business
endpoints across 8 resource routers, verified via the live OpenAPI
schema), and designed the screens, routing, component architecture, API
integration, and UX behavior a future implementation phase would need —
expressing exactly what the backend already supports, never inventing a
business rule the backend doesn't enforce. §34 records how much of that
design is now real.

## 0. How to read this document

* **CONFIRMED** — verified directly against current frontend/backend
  code, configuration, or the live OpenAPI schema, this session.
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts and this project's established conventions. Not implemented.
* **PROVISIONAL** — a judgment call made explicitly, not extracted from
  any source of truth (a UX/design decision this document had to make
  one way or another); flagged so it's revisited deliberately, not
  mistaken for a backend-confirmed fact.
* **PENDING BUSINESS CLARIFICATION** / **PENDING BACKEND API** —
  genuinely open; not guessed into a design.

## 1. Existing frontend architecture (verified fresh)

Read directly this session: every file under `frontend/` (18 files,
excluding `node_modules/`, which does not exist —
`npm install` has never been run in this repository), `package.json`,
`vite.config.js`, `.env.example`, and every placeholder `README.md`
under `src/*/`.

**CONFIRMED — this is a pure Phase 1 skeleton, nothing beyond it
exists**: `src/App.jsx` renders a static heading and one paragraph
("Phase 1 foundation. No functionality is implemented yet."); `src/main.jsx`
mounts it with no router. Every other `src/*` directory
(`assets/components/constants/context/hooks/layouts/pages/routes/services/utils`)
contains only a one-line placeholder `README.md` describing its intended
future purpose — no `.jsx`/`.js` implementation file exists anywhere
except `App.jsx`, `main.jsx`, and `constants/app.js` (three constants:
`APP_NAME`, `APP_SHORT_NAME`, `API_BASE_URL`, all environment-driven).

**CONFIRMED — the stack is already chosen** (`package.json`):

| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | 18.3.1 | UI library |
| `vite` | 5.3.1 | Build/dev server |
| `react-router-dom` | 6.24.0 | Routing (installed, not yet wired — `App.jsx` has no `RouterProvider`) |
| `axios` | 1.7.2 | HTTP client (installed, no instance/service module exists yet) |

**No state-management library, no CSS/UI framework, no test framework**
is installed or configured — confirmed by the complete absence of any
such entry in `package.json`. `vite.config.js` proxies `/api` to
`http://localhost:8000` in dev (so no absolute backend URL is ever baked
into source) and aliases `@` to `src/`. `.env.example` defines
`VITE_APP_NAME` and `VITE_API_BASE_URL=/api/v1` — matching the backend's
actual `API_V1_PREFIX`.

**RECOMMENDED**: keep this stack exactly as-is. Per this document's own
explicit instruction and this project's established "don't introduce
complexity without a demonstrated need" philosophy (root `README.md` §6),
nothing below recommends adding React Query/Redux/Zustand/a UI framework
unless a specific section identifies a concrete, current-scope reason to
— see §21/§26/§29 for where those questions actually come up, each
resolved in favor of the simplest option the existing stack already
supports.

## 2. Backend-to-frontend endpoint map (verified via the live OpenAPI schema)

Generated from `app.openapi()` directly, not reconstructed from memory —
**42 business endpoints**, excluding `GET /health` and the five
verification-only `/auth/test/*` routes (`dev_authz_test.py`, explicitly
not business functionality per `docs/architecture/authorization.md` §7 —
excluded from every screen below).

| Resource | Endpoints | Roles | Screens (§5-§17) |
|---|---|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` | any / unauthenticated | Login, Signup, session bootstrap |
| Departments | `POST`/`GET`/`PATCH /departments`, `.../{id}`, `.../{id}/activate`, `.../{id}/deactivate` | SYSTEM_ADMIN | System Admin → Departments |
| Admins | `POST /admins/authorizations`, `GET /admins`, `GET /admins/{id}`, `POST .../approve`, `.../deactivate`, `.../reactivate`, `PATCH .../department` | SYSTEM_ADMIN | System Admin → Administrators |
| Users | `POST`/`GET /users/authorizations`, `DELETE .../{id}`, `GET /users`, `GET /users/{id}`, `POST .../approve`, `.../deactivate`, `.../reactivate` | ADMIN (own department) | Admin → Users |
| Categories | `POST`/`GET`/`PATCH /categories`, `.../{id}`, `.../{id}/activate`, `.../{id}/deactivate` | SYSTEM_ADMIN | System Admin → Categories |
| Classifications | Same shape, plus `restricts_access` | SYSTEM_ADMIN | System Admin → Classifications |
| Letters | `POST /letters` (USER/ADMIN only), `GET /letters` (paginated/sortable/searchable), `GET`/`PATCH`/`DELETE /letters/{id}` | USER/ADMIN own department; SYSTEM_ADMIN read/update/archive any department, cannot create | Letters (list/create/detail/edit/archive) — all roles except create for SYSTEM_ADMIN |
| Documents | `POST`/`GET /letters/{letter_id}/documents`, `GET .../{document_id}` | Same access as the parent Letter | Nested inside Letter detail |
| Notifications | `GET /notifications`, `GET .../unread-count`, `PATCH .../{id}/read`, `PATCH .../read-all` | any authenticated role, always scoped to self | Notification bell + panel, every role |

## 3. Frontend stack — decisions this review had to make

The stack itself is CONFIRMED (§1); three genuine architecture decisions
remain, none of them "which framework":

* **Data fetching, no caching library** — RECOMMENDED: plain `async`
  functions in `src/services/*.js` (one module per backend resource,
  matching the existing `README.md`'s own stated convention — "all HTTP
  goes through `src/services/`"), called from component-level
  `useEffect`/`useState`, or a small shared `useApiResource`-style hook
  if list-screen duplication becomes a real, observed problem once
  several screens exist. **Not React Query/TanStack Query at V1** — see
  §29 for the reasoning, applied consistently with this section's own
  explicit instruction not to add it "unless the existing stack does not
  provide an adequate approach and there is a real need."
* **Auth/global state** — RECOMMENDED: a single `AuthContext` (React
  Context + a reducer or plain `useState`), not a general-purpose state
  library — see §22. Nothing else in the confirmed screen set (§5-§17)
  needs cross-tree shared state beyond "who is logged in."
* **Styling** — no framework is installed; RECOMMENDED CSS Modules plus
  a small shared token file (colors/spacing/typography) — see §26.

## 4. Authentication UX

Mapped directly against `auth.py` (read in full this session, not
assumed):

| Endpoint | Success | Failure modes (exact backend response) |
|---|---|---|
| `POST /auth/signup` | `201` `UserPublic` | `403` "This email is not authorized to sign up." (collapses never-authorized/expired/revoked/already-used, deliberately — see `SignupNotAuthorizedError`'s docstring); `409` "An account with this email already exists." |
| `POST /auth/login` | `200` `TokenResponse` (`access_token`, `token_type`, `expires_in` **in seconds**, `user: UserPublic`) | `401` "Incorrect email or password." (deliberately undifferentiated — no account enumeration); `403` "Your account is awaiting administrator approval."; `403` "Your account has been deactivated." |
| `GET /auth/me` | `200` `UserPublic` | `401` (missing/invalid/expired token, or the account is no longer `ACTIVE` — `get_current_user` re-checks status on every call) |

**RECOMMENDED screens/flows**:

* **Login** — email/password form → `POST /auth/login`. On `401`, show a
  single generic "Incorrect email or password" message (matching the
  backend's own deliberate non-enumeration). On `403`, branch on the
  exact `detail` text to show a distinct "pending approval" or
  "deactivated" message (see §23 for why this string-matching is a real,
  imperfect coupling point, not a clean contract).
* **Signup** — `full_name`/`email`/`password`/`password_confirm` →
  `POST /auth/signup`. **Never auto-login after signup** — a fresh
  account is always `PENDING_APPROVAL` (login would immediately `403`);
  RECOMMENDED a clear "signup successful — awaiting administrator
  approval" confirmation screen instead.
* **Logout** — CONFIRMED there is no server-side revocation endpoint and
  no refresh-token mechanism (`docs/architecture/authentication.md` §16,
  unchanged since Phase 3A) — "logout" is purely client-side: clear the
  stored token/user state and redirect to `/login`. The token itself
  remains cryptographically valid until its natural expiry
  (`ACCESS_TOKEN_EXPIRE_MINUTES`); this is an accepted, already-documented
  backend limitation, not something the frontend can or should paper
  over.
* **Persistence & session restore** — on app load, if a token exists in
  storage, RECOMMENDED calling `GET /auth/me` before rendering anything
  role-gated (a brief loading state) — never trust a locally cached
  `user` object for a fresh page load, since it could be stale (§13,
  §22). A `401` here clears storage and routes to `/login`; success
  populates `AuthContext`.
* **Expired/invalid token (any authenticated call, not just `/auth/me`)**
  — RECOMMENDED a centralized `axios` response interceptor (§21) that
  clears auth state and redirects to `/login` on any `401` **except**
  the login call itself (which handles its `401` locally as a form
  error, not a redirect — the user is already on the login screen).
* **Unauthorized (`403`) on an authenticated call** — distinct from the
  above: the session is valid, the caller just isn't allowed to do
  *this*. RECOMMENDED an in-page "you don't have permission" state, not
  a redirect to login (§23).

**CONFIRMED constraint the frontend must respect**: the backend never
assigns role/department, approves accounts, or determines authorization
— every one of those facts is read from `UserPublic`/service responses,
never computed or cached client-side as a source of truth (§22).

## 5. Role hierarchy UX

Three roles (`UserRole`: `SYSTEM_ADMIN`/`ADMIN`/`USER`), each mapped
against §2's endpoint table, not assumed from the task's own suggested
structure — one real gap in that suggestion is corrected below (§6).

**RECOMMENDED principle, stated once, applying to every role section
below**: navigation is convenience, not security. A `RoleGuard`
component (§20) hides/shows nav items and redirects away from screens a
role structurally cannot use — this reduces confusing dead-end UI, it
does not and cannot substitute for the backend's own checks
(`assert_department_access`/`assert_letter_access`/`require_*` role
dependencies), which run on every request regardless of what the
frontend rendered.

## 6. System Admin UI

Mapped against §2: Departments, Admins, Categories, Classifications
(all full CRUD + activate/deactivate, all SYSTEM_ADMIN-only) map exactly
to the task's own suggested structure. **One capability the suggested
structure omits, confirmed real**: `SYSTEM_ADMIN` has full cross-department
read/update/archive access to **Letters and Documents** — it bypasses
`assert_department_access` entirely (`docs/architecture/authorization.md`
§2) and is the one role for which `GET /letters`'s `department_id` query
parameter is actually meaningful (SYSTEM_ADMIN-only; silently ignored for
USER/ADMIN — §13). It cannot **create** a letter (`POST /letters` is
`require_user_or_admin`, structurally excluding SYSTEM_ADMIN, which has
no department to record one against). **RECOMMENDED**: add a Letters
screen to the System Admin area (read/search/update/archive across all
departments, with a department filter) — not inventing new backend
capability, correcting an incomplete suggested nav structure against
what the backend actually grants this role.

```
System Administration
├── Departments
├── Administrators
├── Categories
├── Classifications
├── Letters            (read/search/update/archive, cross-department — RECOMMENDED addition)
└── System Activity    (PENDING BACKEND API — see §16)
```

Notifications: `GET /notifications` has no role restriction, so a
SYSTEM_ADMIN *can* open the notification panel — **CONFIRMED it will
always be empty** under the current recipient strategy (§13/§14 of
`docs/architecture/audit-notifications.md` — only the recipient
department's Admins ever receive one). Include the bell for
consistency; document plainly that it's structurally quiet for this
role today, not a bug.

## 7. Admin UI

Matches the task's own suggested structure exactly, verified against
§2: `Dashboard`, `Letters` (full CRUD in own department, via the same
non-narrowed access `assert_letter_access` gives ADMIN), `Users`
(`/users*`, own department), `Notifications` (the CONFIRMED real
recipient of the one implemented trigger), `Profile` (`/auth/me`).
Document operations are **not** a separate top-level nav item — they
live nested inside Letter detail, matching the backend's own URL nesting
(`/letters/{id}/documents*`, §14). **Confirmed absent for this role**:
Department/Category/Classification/other-Admin management — every one
of those endpoints is `require_system_admin`-gated; an Admin has no path
to them regardless of frontend routing.

## 8. User UI

`Dashboard`, `Letters` (full CRUD in own department, narrowed by the
classified-access boundary for letters this USER didn't record —
§11/§12), `Notifications`, `Profile` — matches the task's suggestion.
**Confirmed absent**: any User-management screen (that's Admin-only).
**Confirmed, and worth stating plainly rather than silently building a
misleading UI**: under the current recipient strategy, a plain `USER`
is **never** a notification recipient (§6) — the Notifications screen
exists because the API imposes no role restriction, but a USER's list
will be empty today. This is accurate to current backend behavior, not
a frontend defect, and would change automatically if the PROVISIONAL
recipient strategy is ever revised.

## 9. Letter registry UX

Mapped against `letters.py`/`letter_service.py` (re-read in full this
session): create, list/search (paginated, sorted, filtered), get, update,
archive — no physical delete anywhere. **RECOMMENDED screens**: a list/
search page (table + filter panel, §11), a create form (§10), an edit
form (same field set, all optional), a detail page (full `LetterResponse`,
including nested documents §14), an archive action (confirmation dialog,
§17) reachable from list and detail. **Empty/loading/error states**:
standard `EmptyState`/`LoadingState`/`ErrorState` components (§20) reused
across every list/detail screen in this document, not one-off per
screen.

## 10. Letter form — the actual schema, not the task's illustrative list

Read `app/schemas/letter.py` fresh this session — the authoritative
field set:

| Field | Required at create? | Editable via update? | Notes |
|---|---|---|---|
| `reference_number` | Yes | Yes | No format imposed; **no uniqueness enforced or implied — do not build an "is this available" check** (§2.3 of `docs/architecture/letter-registry.md`, unchanged since the Phase 4B hardening pass) |
| `subject` | Yes | Yes | |
| `source_name` | Yes | Yes | The letter's origin (free text) |
| `source_department_id` | No | Yes | Optional FK — only when the source happens to be an LRS-registered department |
| `source_location` | No | Yes | |
| `sender_name` | Yes | Yes | |
| `sender_designation` | Yes | Yes | |
| `sender_department` | Yes | Yes | **Distinct from `source_department_id`** — free text describing the sender's own department, not a cross-reference; the form's labels/help text should make this distinction legible, since the two fields can describe the same real-world department without being the same value (an existing, acknowledged overlap — `app/models/letter.py`'s own docstring — not something the frontend should try to reconcile) |
| `sender_address` | No | Yes | Deliberately optional — "the physical letter may not provide one" |
| `reason` | No | Yes | Present on the schema; not in the task's own "known fields" list, included here because §10 asks for the *actual* schema |
| `category_id` | No | Yes | Optional FK, must reference an `ACTIVE` Category |
| `classification_id` | No | Yes | Optional FK, must reference an `ACTIVE` Classification; see §12 |
| `received_at` | Yes | Yes | Datetime |
| `text_content` | No | Yes | The letter's typed/transcribed content — distinct from an uploaded document (§14); not a generic "content" field despite the task's loose phrasing |

**Server-derived, never a form field, on neither create nor update**:
`id`, `recipient_department_id` (derived from the recorder's own
department — **there is no "choose recipient department" control
anywhere**), `recorded_by`, `status`, `created_at`, `updated_at`.

**CONFIRMED validation** (nothing invented beyond this): every required
string field is rejected if blank/whitespace-only
(`_require_non_blank`); no other format constraint exists on any field.
An update with every field `None` changes nothing (the "leave unchanged"
convention) — a nullable field already set (e.g. `sender_address`)
**cannot currently be cleared back to `null`** through the update
endpoint, a known, already-documented backend limitation
(`docs/architecture/letter-registry.md`) the form should not attempt to
paper over with client-side tricks.

## 11. Letter search UX

CONFIRMED backend capability (`letters.py`/`letter_repository.py`,
re-verified this session): seven independent case-insensitive
"contains" text filters (`reference_number`, `subject`, `sender_name`,
`sender_designation`, `sender_department`, `source_name`,
`source_location` — each its own query parameter, **not** one shared
box), three exact filters (`category_id`, `classification_id`, `status`)
plus `department_id` (SYSTEM_ADMIN-only, §6/§13), inclusive
`received_from`/`received_to`, whitelisted `sort_by`
(`received_at`/`created_at`/`reference_number`/`subject`) + `sort_order`,
and `page`/`page_size` (bounded, `MAX_PAGE_SIZE=100`).

**No single global "search=" box exists in the backend** — confirmed
absent, and `docs/PROJECT_STATUS.md`'s own Pending list already tracks
this as an open question. Per this task's explicit instruction: **a
unified global search is marked PENDING BACKEND API**, not built by
concatenating client-side logic over the seven per-field filters (which
would silently invent search semantics the backend doesn't implement,
e.g. matching *any* field vs. *all* fields is genuinely ambiguous and
not this document's call to make).

**RECOMMENDED V1 search UI**: an "advanced filters" panel exposing the
seven text filters, three exact filters, and the date range, each
independently clearable; active filters shown as removable chips; a
sort selector (the four whitelisted fields only — never a raw client
string, mirroring the backend's own whitelist discipline); standard
pagination controls. This is a direct, literal mapping of confirmed
capability — no invented semantics.

## 12. Classified Letter UX — CRITICAL

**CONFIRMED backend design** (`docs/architecture/letter-registry.md` §8,
`docs/architecture/registry-search.md` §8, re-verified this session):
`LetterNotFoundError` collapses "doesn't exist," "wrong department," and
"classified and inaccessible" into one identical `404` for single-resource
access; `letter_visibility_filter` excludes inaccessible classified
letters from **both** `items` and `total` at the query level for list/
search — the frontend receives an already-correct, already-filtered
result set and an already-correct count on every page.

**RECOMMENDED, the single governing rule for this section**: the
frontend must **never** perform its own classified-access filtering,
labeling, or existence-inference of any kind — it renders exactly what
the API returns, trusts `total`/`items` completely, and treats every
`404` on a letter or document identically, with no distinguishing
language ("this letter is restricted," "you don't have clearance," etc.)
that would itself leak existence. This is the same "backend authoritative"
discipline every prior phase of this project has enforced, applied here
to the one UI surface where getting it wrong would silently reintroduce
the exact leakage risk Phase 4C's own review found and fixed at the
query level.

* **List/search** — render `items`/`total` as returned; no client-side
  post-filter.
* **Detail** — a `404` response renders the same generic "Letter not
  found" as a genuinely nonexistent id; never a distinguishable state.
* **Pagination** — page-count math already reflects only accessible
  rows; no adjustment needed.

## 13. Department isolation UX

* **Department filter** — CONFIRMED `department_id` is silently ignored
  for USER/ADMIN (always scoped server-side to their own department);
  RECOMMENDED the frontend not show a department selector for those
  roles at all (there's nothing for it to do), and show one only for
  SYSTEM_ADMIN, defaulting to "all departments."
* **Backend ignores unauthorized department filters** — confirms no
  defensive frontend logic is needed beyond simply not exposing the
  control for USER/ADMIN.
* **The caller's own department becomes `INACTIVE`** — CONFIRMED
  `LetterService` applies `assert_department_access` uniformly for
  *every* Letter operation, including plain reads within one's own
  department (unlike `UserService`'s three-tier read/lock-down/
  state-elevating split) — an affected User/Admin would get `403` on
  essentially every Letter action. **A real, honestly-surfaced gap**:
  `UserPublic` exposes `department_id` but not that department's own
  `status` — **the frontend has no way to know proactively** that its
  own department just went inactive; it can only infer this reactively,
  after a `403`. RECOMMENDED a generic "you don't currently have
  permission to perform this action — contact your administrator"
  message on such a `403` (§23), not a specific "your department is
  inactive" claim the frontend cannot actually confirm without a backend
  change this review is not proposing.
* **A User is deactivated** — cannot authenticate at all
  (`get_current_user` blocks at the dependency layer); manifests as a
  `401` on their next call, handled by the standard session-expired flow
  (§4). A subsequent login attempt would surface the distinct "your
  account has been deactivated" message.
* **An Admin's department changes** — CONFIRMED `get_current_user`
  re-loads the `User` row fresh from the database on every request, and
  every authorization check operates on that live object, **not** a
  claim baked into the JWT at login time — a department transfer takes
  effect on the Admin's very next API call, with no new login required.
  The only staleness risk is **cosmetic**: a locally cached `user` object
  in `AuthContext` would still show the old `department_id` until
  re-fetched. RECOMMENDED re-fetching `/auth/me` at reasonable
  boundaries (app load, recovering from a `401`, optionally on
  navigating into a department-scoped screen) to keep chrome (e.g. a
  "Department: X" label) accurate — explicitly a display concern, not a
  security one, since the backend's own authorization is correct
  regardless of what the frontend has cached.

## 14. Document management UX

Mapped against `documents.py`/`document_service.py`
(re-verified this session): upload (`POST`), list (`GET`, metadata
only — no `storage_path` field exists on `DocumentResponse` to expose),
download (`GET .../{document_id}`, streamed binary with
server-validated `Content-Type` and a sanitized `Content-Disposition`
filename).

* **Upload** — a file input plus client-side extension/size pre-checks
  as a **UX nicety only** — RECOMMENDED, never authoritative; the
  backend re-validates extension, an authoritative magic-byte content
  signature, and size independently (`docs/architecture/document-management.md`
  §8), and will reject a file the frontend's own pre-check let through
  if it doesn't actually match. Progress: `axios`'s `onUploadProgress`
  callback, RECOMMENDED for files approaching the (architectural,
  10 MB) size limit.
* **Validation errors** — map the backend's `422` (unsupported/
  mismatched type) and `413` (too large) responses to specific,
  distinguishable messages, not a generic upload failure.
* **Download/open** — **CONFIRMED, and a real technical constraint**:
  this endpoint requires a Bearer token like every other authenticated
  route; a plain `<a href="...">` cannot carry it (browsers don't attach
  custom `Authorization` headers to a normal navigation/anchor click).
  RECOMMENDED: fetch via the authenticated `axios` instance, then create
  an object URL (`URL.createObjectURL`) for either inline preview or a
  programmatic download trigger. **PENDING/FUTURE**: this means "open in
  a new tab with a shareable/bookmarkable URL" isn't directly available
  without either buffering the whole file client-side first or a future
  backend addition (a short-lived signed URL) this review is not
  proposing — flagged as a real, accepted V1 limitation, not silently
  worked around.
* **File-size/type display** — from `DocumentResponse.file_size`/
  `mime_type` directly (human-formatted client-side, e.g. "2.4 MB").
* **No delete UI, of any kind** — CONFIRMED no such endpoint exists
  (`docs/architecture/document-management.md` §14). **Replacement = a
  second upload** — the old document remains, exactly matching backend
  behavior; the UI should present "upload another" rather than implying
  an old one is replaced/removed.
* **Empty state, upload failure, retry** — standard `EmptyState`/error
  messaging (§20); a failed upload is simply retryable by re-submitting
  the form, no special backend retry semantics exist or are needed.

## 15. Notifications UX

Mapped against `notifications.py` (re-verified this session): list
(paginated, newest-first), unread count, mark-one-read (idempotent),
mark-all-read — every route scoped unconditionally to `current_user`,
confirmed by direct code read, not just the doc record.

**RECOMMENDED**: a bell icon with an unread-count badge, polling
`GET /notifications/unread-count` only (never the full list) at a modest
interval (§29); a panel/page listing `GET /notifications` results with
mark-read/mark-all-read actions. **No recipient-selection UI of any
kind** — there is no backend capability for a user to choose or view
another user's notifications (`recipient_user_id` isn't a field a client
can set anywhere — confirmed absent from every notification schema and
endpoint), so there is nothing for such a control to do.

## 16. Audit UI — PENDING BACKEND API

**CONFIRMED, re-verified this session**: no audit-viewing endpoint
exists anywhere in `app/api/v1/endpoints/` — `AuditLog` is written to
(Phase 4E) but nothing exposes it. Per explicit instruction: **no
"System Activity" page is designed against an endpoint that doesn't
exist.** The System Admin nav (§6) reserves a labeled, disabled/
placeholder slot for it, explicitly marked **PENDING BACKEND API** — a
future audit-read endpoint (whenever built, at whatever access scope
`docs/architecture/audit-notifications.md` §9 eventually resolves) is
the only thing that could make this a real screen; nothing here designs
its content in advance of that endpoint existing.

## 17. Administration UX

Every workflow below is a direct, verified mapping to §2's endpoint
table — nothing added, nothing assumed:

* **Department**: create, list, update, activate, deactivate.
* **Admin**: authorize (issues a `UserAuthorization`), signup (reuses
  the same `/auth/signup` flow — no separate Admin signup endpoint
  exists), approve, deactivate, reactivate, department transfer.
* **User**: authorize, list, get, approve, deactivate, reactivate,
  revoke authorization (`DELETE /users/authorizations/{id}` — the one
  authorization-revocation path that exists; **no equivalent exists for
  ADMIN-purpose authorizations**, a pre-existing, documented backend gap
  this review does not paper over with a UI control that would call a
  nonexistent endpoint).

**RECOMMENDED**: a `ConfirmDialog` (§20) before every deactivate,
archive, and revoke action — all genuinely state-changing and, for
deactivate/revoke, not casually reversible from the caller's own screen
(reactivation is a separate, deliberate action). **No physical deletion
exists anywhere in the confirmed backend** (append-only/soft-delete
throughout every entity) — the UI must never use "delete" language for
any of these actions; "archive"/"deactivate"/"revoke" only, matching the
backend's own vocabulary exactly.

## 18. Account lifecycle UX — three distinct enums, not one

The task's own suggested label set ("AUTHORIZED, PENDING_APPROVAL,
ACTIVE, INACTIVE/DEACTIVATED, REVOKED") blends three genuinely separate
backend enums (`app/models/enums.py`, re-read this session) — worth
correcting precisely rather than adopting loosely:

| Enum | Values | Applies to |
|---|---|---|
| `AuthorizationStatus` | `ACTIVE`, `USED`, `REVOKED` | `UserAuthorization` — the "AUTHORIZED, not yet signed up" state is `AuthorizationStatus.ACTIVE`, not a `User` state at all |
| `UserStatus` | `PENDING_APPROVAL`, `ACTIVE`, `DEACTIVATED` | `User` (both USER and ADMIN roles) — the value is `DEACTIVATED`, not `INACTIVE` |
| `ActiveStatus` | `ACTIVE`, `INACTIVE` | `Department`/`Category`/`Classification` — a *different* enum that happens to use `INACTIVE`, never applied to a `User` |

**RECOMMENDED**: a single flexible `StatusBadge` component (§20)
parameterized by which enum + value it's rendering, so the label/color
mapping for each of these three enums stays centralized and cannot drift
into showing, say, a Department's `INACTIVE` styling on a
`DEACTIVATED` User by accident. **RECOMMENDED copy, never exposing
internal mechanics**: "Pending approval," "Active," "Deactivated,"
"Authorization revoked," "Department inactive" — plain language, never
the raw enum token, and never implying *why* in more detail than the
backend's own error messages already provide (§4/§13).

## 19. Route architecture

**RECOMMENDED, not extracted from any existing code** — the current
frontend has zero routes (§1), so this is this document's own proposal,
derived from §2's endpoint map and corrected for §6's finding, not a
blind copy of the task's own illustrative tree:

```
/login
/signup

/app                                (authenticated shell)
/app/letters
/app/letters/new                    (USER/ADMIN only)
/app/letters/:id
/app/letters/:id/edit
/app/notifications
/app/profile

/app/admin/users                    (ADMIN only)
/app/admin/users/:id

/app/system/departments             (SYSTEM_ADMIN only)
/app/system/admins
/app/system/admins/:id
/app/system/categories
/app/system/classifications
/app/system/letters                 (SYSTEM_ADMIN only — §6's addition)
/app/system/letters/:id
/app/system/activity                (disabled placeholder — §16, PENDING BACKEND API)
```

Documents have **no standalone route** — always reached via
`/app/letters/:id` (matching the backend's own nested URL design,
`/letters/{letter_id}/documents*`, and reinforcing §12's "never treat a
document as independently addressable" discipline at the routing layer
too).

## 20. Component architecture

**RECOMMENDED, evaluated against genuine duplication across the screens
in §5-§17, not proposed speculatively**:

| Component | Reused by |
|---|---|
| `AppShell`, `Sidebar`, `Topbar` | Every authenticated screen |
| `NotificationBell` | Topbar, every role (§15) |
| `ProtectedRoute` | Every `/app/*` route (redirect to `/login` if unauthenticated) |
| `RoleGuard` | Role-restricted routes (§5) — convenience only |
| `DataTable` | Letters, Documents, Users, Admins, Departments, Categories, Classifications, Notifications — **note**: only Letters and Notifications are server-paginated (`page`/`page_size` in the response); Departments/Categories/Classifications/Admins/Users return a bare `{items, total}` with no pagination at all (confirmed absent from every one of those response schemas) — `DataTable` needs a mode that doesn't assume pagination exists |
| `Pagination` | Letters, Notifications only (per the note above) |
| `SearchFilters` | Letters (§11) |
| `LetterForm` | Create + edit (§10) |
| `LetterDetail` | Letter detail, embeds `DocumentList` |
| `DocumentList`, `DocumentUpload` | Letter detail (§14) |
| `StatusBadge` | Every entity with a lifecycle status (§18) — one component, parameterized, not one per enum |
| `ConfirmDialog` | Every deactivate/archive/revoke action (§17) |
| `EmptyState`, `ErrorState`, `LoadingState` | Every list/detail screen |

**Explicitly not recommended**: anything beyond this list at V1 — no
generic form-builder abstraction, no headless-UI kit, no component
library wrapper layer. Matches this section's own "avoid
overengineering" instruction.

## 21. API client architecture

**RECOMMENDED**: one `axios` instance (`baseURL` from
`VITE_API_BASE_URL`), a request interceptor attaching
`Authorization: Bearer <token>` from `AuthContext`, and a response
interceptor normalizing errors centrally rather than per call site.

**A real, precise technical detail worth stating explicitly**: this
backend returns **two different error body shapes** depending on the
failure's origin — a raised `HTTPException` (used for every business-rule
rejection throughout every service in this codebase) returns
`{"detail": "<plain string>"}`; a Pydantic/FastAPI request-validation
failure (`422`, e.g. a missing required field or a bad type) returns
FastAPI's own `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`
array shape. **The frontend's error-normalization layer must handle
both** — treating every `422` as if it always carries a plain string (or
vice versa) will break on whichever shape wasn't tested.

**Status-code handling** (§23 has the full table): `401` → distinguish
"failing login itself" (local form error) from "any other authenticated
call" (clear session, redirect); `403` → in-page permission-denied,
never a redirect; `404` → generic "not found," never elaborated (§12);
`409` → surface the conflict message as-is (e.g. duplicate department
name); `422` → field-level validation display, handling both shapes
above; `500`/network failure → generic "something went wrong, try again"
with no internal detail exposed.

## 22. Auth state

**RECOMMENDED**: `AuthContext` holding `{ token, user, status }` where
`status` is `'loading' | 'authenticated' | 'unauthenticated'`. `user`
(role/department_id/status) is **always** the `UserPublic` object most
recently returned by `/auth/login` or `/auth/me` — **never** decoded
from the JWT payload client-side, even though the token technically
carries `role`/`department_id` claims (`create_access_token`). Those
claims exist, per `docs/architecture/authorization.md`, "for a future
fast-path/cache use, not as a trust source" on the backend's own side
either — every backend authorization check re-derives from the live
database row, and the frontend should mirror that discipline rather than
trust a claim that could be stale (department transfers — §13) or
tampered with client-side (role — harmless to the backend, §28, but
capable of showing a misleading UI if trusted).

## 23. Error handling

Consolidated status-code table, all CONFIRMED backend behaviors, not
invented frontend policy:

| Status | Meaning in this backend | Frontend treatment |
|---|---|---|
| `401` | No/invalid/expired token, or account no longer `ACTIVE` (checked live, every call) | Login: local form error. Elsewhere: clear session, redirect to `/login` |
| `403` | Role-gated endpoint, or a caller's own department is inactive (§13), or (login only) account pending/deactivated | In-page "not permitted" — **never** a redirect, the session is valid |
| `404` | **CRITICAL**: "genuinely doesn't exist" and "exists but you can't access it" are deliberately identical for Letters/Documents/Notifications (enumeration resistance — §12) | Generic "not found," always, with zero distinguishing detail |
| `409` | A real conflict (duplicate department/category/classification name, an already-used authorization, etc.) | Surface the specific message — these are informative, not security-sensitive |
| `422` | Pydantic validation failure (array-shaped `detail`) or a business-rule rejection expressed as 422 (e.g. `received_from` after `received_to` — plain-string `detail`) | Field-level display where `loc` maps to a known form field; a banner otherwise |
| `500` / network failure | Unhandled server error or connectivity loss | Generic retry-oriented message, no internal detail |

**The one rule this whole table exists to protect**: `403 ≠ 404`. A
`403` implies the resource/feature exists and this caller isn't allowed
to use it; a `404` on a Letter/Document must never be distinguished from
"this exists but is classified" — collapsing that distinction is exactly
what the backend's own design already does, and the frontend must not
reintroduce it by treating the two status codes as interchangeable "access
denied" states.

## 24. Responsive design

**RECOMMENDED (PROVISIONAL — a design judgment, not extracted from any
source)**: desktop-first, matching this section's own instruction to
prioritize data tables/forms/search/administrative workflows over mobile
optimization. A sidebar that collapses to a hamburger/drawer below a
~1024px breakpoint; tables that either scroll horizontally within their
own container (never the page — an established convention already used
for wide content in this project's documentation artifacts) or reflow to
a card-per-row layout below a tablet-width breakpoint; forms remain
single-column at all widths (Letter forms have enough fields that a
multi-column layout adds little at any size). No dedicated mobile
navigation paradigm (bottom tab bar, etc.) is recommended — this is an
operational tool, not a consumer app.

## 25. Accessibility

**RECOMMENDED V1 baseline, woven into component design (§20), not a
separate initiative**: full keyboard navigation (tab order, no
mouse-only interactions anywhere, especially `DataTable` row actions and
`ConfirmDialog`); every form control has an associated, visible label
(never placeholder-as-label); visible focus states on every interactive
element; semantic HTML (`<button>` for actions, not a styled `<div>`);
`ConfirmDialog` traps focus, closes on `Escape`, and sets `aria-modal`;
form validation errors are associated with their field
(`aria-describedby`) and announced, not conveyed by color/position
alone — relevant specifically to `StatusBadge` (§18), which must pair
color with text/an icon, never color alone, since status is exactly the
kind of information that must survive being read by a screen reader or
by someone with color-vision deficiency; sufficient contrast on every
status color pairing. **Not recommended**: a dedicated accessibility
testing framework or WCAG audit tooling as a separate workstream —
matches this section's own explicit caution against turning this into a
parallel framework.

## 26. Design system

No CSS framework or UI library is installed (§1). **RECOMMENDED**: CSS
Modules (native to Vite, zero new dependency) plus a small shared token
file — a handful of CSS custom properties for color (including one
consistent set of status colors feeding `StatusBadge`, §18), spacing
scale, and typography (one font stack, 3-4 sizes) — rather than a global
stylesheet that grows unbounded or a component-scoped-only approach with
no shared vocabulary. **Explicitly not recommended without further
justification**: Tailwind, MUI, Chakra, or any comparable framework —
none is currently installed, and this section's own instruction cautions
against adding one without cause; nothing in the confirmed screen set
(§5-§17) demonstrates a need heavy enough to justify the dependency and
learning-curve cost over a small, hand-rolled token system for an
internal operational tool of this scope.

## 27. Dashboard assessment (not implemented, evaluated only)

What's derivable from **already-confirmed endpoints, no new backend
work**:

* **Letters registered (count)** — `GET /letters?page_size=1`, read
  `total`. Works today, zero new backend needed.
* **Recent letters** — `GET /letters?sort_by=received_at&sort_order=desc&page_size=N`.
  Works today.
* **Unread notifications** — `GET /notifications/unread-count`. Works
  today, but only meaningful for `ADMIN` under the current recipient
  strategy (§8/§15).
* **Department activity** (own department's letter volume) — same
  technique as "Letters registered," already scoped to the caller for
  USER/ADMIN. If "activity" is meant more richly (a timeline of *who did
  what*), that's audit-derived and **PENDING BACKEND API** (§16) — not
  available today at any cost.
* **Status breakdown** (e.g. ACTIVE vs. ARCHIVED, or by Category) — technically
  possible today via one `GET /letters?status=X&page_size=1` call per
  bucket, reading `total` each time — **a real, worth-naming
  inefficiency**: no aggregate/count-by-group endpoint exists, so an
  N-bucket breakdown costs N round trips. **RECOMMENDED**: acceptable at
  V1 scale for a small, fixed bucket count (e.g. two Letter statuses);
  **PENDING/OPTIONAL FUTURE**: a dedicated stats/aggregate endpoint if a
  richer breakdown is ever wanted, not something to build via many
  small requests without confirming the need first.

## 28. Frontend security review

* **Token storage** — **PROVISIONAL**: `localStorage`, RECOMMENDED as
  the pragmatic default (this stack has no other option without a
  backend change — the API issues a bearer token in a JSON body, not a
  cookie, and `HTTPBearer` expects an explicit `Authorization` header,
  confirmed via `app/api/deps.py`). This carries a real, accepted
  XSS-exposure trade-off common to every bearer-token-over-`localStorage`
  design; `sessionStorage`/in-memory-only don't meaningfully change that
  specific threat (any script running on the page can already reach
  application memory), they trade it for a *different* property — the
  token not surviving a closed tab/browser restart, which matters more
  on a shared/kiosk workstation than an individually-assigned one.
  **PENDING BUSINESS CLARIFICATION**: which deployment model applies —
  not something this review can answer.
* **XSS** — React's default JSX escaping covers the common case;
  RECOMMENDED: never use `dangerouslySetInnerHTML` with any
  backend-sourced free text (Letter `subject`/sender fields, notification
  `message` — all ultimately User-influenced input) even though nothing
  in the confirmed screen set currently needs it.
* **Route guards** — convenience only, restated per §5; provide no
  actual security boundary.
* **API authorization** — 100% backend; the frontend computes nothing
  beyond "should I show this button," consistent with every prior phase
  of this project.
* **Role/department spoofing** — a tampered local `user.role`/
  `department_id` is caught the moment any API call runs (the backend
  never trusts client-supplied identity beyond the signed JWT's
  authenticated subject) — the worst outcome is momentarily misleading
  UI, never real access. RECOMMENDED re-validating via `/auth/me` at
  the boundaries named in §13/§22 to shrink that window.
* **IDOR** — already prevented at the API layer by the enumeration-resistant
  `404` design (§12/§23); the frontend's only job is not undermining it
  by rendering a more specific message than the backend gave.
* **Classified Letter / notification leakage** — covered in full in
  §12/§15; the frontend renders exactly what it receives, nothing more.
* **Document URL exposure** — **CRITICAL, already addressed in §14**:
  the download endpoint requires the same bearer auth as everything
  else; there is no plain, unauthenticated, guessable, or static URL to
  a document anywhere in this backend (confirmed — no `StaticFiles`
  mount exists, `docs/architecture/document-management.md` §20), so
  there is nothing for the frontend to accidentally expose beyond what
  an authenticated `fetch`/`axios` call already requires.

## 29. Performance

* **Pagination** — use exactly what the backend provides (Letters,
  Notifications); never fetch "all" and paginate client-side.
* **Unnecessary requests** — avoid re-fetching `/auth/me` on every
  navigation; re-validate only at the boundaries named in §4/§13/§22.
* **Notification polling** — **PROVISIONAL** (no backend guidance
  exists): a modest interval (e.g. 30-60s) against the lightweight
  unread-count endpoint only, never the full list; the full list is
  fetched on-demand when the panel opens.
* **Caching library** — **RECOMMENDED: none at V1.** This section's own
  instruction is explicit — React Query/TanStack Query only if the
  existing stack (plain `axios` + component state, §3) proves inadequate
  against a *real*, observed problem (e.g. duplicate fetches on
  back-and-forth navigation), not adopted preemptively.
* **Large tables** — bounded by the backend's own `MAX_PAGE_SIZE=100`
  for Letters/Notifications; Departments/Categories/Classifications/
  Admins/Users have no server pagination at all (§20) — acceptable at
  this project's current/expected data volumes (an existing,
  already-documented backend limitation, not a new frontend problem to
  solve).
* **Document downloads** — the existing 10 MB architectural cap
  (`docs/architecture/document-management.md` §9) makes full
  client-side buffering before creating an object URL (§14) acceptable;
  no streaming-download UI is needed at this scale.

## 30. Test strategy (design only, not implemented)

**Not currently possible without additions**: no test framework is
configured in `package.json` (§1) — naming what's needed is part of
designing the strategy, not scope creep; nothing below is installed or
configured during this review.

* **Unit** — pure functions (formatters, client-side pre-validation
  mirroring backend rules for early UX feedback — §10/§14), reducer/
  context logic (§22). RECOMMENDED Vitest — Vite-native, no separate
  build toolchain.
* **Component** — individual components in isolation (`StatusBadge`
  renders the right label/color per enum+value, §18; `LetterForm`
  surfaces required-field errors; `ConfirmDialog` traps focus and
  responds to `Escape`, §25). RECOMMENDED React Testing Library +
  Vitest.
* **Integration** — page-level flows against a mocked API layer (e.g.
  Mock Service Worker), exercising role-based rendering (§5-§8),
  error-state handling (§23) without a real backend.
* **E2E** — a smaller, prioritized set against a real running backend +
  disposable test database, in the priority order this section itself
  names: authentication (login/pending/deactivated/logout/session-restore,
  §4), role-based navigation (§5-§8), department isolation (cross-department
  `404`s, §13), classified Letter behavior (non-recorder `USER` gets
  `404`; Admin/SYSTEM_ADMIN see it, §12), Letter CRUD (§9/§10), search
  (§11), documents (upload/list/download/validation rejection, §14),
  notifications (unread count/mark-read/isolation, §15), administration
  (lifecycle actions with confirmations, §17). **PROVISIONAL** tool
  choice: Playwright (more actively maintained as of this stack's era;
  Cypress is an equally defensible alternative — not a decision this
  review needs to force).

## 31. Pending business clarifications / backend dependencies (consolidated)

1. **A unified global search box** (§11) — the backend has no such
   semantics today; PENDING BACKEND API.
2. **An audit-viewing screen** (§16/§19) — PENDING BACKEND API; the
   nav slot is reserved, not built.
3. **Deployment model for token-storage risk** (§28) — individually-assigned
   workstations vs. shared/kiosk machines changes the
   `localStorage`-vs-`sessionStorage` calculus; PENDING BUSINESS
   CLARIFICATION.
4. **A short-lived signed document-download URL** (§14/§28) — would
   enable "open in a new tab" without client-side buffering; not
   proposed as a change here, PENDING/FUTURE if ever needed.
5. **A dedicated stats/aggregate endpoint** (§27) — would make a richer
   dashboard breakdown efficient; not proposed here, PENDING/FUTURE.
6. Every PENDING item already carried by the backend's own architecture
   docs still applies unchanged to whatever UI eventually surfaces it:
   the exact classification value list and classified-visibility matrix
   (`docs/architecture/letter-registry.md` §12), notification recipient
   strategy (`docs/architecture/audit-notifications.md` §13), audit
   access control (`docs/architecture/audit-notifications.md` §9).

## 32. Recommended Phase 5 (implementation) plan — not started

Sequenced so authentication and the shared chrome exist before any
feature screen needs them:

1. Wire `react-router-dom` (already installed) into `App.jsx`; build
   `AuthContext` (§22), the `axios` instance with interceptors (§21),
   and `ProtectedRoute`/`RoleGuard` (§20).
2. Login/Signup/session-restore (§4) — the only screens reachable before
   authentication exists.
3. `AppShell`/`Sidebar`/`Topbar`/`StatusBadge`/`ConfirmDialog`/
   `EmptyState`/`ErrorState`/`LoadingState` (§20) — shared primitives
   every feature screen depends on.
4. Letters: list/search (§9/§11) → detail (§9/§12) → create/edit form
   (§10) → archive action (§17) — the highest-value, most-used surface.
5. Documents, nested into Letter detail (§14).
6. Notifications: bell + panel (§15).
7. Administration: Users (Admin), then Departments/Admins/Categories/
   Classifications (System Admin) (§6/§7/§17).
8. Test scaffolding (§30) — introduced alongside step 3 onward, not
   bolted on at the end.

## 33. Explicitly NOT in this phase (review pass — superseded by §34)

At the time of the review, nothing below had been built: React pages,
components, CSS, frontend API clients, a dashboard, an audit UI, new
backend endpoints, backend modifications, database changes, migrations,
WebSockets, notification delivery, external services. **§34 records what
changed** — foundation infrastructure (routing, auth state, API client,
route guards, navigation, shell, tokens, tests) is now implemented;
every feature screen, the dashboard, the audit UI, and all backend/
database work remain explicitly out of scope, unchanged.

## 34. Phase 5A implementation record

Built directly on top of §1-33's recommendations — no new architecture
decisions, only the ones already recommended, built. Every item below
is IMPLEMENTED unless marked otherwise.

### Stack — unchanged, as recommended (§3)

No dependency was replaced. `react-router-dom`/`axios` (already
installed since Phase 1) are now actually wired up. No state-management
library, no CSS/UI framework was added. Two devDependency groups were
added, both named explicitly in the review as things this phase would
need to introduce: Vitest + React Testing Library + jsdom (§30 — no test
framework existed before) and nothing else.

### Environment configuration (§3 of the implementation brief)

No new environment variable was needed — `VITE_API_BASE_URL` (already
in `.env.example` since Phase 1) is exactly what `services/apiClient.js`
uses for its `baseURL`. Documented in `frontend/README.md`'s new
"Configuration" section.

### API client (§21)

`services/apiClient.js` — one Axios instance. Request interceptor
attaches `Authorization: Bearer <token>` from `services/tokenStorage.js`
when a token exists. Response interceptor runs every error through
`services/errorNormalization.js` (§21's own two-shape finding —
plain-string `HTTPException` detail vs. Pydantic's array-shaped
validation `detail` — both handled, verified by dedicated tests) and
triggers a single registered 401 handler *unless* the failing call opted
out via `{ skipAuthRedirect: true }` — the mechanism `authService.js`'s
three functions (`login`/`signup`/`getCurrentUser`) all use, so a `401`
on the login form itself never triggers a global redirect (§4).

### Authentication state (§22)

`context/AuthContext.jsx` — `status`
(`'loading' | 'authenticated' | 'unauthenticated'`) and `user` (always
the `UserPublic` most recently returned by the backend, never decoded
from the JWT — verified: no JWT-decoding library was added, and nothing
in this codebase parses the token's payload). `login`/`logout` are the
only two mutators; nothing else sets `user`/`status` directly.

### Token handling (§6 of the implementation brief, §28 of the review)

`services/tokenStorage.js` — the one isolated module; every other file
reads/writes the token exclusively through its three functions.
`localStorage`, documented explicitly (module docstring +
`frontend/README.md`) as the V1 PROVISIONAL approach the review named,
with the exact replacement boundary stated (edit this one file). No
token is logged anywhere (grepped — zero `console.log`/`console.error`
calls reference the token or `Authorization` header in any file this
phase added) and no token appears in a URL (never passed as a query
parameter or route param anywhere in `routes/index.jsx`).

### Login / signup flow foundations (§7/§8)

`services/authService.js` exposes `login`/`signup`/`getCurrentUser` —
the functions a future, fully-polished Login/Signup page would call.
`pages/LoginPage.jsx`/`SignupPage.jsx` are minimal, functional forms (not
the final, fully-polished pages §4 of the review describes) built far
enough to prove the foundation actually works end-to-end: success,
invalid credentials, a pending account, and a deactivated account all
render the backend's own distinct message (verified against the exact
strings in `auth.py`, §4); a network failure or unexpected server error
renders `errorNormalization`'s own generic messages. Signup never
auto-logs in — a fresh account is always `PENDING_APPROVAL`, matching
§4's explicit finding. Neither form has a `role`/`department`/`status`
field — `SignupRequest`/`LoginRequest` (backend) have none either, so
there is nothing for one to bind to.

### Session restoration (§9)

`AuthContext`'s mount effect: no token → `unauthenticated` immediately
(no wasted call); a token present → `GET /auth/me` → success sets
`user`/`authenticated`, failure clears the session. `ProtectedRoute`
renders a `LoadingState` for the entire `'loading'` window — no
protected route content (or its data-fetching effects, since none exist
yet to fire prematurely) ever mounts before this resolves, avoiding the
authentication flicker the brief named explicitly.

### Logout (§10)

`AuthContext.logout()` — clears the token (`tokenStorage.clearToken`),
clears `user`, sets `status` to `'unauthenticated'`. No backend logout
endpoint was invented; none exists (unchanged since Phase 3A). Setting
`status` to `'unauthenticated'` is what actually prevents stale
authenticated UI from lingering — `ProtectedRoute` re-evaluates on every
render and redirects the instant `status` changes.

### Routing (§11) and protected routes (§12)

`routes/index.jsx` — `/`, `/login`, `/signup` public; `/app/*` behind
`ProtectedRoute`. Placeholder child routes exist only where necessary to
prove the architecture (§11's own explicit allowance), all rendering one
shared `pages/PlaceholderPage.jsx` — no feature logic in any of them.
`ProtectedRoute` performs authentication-only gating (§12's explicit
instruction not to fold role authorization into it); `RoleGuard` is the
separate component that does role-based redirection, used only on the
System-Admin- and Admin-only placeholder routes.

### Role-aware navigation (§13)

`navigation/navigationConfig.js` — a plain, frozen data structure, no
component logic. Matches the implementation brief's three role lists
exactly, including "Documents" as a nav entry for every role even though
the review's own recommended design (§14) gives it no standalone route —
resolved by pointing every role's "Documents" entry at a placeholder
that states this explicitly, rather than silently dropping the entry or
silently building a page the review didn't recommend. No department id
appears anywhere in the file (verified by a dedicated test). Navigation
visibility is documented, in the module's own header comment and in
`RoleGuard`'s, as providing zero security.

### Application shell (§14)

`layouts/AppShell.jsx` (`Sidebar` + `Topbar` + `<Outlet/>`) — current
user's display name, a role indicator, and a logout control in the
Topbar; role-derived nav in the Sidebar. No dashboard widget of any kind
— `AppShell` renders only chrome, `<Outlet/>` is where every future
feature screen mounts.

### Error normalization and HTTP status behavior (§15/§16)

`services/errorNormalization.js` — the single function producing
`{ status, message, fieldErrors }`, handling both confirmed backend
error-body shapes (§21). `401` is handled centrally in `apiClient.js`
(§21 above); `403`/`404`/`409`/`422`/`500` are not yet centrally
*displayed* anywhere (no feature screen exists to display them in), but
the normalized shape already carries everything a future screen would
need, including the `404`-is-never-distinguished-from-"classified"
discipline (§12/§16 of the review) — nothing in this phase's code path
adds a distinguishing message for a `404`, since nothing renders one yet.

### Loading / error / empty state primitives (§17)

`components/LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx` — each
genuinely minimal (a handful of lines), each already used by at least
one real screen this phase built (`LoadingState` by `ProtectedRoute`/
`RootRedirect`; `ErrorState` by `LoginPage`/`SignupPage`), not built
speculatively for screens that don't exist yet.

### Design tokens (§18/§26) and accessibility foundation (§19/§25)

`styles/tokens.css` — color/spacing/typography/radius/shadow/breakpoint
custom properties, `styles/global.css` — a minimal reset plus a visible
`:focus-visible` style. No UI framework was added. Every interactive
element built this phase is a real `<button>`/`<input>`/`<a>` (via
`NavLink`) with an associated `<label>`; `LoadingState`/`ErrorState` use
`role="status"`/`role="alert"` respectively so assistive technology
announces them without manual `aria-live` wiring elsewhere.

### Frontend test infrastructure (§20/§30)

Established from nothing — `package.json` had no test framework before
this phase. Vitest + React Testing Library + jsdom, configured in
`vite.config.js`'s `test` block (no separate config file needed). 17
tests across the four areas the implementation brief named as the
minimum: `services/errorNormalization.test.js` (4 — both error shapes,
network failure, unexpected shape), `navigation/navigationConfig.test.js`
(5 — each role's exact nav set, an unknown role, no department id
anywhere), `routes/ProtectedRoute.test.jsx` (3 — all three auth states),
`context/AuthContext.test.jsx` (5 — no-token start, valid-token restore,
invalid-token clear, login transition, logout transition). No E2E
infrastructure was added — not genuinely necessary for this foundation
(§20's own explicit allowance to skip it), since there is no real
feature flow yet for an E2E test to exercise.

### Validation

`npm run build` succeeds (Vite production build, 113 modules, no
errors). `npm run test` — **17 passed**, 0 failed. Backend regression:
`pytest tests/` — **458 passed**, unaffected, confirming zero backend
impact. `git status` confirms only frontend files (plus five
documentation files) changed — no `backend/app/`, `backend/alembic/`,
or database file was touched.

### Known limitations (post-implementation)

* **`npm audit` reports two pre-existing advisories with no non-breaking
  fix** — `react-router-dom`'s only patched release is a `v7` major
  version, and the `esbuild`/`vite` toolchain's fix requires `vite@8` —
  both already pinned to their current major versions since Phase 1;
  upgrading either would violate this phase's own explicit "use the
  existing stack, do not replace it" instruction. Documented in
  `frontend/README.md` rather than silently upgraded or silently
  ignored.
* **No feature screen exists** — every nav destination under `/app`
  renders the same generic placeholder. Letters, Documents,
  Notifications, and every administrative screen remain exactly what §32
  already scheduled for later steps.
* **Two harmless React Router "future flag" warnings appear during
  tests** (`v7_startTransition`, `v7_relativeSplatPath`) — informational
  only; not addressed, since opting in would be a behavior change this
  foundation phase has no reason to make yet.

## 35. Phase 5B implementation record — Authentication & Account UX

Turns §34's foundation-level `LoginPage`/`SignupPage` into the complete
V1 authentication/account experience. No backend file was touched; every
behavior below is driven by the exact confirmed contract in
`backend/app/api/v1/endpoints/auth.py`, re-read fresh this phase.

### Resolved design tension: post-login user refresh (§4)

The implementation brief asked to "refresh/load the authoritative user
through `/auth/me`" after login, distinct from §34's original behavior
of setting `user` directly from `POST /auth/login`'s own `TokenResponse.user`
field. Re-reading `auth.py` resolved this without adding a redundant
call: the login endpoint constructs `TokenResponse.user` from the exact
same freshly-queried `UserPublic` it just authenticated in that request
— it is not derived from the JWT, and it is not client-supplied. A
follow-up `GET /auth/me` immediately afterward would return byte-identical
data. **Decision: `AuthContext.login()` continues to set `user` directly
from the login response.** What actually matters — "never derive
authorization state from decoded JWT claims" — was already true and
remains true: this codebase has no JWT-decoding library, and nothing
parses the token payload. Session *restoration* (a stored token with no
fresh server response to trust) is the case that genuinely requires
calling `/auth/me`, and it already did so before this phase.

### LoginPage / SignupPage (§3, §6, §7)

Both rebuilt as real forms: client-side required-field and email-format
validation (`utils/formValidation.js`, dependency-free — no form
library), `aria-invalid`/`aria-describedby` wiring every field to its own
error text, a disabled submit button with a distinct loading label while
a request is in flight, and a clearing of the previous error the instant
a new submission begins. Server-side validation (422, via
`errorNormalization.js`'s existing field-error extraction) remains
authoritative — client-side checks only ever prevent an obviously
incomplete submission from being sent.

### Pending-approval and deactivated-account UX (§8, §9)

Two new reusable components, `components/PendingApprovalNotice.jsx` and
`components/DeactivatedAccountNotice.jsx`, each rendered in place of the
form. `PendingApprovalNotice` appears in two places that share the same
underlying fact: right after a successful signup, and after a login
attempt against a `PENDING_APPROVAL` account (`403`, exact message
matched via `authService.PENDING_APPROVAL_MESSAGE`). Neither invents an
approval timeline, an email-notification promise, or administrator
contact information — none of that is available from the backend.
`DeactivatedAccountNotice` appears only after a login attempt against a
deactivated account (`403`, `authService.DEACTIVATED_MESSAGE`) — states
the account is disabled and its record has not been deleted, nothing
more. It has no "logout" action because there is no scenario in which
the frontend can show it to an already-authenticated user: the
backend's distinct deactivation message is raised only by
`POST /auth/login` (`auth_service.py`); a mid-session deactivation
instead surfaces as a generic `401` on the next API call, already
handled by `apiClient.js`'s existing centralized 401 handler. This
asymmetry is intentional, not an oversight, and is documented in the
component's own header comment.

### Session restoration hardening (§10)

`AuthContext` now distinguishes *why* `GET /auth/me` failed during
restoration, not just that it failed. A definite rejection (`401`, or
any other real response) still clears the stored token, exactly as
before. A network failure (`status: 0` — the server could not be
reached at all) no longer clears the token: the stored credential might
still be perfectly valid, so discarding it would force a needless fresh
login the moment connectivity returns. Instead, `status` becomes
`'unauthenticated'` (never silently `'authenticated'` — a server outage
is never treated as a successful session) and a new `restoreError`
field is set with an explanatory message; `LoginPage` renders this as a
retry-capable banner (`ErrorState` + `retryRestoreSession`, also newly
exposed from the context) above the login form, rather than presenting
an unexplained demand to re-enter credentials.

### Logout (§11)

Unchanged mechanism from §34 (`AuthContext.logout()` → clear token,
clear user, set `'unauthenticated'`), now covered by an end-to-end test
(`routes/routing.test.jsx`) that renders the real `AuthProvider` +
`ProtectedRoute` + `AppShell` + `Topbar` together, clicks the real
"Log out" button, and asserts the app lands back on `/login` with the
token cleared. Still purely client-side token removal — **there is no
server-side revocation endpoint, and this is documented as an accepted
architecture limitation** (unchanged since Phase 3A), not a defect.

### Redirects (§12)

`SignupPage` gained the same "already authenticated → redirect into the
app" guard `LoginPage` already had in §34 — a real gap this phase found:
before this change, an authenticated user visiting `/signup` directly
would see the signup form instead of being redirected. Both pages now
check `status === 'authenticated'` before rendering their form, matching
`ProtectedRoute`'s own unauthenticated → `/login` redirect. No loop is
possible: the two guards check mutually exclusive states of the same
`status` value.

### Error handling and account-state coupling (§14, §5)

The two backend account-state messages (`"Your account is awaiting
administrator approval."`, `"Your account has been deactivated."`) are
matched verbatim in exactly one place, `services/authService.js`
(`PENDING_APPROVAL_MESSAGE`/`DEACTIVATED_MESSAGE`), imported by
`LoginPage` rather than duplicated. A `401` on login always renders the
same generic "Incorrect email or password." text the backend sends —
this page never adds logic that would distinguish a nonexistent account
from a wrong password itself. A `404`/`403`/`409` from signup is shown
using the backend's own message unmodified; none is remapped into a
different status's meaning.

### Accessibility (§17)

Every form field: a real `<label htmlFor>`, `aria-invalid` when its own
client- or server-reported error is active, and `aria-describedby`
pointing at that error's own `id` (verified by a dedicated test that
resolves the `aria-describedby` id via `document.getElementById` and
asserts it contains the visible error text — not just that the attribute
exists). Submission-level errors use the existing `ErrorState`'s
`role="alert"`; the two new account-state notices use `role="status"`
(an informational account-state fact, not an error the user caused).

### Tests (§20)

44 tests total (was 17 in §34) across 8 files. New/expanded this phase:
`utils/formValidation.test.js` (6), `pages/LoginPage.test.jsx` (11 —
success, invalid credentials, pending, deactivated, required-field
validation, `aria-invalid`/`aria-describedby` association, loading
state, network failure, already-authenticated redirect, error clears on
resubmission, retryable session-restoration-network-failure banner),
`pages/SignupPage.test.jsx` (7 — required-field validation, password
mismatch, pending-approval success state, duplicate-account error,
not-authorized error, the payload sent to the backend contains exactly
`full_name`/`email`/`password`/`password_confirm` and nothing else,
already-authenticated redirect), `context/AuthContext.test.jsx` (extended
from 5 to 7 — the network-failure-does-not-clear-token case and its
retry), `routes/routing.test.jsx` (1, new — the logout-redirect
integration test described above). `services/errorNormalization.test.js`,
`navigation/navigationConfig.test.js`, `routes/ProtectedRoute.test.jsx`
are unchanged from §34.

### Validation

`npm run build` succeeds (117 modules, no errors). `npm run test` —
**44 passed**, 0 failed (re-run twice: once before, once after the final
self-review pass). Backend regression: `pytest tests/` — **458 passed**,
unaffected, confirming zero backend impact. `git status` confirms no
file under `backend/app/`, `backend/alembic/`, or `backend/tests/` was
touched.

### Known limitations (post-implementation)

* Everything listed in §34's own "Known limitations" still applies
  unchanged (the `npm audit` advisories, the two React Router future-flag
  warnings) — neither is affected by this phase's work.
* No server-side token revocation exists — logout is client-side removal
  of the locally held JWT only; an already-issued token remains valid
  until it naturally expires. This is the existing, accepted V1
  architecture (unchanged since Phase 3A), restated here because §11 of
  the brief asked for it to be explicit, not because it is new.
* A network failure during session restoration is retried manually (a
  button in the banner) rather than automatically — no automatic
  retry/backoff was added, since the brief asked only that a network
  failure not be silently treated as authenticated and that the token
  not be discarded; automatic retry was not requested and would add
  complexity (timers, backoff, cancellation) this phase has no clear
  requirement for yet.

## 36. Phase 5C implementation record — Core Registry UI

Turns the `/app/letters` and `/app/system/letters` placeholders into a
complete V1 Letter registry: list/search/sort/paginate, create, view,
edit, and archive. No backend file was touched; every behavior below is
driven by the exact confirmed contract in
`backend/app/api/v1/endpoints/letters.py`,
`app/services/letter_service.py`, `app/services/authorization.py`, and
`app/schemas/letter.py`, all re-read fresh this phase — not the §10
summary table above, which predates this implementation and is kept
only as historical review context.

### CONFIRMED backend-contract gap, not silently worked around

`GET /api/v1/categories`, `GET /api/v1/classifications`, and
`GET /api/v1/departments` are all `require_system_admin`-only
(`app/api/v1/endpoints/{categories,classifications,departments}.py`) —
a fact this phase confirmed by reading the endpoint dependencies
directly, not previously called out this precisely anywhere in this
document. `POST /api/v1/letters` (create) is `require_user_or_admin`,
which structurally *excludes* SYSTEM_ADMIN (no department to record a
letter against). The intersection is empty: **no role that can create
or edit a Letter can ever legitimately load the category/classification/
department reference-data lists**, and the one role that can load them
(SYSTEM_ADMIN) can never create a Letter.

Resolved, not routed around: `category_id`/`classification_id` never
appear on the Create form for any role (no caller of that form could
populate them regardless of role). On Edit, they appear only for a
SYSTEM_ADMIN caller — the only role for which both the reference-data
load and `assert_letter_access`'s edit permission actually succeed. A
USER/ADMIN editing a letter never touches those two fields; the
backend's own "omitted field means unchanged" `LetterUpdate` semantics
leave whatever value was already there untouched. `source_department_id`
is a separate, deliberate *simplification* (not a backend blocker) —
omitted from both forms for all roles because `source_name` (always
required, always shown) already conveys the source in human-readable
form, and resolving the optional structured cross-reference would need
the same SYSTEM_ADMIN-only department list for comparatively little
value. Neither omission invents a workaround (no hardcoded category/
classification/department names anywhere — grepped, confirmed zero
matches outside test fixtures) — both are documented, honest scope
narrowings in response to a real, confirmed contract fact.

A related, already-known backend limitation this phase had to design
around rather than paper over: `LetterUpdate` cannot currently clear a
nullable field back to `null` (§10 above) — sending an explicit `null`
for `category_id`/`classification_id` on edit would silently no-op, not
unassign. The SYSTEM_ADMIN edit form therefore never sends a `null` for
either field; it only ever sends a value when one is actually chosen,
and says so directly in the form's own hint text rather than implying
"Unassigned" works when it doesn't.

### Services (§30 of the brief)

`services/letterService.js` — `list`/`get`/`create`/`update`/`archive`,
matching the five confirmed endpoints exactly. `create`/`update` route
every payload through an explicit field allowlist
(`CREATE_FIELDS`) mirroring `LetterCreate`'s own field set — there is no
code path by which `recipient_department_id`/`recorded_by`/`status`/`id`
could reach the request body, verified by a dedicated payload-shape test
on both the create and edit forms. `services/categoryService.js`/
`classificationService.js`/`departmentService.js` — thin wrappers around
their respective `GET` endpoints, each documented in its own header as
SYSTEM_ADMIN-only, called only from SYSTEM_ADMIN-gated code paths.

### List/search/sort/pagination (§3-§5, §8-§13)

`pages/LetterListPage.jsx` — one component mounted at both
`/app/letters` (USER/ADMIN) and `/app/system/letters` (SYSTEM_ADMIN,
`RoleGuard`-wrapped), adapting to `user.role` the same way
`RoleGuard`/`navigationConfig.js` already do, rather than two
near-duplicate pages. All list/filter/sort/pagination state lives in the
URL via `useSearchParams` (already part of `react-router-dom` — no new
dependency), so refresh, back/forward, and bookmarking all preserve
registry state (§11). The seven confirmed text filters, the `status`
exact filter, and the inclusive date range are available to every role;
`category_id`/`classification_id`/`department_id` filters are rendered
only when the corresponding reference-data list loaded successfully —
in practice, SYSTEM_ADMIN only, per the gap above. Sorting exposes all
four whitelisted fields (`received_at`/`created_at`/`reference_number`/
`subject`, `LetterSortField`) via an explicit dropdown plus clickable,
`aria-sort`-labeled column headers for the three that have a matching
table column. Pagination renders exactly the backend's own
`page`/`page_size`/`total`/`total_pages` — `total_pages` is never
recomputed client-side. A response whose `page` exceeds its own
`total_pages` (e.g., a filter narrowed the result set out from under an
already-paginated view) is corrected by re-requesting the corrected
page, not left showing an empty page silently.

### Classified-record safety (§7, §12 — CRITICAL)

`items`/`total` are rendered exactly as the backend returns them — no
client-side re-filtering, no post-fetch row removal, no distinguishing
label for a restricted-but-existing record. A `404` on
`GET /api/v1/letters/{id}` — whether the letter doesn't exist, belongs
to another department, or is classified and inaccessible to this caller
(all three collapsed by `LetterNotFoundError`,
`app/services/letter_service.py:_get_for_access`) — renders the
identical generic "Letter not found," verified by a dedicated test
asserting the rendered text contains neither "classif" nor "permission."

### Create / edit / archive (§14-§19)

`pages/LetterFormPage.jsx` — one component for both
`/app/letters/new` (create) and `/app/letters/:id/edit` (edit), per
§31's own reuse recommendation. Field set matches `LetterCreate`/
`LetterUpdate` exactly, minus the two documented omissions above.
Client-side validation (`utils/formValidation.js:validateLetterForm`) is
lightweight and checks only the fields the backend itself requires at
creation (`reference_number`/`subject`/`source_name`/`sender_name`/
`sender_designation`/`sender_department`/`received_at`) — never a
replacement for the backend's own authoritative validation, whose `422`
field errors render through the same mechanism. `pages/
LetterDetailPage.jsx` renders every `LetterResponse` field except
`recorded_by` (no cross-role name-resolution endpoint is in this
phase's scope — only Category/Classification reference-data consumption
was authorized, per the brief's own §40) — `created_at` conveys "when
this was recorded" without needing one. Archive
(`components/ArchiveConfirmDialog.jsx`) never says "delete" or
"permanent" — `DELETE /api/v1/letters/{id}` is confirmed, from the
endpoint's own summary string, to be a soft status transition, never a
physical row deletion; the dialog's copy states this directly ("It
remains fully visible in the registry... archiving does not delete or
hide its record"), and the archive action itself disappears once a
letter is already `ARCHIVED` (idempotent on the backend, but showing an
already-fired action as available is misleading).

### Role-aware UX (§20-§21)

USER and ADMIN are treated identically throughout — not a shortcut, but
a direct match to `LetterService`'s own docstring: "USER and ADMIN share
identical access within their own `recipient_department_id`." SYSTEM_ADMIN
gets a resolved Department column (from the SYSTEM_ADMIN-only reference
load above) and no "Record New Letter" action, matching
`POST /letters`'s `require_user_or_admin` dependency exactly — derived
from the documented backend contract, not an invented frontend rule
(§20's own explicit preference). No department selector is ever shown to
USER/ADMIN (§21) — `department_id` is silently ignored for them
server-side regardless, so there is nothing for a frontend control to do
even if one existed.

### Accessibility (§27) and responsive design (§28)

Semantic `<table>` markup with `scope="col"`/`scope="row"`, `aria-sort`
on the three clickable sort headers, `aria-current="page"` on the active
pagination control, labelled filter/form inputs with `aria-invalid`/
`aria-describedby` field errors, and a dependency-free but
keyboard-trapped, `Escape`-dismissible `role="dialog"` confirmation for
archive. The table scrolls horizontally inside its own container on
narrow viewports (`overflow-x: auto`, a fixed `min-width` on the table
itself) rather than letting the page itself overflow; the filter grid
and create/edit form collapse to a single column below the existing
tablet breakpoint. No CSS framework was added.

### Performance (§29)

One request per registry page load — category/classification/department
names come from lookup maps loaded once (SYSTEM_ADMIN only), never
per-row. No caching library was added; the reference-data effect simply
runs once per page mount, matching the brief's own "do not introduce a
caching library unless genuinely required" instruction.

### Tests (§34 of the brief)

84 tests total (was 44 after Phase 5B) across 17 files. New this phase:
`utils/formValidation.test.js` extended with `validateLetterForm` (3),
`components/LetterTable.test.jsx` (5 — accessible headers, `aria-sort`,
sort-click behavior, conditional columns, row links),
`components/Pagination.test.jsx` (4 — single-page collapse,
`aria-current`, boundary disabling, page-change callback),
`pages/LetterListPage.test.jsx` (10 — successful list, empty state, API
failure with retry, URL-encoded request params, filter-resets-page,
clear-resets-filters-and-sort, sort toggling, role-based Create-link/
department-column visibility, no reference-data requests for
non-SYSTEM_ADMIN), `pages/LetterDetailPage.test.jsx` (7 — field
rendering, generic 404 with no classified/permission language, retry on
non-404 failure, archive dialog copy, successful archive, failed
archive, hidden archive action once already archived),
`pages/LetterFormPage.test.jsx` (11 — required-field validation, create
success, 422 field errors, 403 forbidden, exact payload shape on both
create and edit, no category/classification field on create for any
role, edit pre-fill, edit 404, category/classification visible only for
SYSTEM_ADMIN on edit).

### Validation

`npm run build` succeeds (139 modules, no errors). `npm run test` —
**84 passed**, 0 failed. Backend regression: `pytest tests/` — **458
passed**, unaffected, confirming zero backend impact. `git status`
confirms no file under `backend/app/`, `backend/alembic/`, or
`backend/tests/` was touched.

### Known limitations (post-implementation)

* **USER/ADMIN cannot assign or view a resolved category/classification
  name when creating or editing a Letter** — the confirmed backend
  contract gap above. A letter can still carry a category/classification
  (assigned by a SYSTEM_ADMIN via edit), but the two roles that do the
  actual day-to-day recording have no UI path to set or see one in V1.
* **A category/classification, once set by SYSTEM_ADMIN, cannot be
  cleared back to unassigned through this UI** — the pre-existing
  `LetterUpdate` "omitted means unchanged" limitation (§10); the form
  never attempts it and says so in its own hint text.
* **`source_department_id` has no UI at all** — a deliberate
  simplification (not a backend blocker); `source_name` already conveys
  the source in every screen this phase builds.
* **`recorded_by` is never resolved to a user's name** — no cross-role
  user-lookup endpoint was in this phase's authorized scope (only
  Category/Classification reference-data consumption was, per the
  brief's own §40); the detail page shows when a letter was recorded
  (`created_at`) without who, by id or name.
* Everything listed in §34/§35's own "Known limitations" still applies
  unchanged (the `npm audit` advisories, the two React Router
  future-flag warnings, no server-side logout revocation) — none is
  affected by this phase's work.
* **No document or notification UI** — explicitly out of scope for this
  phase (Phase 5C); at the time, the Letter detail page had a labeled
  placeholder section for documents rather than a fake feature.
  **RESOLVED (Phase 5E)** — the placeholder was replaced with a real
  Documents section, and a full Notification UI was added; see
  `document-notification-ui.md` §27.
