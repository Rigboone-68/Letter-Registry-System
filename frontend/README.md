# LRS Frontend

React + Vite client for the Letter Registry System. **Phase 5I.6A:
Sidebar icon identity correction complete** — the navigation "icons"
(3-letter monograms since Phase 5I.2) replaced with 9 small inline-SVG
geometric icons (grid/envelope/document-stack/bell/building/shield/
badge/folder/layers, plus a person icon for `Users`), each following
the one existing active-state color rule rather than a new mechanism;
`navigationConfig.js`/routes/labels/permissions untouched — see
"Visual design system" below. On top of Phase 5I.6's Final Polish,
Manual E2E & Handover Audit (the closing audit across all nine prior
visual phases, fixing one genuine defect — `NotificationBell`'s emoji
icon replaced with a CSS-only outline, zero behavior change — and
confirming everything else already consistent or intentional; manual
browser verification honestly reported as not performed, no
browser-automation tool available in this environment). The Phase 5I
visual architecture is now closed, on top of Phase 5I.5's Boot &
Loading Experience (a new `BootScreen` — a CSS-only "LRS Registry
Glyph" nested-square mark with a sequential-tick "registry scan"
animation and a truthful accessible status — gated at `App.jsx` using
`AuthContext`'s own existing `status === 'loading'` window, never a
duplicated timer; `AuthContext.jsx` untouched), Phase 5I.4E's
Authentication entrance visual transformation, Phase 5I.4D's
Documents & Notifications visual transformation, Phase 5I.4C's
Administration workspace visual transformation, Phase 5I.4B's
Letter Registry visual
transformation, Phase 5I.4A's Dashboard visual transformation, Phase 5I.3's Core UI Primitives &
Interaction System, Phase 5I.2's App
Shell & Navigation, Phase 5I.1's Global Visual Foundation, Phase 5H.1's Category &
Classification Admin UI, Phase 5H's Source
Department & Designation Master Data, Phase 5F's Dashboard &
Operational Overview UI, Phase 5E's Documents & Notifications UI, Phase
5D's Administration & Account Management UI, Phase 5C's core Letter
registry, Phase 5B's authentication/account UX, Phase 5A's foundation,
and Phase 5's own architecture/UX review
(`docs/architecture/frontend.md`,
`docs/architecture/administration-ui.md`,
`docs/architecture/document-notification-ui.md`,
`docs/architecture/dashboard.md`,
`docs/architecture/source-designation.md`). Login, signup, session
restoration, and logout are all in place; the Letter registry —
list/search/sort/paginate, create, view, edit, and archive — works
against the real backend; Department/Administrator/User management —
list/create/detail, authorization workflows, lifecycle actions, and
Admin department transfer — works against the real backend; Document
upload/list/download (integrated into the Letter detail page) and
Notifications (a bell in the Topbar, a dropdown panel, and a full
paginated page) work against the real backend; `/app/dashboard` renders
a role-aware operational overview with no chart, trend, or analytics
infrastructure of any kind; and the Letter form's Source and Designation
fields are now selection-driven — Source Department uses the existing
`DepartmentSelector`, Designation uses a new SYSTEM_ADMIN-managed
master-data dropdown — both replacing free-text entry, both backed by
real backend validation. Category and Classification management —
list/create/edit/activate/deactivate, SYSTEM_ADMIN only — now works
against the real backend at `/app/system/categories*` and
`/app/system/classifications*`, closing a gap where both routes
previously rendered a "planned" placeholder despite the backend
supporting this functionality since Phase 4B.

## Setup

```bash
npm install
cp .env.example .env.local     # optional — see "Configuration" below
npm run dev
```

Runs on `http://localhost:5173`. Requests to `/api` are proxied to the FastAPI
backend on port 8000 (see `vite.config.js`), so no absolute backend URL is
baked into the source.

```bash
npm run build      # production build (vite build)
npm run preview    # preview the production build locally
npm run test       # run the test suite once (vitest run)
npm run test:watch # run the test suite in watch mode
```

## Configuration

Only `VITE_`-prefixed variables are exposed to the browser bundle — never
place a secret in one. `.env.example` documents the two currently used:

| Variable | Purpose |
|---|---|
| `VITE_APP_NAME` | Display name shown in the Topbar |
| `VITE_API_BASE_URL` | Backend API base URL (default `/api/v1`, proxied in dev by `vite.config.js`) |

`.env.local` (git-ignored, like every `.env*` file except `.env.example`
— see the root `.gitignore`) is where a real local override would go;
neither variable is a secret, so committing `.env.example` with its
current placeholder values is safe.

## Authentication & token handling

`src/context/AuthContext.jsx` is the single authentication state
mechanism (`status`: `'loading' | 'authenticated' | 'unauthenticated'`,
plus `user`, always the `UserPublic` object most recently returned by
the backend — never decoded from the JWT client-side). On app start it
restores a session by validating any stored token against
`GET /auth/me` before rendering any protected route (`src/routes/ProtectedRoute.jsx`),
which avoids an authentication flicker.

**Token storage is isolated to one module**, `src/services/tokenStorage.js`
— nothing else reads/writes it directly. **V1 approach: `localStorage`.**
This is a **documented, PROVISIONAL placeholder**, not a settled
decision — `docs/architecture/frontend.md` §28 flags the exact storage
strategy as a pending deployment decision (a shared/kiosk workstation
would favor `sessionStorage` instead; a cookie-based approach would
require a backend change this project has not made, since the backend
issues a bearer token in a JSON body, not a cookie). Changing the
strategy later means editing only `tokenStorage.js`.

There is no logout endpoint on the backend (unchanged since Phase 3A —
no refresh-token/revocation mechanism exists) — logout is purely
client-side: `AuthContext.logout()` clears the stored token and cached
user, nothing more. **An already-issued JWT is not revoked server-side
by logging out** — it simply expires naturally later; this is the
accepted V1 architecture, not a defect.

A network failure while restoring a session (the server can't be
reached) is treated differently from a rejected token: the stored
credential is **not** discarded (it might still be valid), `status`
becomes `'unauthenticated'` so no protected content is ever shown, and
`LoginPage` displays a retry-capable banner (`restoreError` /
`retryRestoreSession` on `AuthContext`) instead of silently demanding a
fresh login.

## Authentication & account UX (Phase 5B)

* **Login** (`pages/LoginPage.jsx`) — email + password, client-side
  required/format validation with `aria-invalid`/`aria-describedby` on
  each field, a disabled submit button with a loading label while the
  request is in flight. A `401` always shows the backend's own generic
  "Incorrect email or password." — this page never distinguishes a
  nonexistent account from a wrong password. A `403` for a pending or
  deactivated account renders a dedicated notice component instead of a
  generic error (see below).
* **Signup** (`pages/SignupPage.jsx`) — `full_name`/`email`/`password`/
  `password_confirm` only; the backend's `SignupRequest` schema has
  `extra="forbid"` and no `role`/`department`/`status` field, so there is
  nothing on this form for one to bind to even accidentally (verified by
  a test asserting the exact payload shape sent to the backend). A
  successful signup never assumes the account is active — it always
  shows the pending-approval notice, since every new account starts
  `PENDING_APPROVAL`.
* **Pending approval** (`components/PendingApprovalNotice.jsx`) — reused
  in two places: right after signup, and after a login attempt against a
  `PENDING_APPROVAL` account. States only what the backend confirms —
  no approval timeline, no email-notification promise, no administrator
  contact information is invented.
* **Deactivated account** (`components/DeactivatedAccountNotice.jsx`) —
  shown only after a login attempt against a deactivated account (the
  backend only distinguishes this case at `POST /auth/login`; a
  mid-session deactivation instead surfaces as a generic `401`, handled
  by the existing centralized 401 handler). States the account is
  disabled and its record has not been deleted; exposes no
  administrative detail and no reactivation action (that is an
  administrative, backend-only operation).
* **Redirects** — an authenticated user visiting `/login` or `/signup`
  is redirected into `/app`; an unauthenticated user visiting `/app/*`
  is redirected to `/login` (unchanged, `ProtectedRoute`). The two
  checks are mutually exclusive states of the same `status` value, so no
  redirect loop is possible.
* **Validation** — lightweight, dependency-free (`utils/formValidation.js`):
  required fields, email format, password-confirmation match. Never a
  replacement for backend validation, which remains authoritative; a
  `422` field error from the backend is displayed the same way a
  client-side one is.

## Letter registry (Phase 5C)

**Frontend visibility and action controls here are UX conveniences
only. Backend authorization remains the security boundary** — nothing
in this section ever decides, filters, or infers what the caller may
see; it renders exactly what `GET`/`POST`/`PATCH`/`DELETE
/api/v1/letters*` returns.

* **List/search** (`pages/LetterListPage.jsx`, mounted at both
  `/app/letters` and `/app/system/letters`) — the seven confirmed text
  filters, `status`, an inclusive received-date range, and sorting on
  all four backend-whitelisted fields (`received_at`/`created_at`/
  `reference_number`/`subject`). Filter/sort/page state lives in the URL
  (`useSearchParams`), so refresh, back/forward, and bookmarking all
  preserve registry state. Pagination renders the backend's own
  `page`/`page_size`/`total`/`total_pages` — never recomputed
  client-side.
* **Classified-record safety (CRITICAL)** — `items`/`total` are rendered
  exactly as returned, with zero client-side re-filtering; a `404` on a
  Letter (nonexistent, wrong-department, or classified-and-inaccessible
  — the backend collapses all three into one response) always renders
  the identical generic "Letter not found."
* **Create/edit** (`pages/LetterFormPage.jsx`, one component for both)
  — field set matches `LetterCreate`/`LetterUpdate` exactly.
  `source_department_id`/`designation_id` (Phase 5H) are now real
  selection-driven fields — see "Source Department & Designation
  (Phase 5H)" below. `category_id`/`classification_id` remain omitted
  from Create entirely and shown on Edit only for SYSTEM_ADMIN — see
  "Known limitations" below, a **confirmed backend-contract gap**, not
  a frontend choice.
* **Archive, never "delete"** (`components/ArchiveConfirmDialog.jsx`) —
  `DELETE /api/v1/letters/{id}` is a soft status transition, never a
  physical row deletion; the confirmation dialog says so directly and
  never uses "delete" or "permanent." The action disappears once a
  letter is already archived.
* **Role-aware UX** — USER and ADMIN are treated identically (matching
  the backend's own `LetterService` docstring: they share identical
  access within their own department); SYSTEM_ADMIN sees a resolved
  Department column and no "Record New Letter" action, matching
  `POST /letters`'s own `require_user_or_admin` dependency.
* **API service layer** — `services/letterService.js`
  (`list`/`get`/`create`/`update`/`archive`, an explicit field allowlist
  on write) plus thin reference-data wrappers: `services/
  categoryService.js`/`classificationService.js` (SYSTEM_ADMIN-only,
  unchanged), `services/departmentService.js` (`list()` is now readable
  by any authenticated role, Phase 5H — see below).

## Administration & account management (Phase 5D)

Same UX-conveniences-only boundary as the Letter registry above —
nothing here decides, filters, or infers what the caller may manage; it
renders exactly what `GET`/`POST`/`PATCH`/`DELETE
/api/v1/{departments,admins,users}*` returns.

* **Departments** (`pages/DepartmentListPage.jsx`/`DepartmentCreatePage.jsx`/
  `DepartmentDetailPage.jsx`, `/app/system/departments*`, SYSTEM_ADMIN
  only) — list (`status` filter, the only one the backend supports),
  create, and one detail page with an inline edit mode rather than a
  separate edit route (the two-field edit surface didn't justify the
  split, unlike Letters). Activate has no confirmation dialog (purely
  restorative); Deactivate does, explaining its real operational impact
  without ever using "delete."
* **Administrators** (`pages/AdminListPage.jsx`/`AdminAuthorizePage.jsx`/
  `AdminDetailPage.jsx`, `/app/system/admins*`, SYSTEM_ADMIN only) —
  list (`status` + `department_id` filters, both real backend
  parameters here), a dedicated Authorize form (`email` +
  `department_id`, `ACTIVE`-only options), and a detail page whose
  actions are entirely status-gated: Approve (confirmed — not
  idempotent server-side), Deactivate + Transfer (`ACTIVE` only),
  Reactivate (`DEACTIVATED` only, not confirmed).
* **Admin transfer** (`components/AdminTransferDialog.jsx`) — states
  verbatim, using the backend's own confirmed guarantee
  (`app/services/admin_service.py:change_admin_department`), that
  historical Letters are never reassigned; a `409` (destination
  department not active) surfaces inline in the dialog, not as a
  page-level error.
* **Users** (`pages/UserListPage.jsx`/`UserAuthorizePage.jsx`/
  `UserAuthorizationsPage.jsx`/`UserDetailPage.jsx`,
  `/app/admin/users*`, ADMIN only) — the Authorize form has a single
  `email` field, matching `UserAuthorizationCreate` exactly (there is
  no `department_id` field on that schema at all — the target
  department is always the calling Admin's own). A separate,
  department-wide Authorizations list (defaults to `status=ACTIVE`)
  shows a creator-scoped Revoke action on every `ACTIVE` row — the
  response has no field to pre-filter by creator, so a mismatched
  attempt simply 404s generically, like any other.
* **The backend's read/lock-down vs. state-elevating asymmetry is
  preserved, not flattened** — Deactivate/Revoke/list actions never
  require the acting Admin's own department to be `ACTIVE`; Authorize/
  Approve/Reactivate do, and can `403` for a reason that has nothing to
  do with the target account. `UserDetailPage` phrases that `403`
  specifically around the Admin's *own* department, never the target
  User.
* **System Admin protection and Admin self-targeting prevention are
  both structural** — no endpoint can ever resolve a SYSTEM_ADMIN id or
  an Admin's own id (role-filtered repository lookups on the backend),
  so no frontend check exists or was added for either case; both simply
  404 like any other unresolvable id.
* **Three status enums, three visually distinct badge tones, never
  merged** — `StatusBadge` (extended, not replaced) renders
  `PENDING_APPROVAL` as a warning tone and `REVOKED` as a negative tone,
  distinct from a plain `DEACTIVATED`/`USED` neutral, with an optional
  `domain` prop as an accessible-name prefix.
* **API service layer** — `services/adminService.js`/`userService.js`
  (new), plus `services/departmentService.js` (extended from Phase 5C's
  single `list()` export to the full create/read/update/activate/
  deactivate set — existing zero-arg callers are unaffected).

## Documents & Notifications (Phase 5E)

Same UX-conveniences-only boundary as above — nothing here decides,
filters, or infers what the caller may access; it renders exactly what
`GET`/`POST /api/v1/letters/{id}/documents*` and
`GET/PATCH /api/v1/notifications*` return. **No frontend authorization
rule was added for either** — a document or a notification-linked
Letter that the caller cannot access renders the same generic `404`
this project has used since Phase 4B, with nothing distinguishing
"classified" from "nonexistent."

* **Documents** (`components/DocumentUploadForm.jsx`/`DocumentList.jsx`,
  integrated directly into `LetterDetailPage` — no separate route) —
  upload with `onUploadProgress`-driven feedback (falling back to an
  indeterminate state where progress can't be measured), client-side
  pre-checks (missing file/unsupported extension/oversized file)
  explicitly labeled as a UX convenience, never authoritative; the list
  renders only confirmed `DocumentResponse` fields with one Download
  action per row — no Delete/Replace/Archive, because no such endpoint
  exists. Download uses an authenticated blob fetch through the
  existing `apiClient` (a plain `<a href>` cannot carry the Bearer
  token a download requires), then a synthetic anchor click using the
  backend's own filename, then a delayed `URL.revokeObjectURL`.
* **Notifications** (`components/NotificationBell.jsx`/
  `NotificationPanel.jsx`/`NotificationItem.jsx`, `pages/
  NotificationsPage.jsx` at `/app/notifications`) — `NotificationBell`
  lives in the existing `Topbar` and polls
  `GET /notifications/unread-count` only (never the full list) on a
  60-second interval (`PROVISIONAL` — no confirmed business
  requirement mandates this exact number), paused while the browser
  tab is hidden via `visibilitychange`. `NotificationPanel` (dropdown,
  10 per page) and `NotificationsPage` (full page, real backend
  pagination) both render the same `NotificationItem`. **Mark-read is
  explicit-button-only** — clicking a notification's related-Letter
  link never marks it read; only the dedicated "Mark as read" button
  does, via `PATCH /notifications/{id}/read`. This is a deliberate
  override of the architecture review's own provisional "mark on
  navigate" lean, not a silently-invented policy — see
  `docs/architecture/document-notification-ui.md` §27.
* **No `recipient_user_id` or equivalent is ever sent** —
  `notificationService.list` forwards only `page`/`page_size`; there is
  no recipient-selection capability anywhere, matching the backend's
  own structural per-account isolation (no endpoint accepts a recipient
  identifier at all).
* **No `is_read` query parameter exists or was invented** — confirmed
  absent from the backend contract; `NotificationsPage` renders every
  notification for the current page, distinguishing read/unread only
  visually.
* **API service layer** — `services/documentService.js`
  (`list`/`upload`/`download` only — no `deleteDocument`/
  `replaceDocument`/`archiveDocument`, because no such endpoint
  exists), `services/notificationService.js` (`list`/`unreadCount`/
  `markRead`/`markAllRead` only).

## Dashboard & Operational Overview (Phase 5F)

`/app/dashboard` — a plain child route inside the existing
`AppShell`/`ProtectedRoute` tree, available to every role (no
`RoleGuard`; `pages/DashboardPage.jsx` renders role-appropriate content
itself). **No `dashboardService.js` exists** — every figure on the page
is one call to an existing service (`letterService`/
`notificationService`/`departmentService`/`adminService`/
`userService`), never a new or fabricated endpoint. The existing
`/app` index redirect to `letters` is unchanged; the dashboard is
additive, not the new default landing page.

* **Universal cards (every role)** — Total/Active/Archived Letters
  (three `letterService.list({ ..., page_size: 1 })` calls, reading
  only `.total` — a real, already department/classified-visibility-
  scoped SQL `COUNT`, never a client-side filter) and Unread
  Notifications (one one-time `notificationService.unreadCount()` call
  on mount — **not** a second polling interval; `NotificationBell`'s
  own 60-second poll, Phase 5E, is untouched).
* **SYSTEM_ADMIN-only cards** — Active Departments, Pending Admin
  Approvals. **ADMIN-only cards** — Active Users, Pending User
  Approvals (own department, server-derived — no parameter sent). A
  USER triggers zero Department/Admin/User requests.
* **Recent Letters** (`components/RecentLetters.jsx`) — up to 5
  Letters from one `letterService.list({sort_by: 'received_at', sort_order: 'desc', page_size: 5})`
  call, the same shape `LetterListPage` already uses, never the full
  registry. A Letter shown is exactly what the backend returned;
  clicking through to a Letter that later 404s is handled by
  `LetterDetailPage`'s existing, unmodified 404 behavior.
* **Quick Actions** (`components/QuickActions.jsx`) — role-scoped
  shortcuts to already-existing routes only: Create Department +
  Authorize Admin (SYSTEM_ADMIN), Authorize User (ADMIN), Record a
  Letter (USER). No "View Letters" shortcut for any role — the
  Sidebar's own link is already one click away.
* **What was deliberately left out** — any chart, trend, monthly
  comparison, department/category/classification breakdown, audit-
  derived figure, or document metric. Every one of these remained
  `PENDING BACKEND API` or `PENDING BUSINESS CLARIFICATION` in the
  Phase 5F architecture review (`docs/architecture/dashboard.md`), and
  none was implemented regardless. No filter controls (date range,
  category, classification) exist on the dashboard for the same reason.
  No charting library was installed.
* **Independent widget failure** — the Letters summary, Administration
  summary, Notifications count, and Recent Letters are four separately-
  fetched widgets; one failing renders `SummaryCard`'s "Unavailable"
  text or the existing `ErrorState` for that widget alone — never a
  fabricated `0`, never a dashboard-wide failure.

## Source Department & Designation (Phase 5H)

Two Letter-form fields moved from free text to real backend-validated
selections, in response to a live handover demonstration
(`docs/architecture/source-designation.md`).

* **Source Department** (`pages/LetterFormPage.jsx`) — the old
  free-text "Source name" input is replaced with the existing
  `DepartmentSelector`, bound to `source_department_id` (a field that
  already existed on every Letter schema since Phase 4B, just never
  had a frontend control until now). Selecting a department auto-fills
  `source_name` — still the backend's own required text field,
  unchanged — with that department's name; the user never types it.
  `services/departmentService.js:list()` is unchanged in shape, but its
  underlying endpoint is now readable by any authenticated role, not
  SYSTEM_ADMIN only (see "Known limitations" below).
* **Designation** — a brand-new, system-wide master-data resource.
  SYSTEM_ADMIN manages it at `/app/system/designations`
  (`pages/DesignationListPage.jsx` — a single combined list + inline
  create form + Activate/Deactivate page, deliberately not a
  Department-style three-page pattern, since Designation has nothing
  else to edit). On the Letter form, the old free-text "Sender
  designation" input is replaced with a `<select>` bound to a new
  `designation_id` field; selecting one auto-fills `sender_designation`
  (still required text, unchanged) with that designation's name — the
  backend remains authoritative and overrides this value server-side
  regardless, so the client-side mirroring here only ensures the
  required text field is never sent blank.
* **Historical integrity** — `designation_id` is a new, **optional**
  field; an existing Letter recorded before this phase simply has it
  `null` and keeps displaying its original `sender_designation` text
  unchanged, with no backfill of any kind. A Designation is never
  physically deleted — deactivating one blocks only *future*
  assignment; a Letter that already carries it keeps a fully readable,
  unchanged reference.
* **Required on create, not on edit** — `utils/formValidation.js`'s
  `validateLetterForm` takes an `{isEdit}` option: Source Department and
  Designation are required client-side when recording a *new* Letter,
  but never retroactively demanded when editing a Letter that predates
  this phase and legitimately has neither set.
* **Zero designations at first, by design** — no designation list was
  invented; the system intentionally starts empty, and SYSTEM_ADMIN must
  add the organization's real designations before any Letter can be
  recorded. The Letter form's Designation field shows a clear message,
  never a fake option, when the list is empty.
* **API service layer** — `services/designationService.js`
  (`list`/`create`/`update`/`activate`/`deactivate` — no delete function
  exists, mirroring `categoryService.js`'s own shape).

## Category & Classification management (Phase 5H.1)

A confirmed frontend completion gap, found during Phase 5H's own manual
E2E verification: `/app/system/categories` and
`/app/system/classifications` still rendered `PlaceholderPage`, even
though both resources' backend has supported list/create/update/
activate/deactivate (`SYSTEM_ADMIN`-only) since Phase 4B. This phase
adds the missing frontend only — **no backend file was touched**.

* **Categories** (`pages/CategoryListPage.jsx`/`CategoryCreatePage.jsx`/
  `CategoryDetailPage.jsx`, `/app/system/categories*`, SYSTEM_ADMIN
  only) — list (`status` filter, the only one the backend supports),
  create, and one detail page with an inline edit mode, mirroring
  `DepartmentListPage`/`DepartmentCreatePage`/`DepartmentDetailPage`
  exactly. Activate has no confirmation dialog; Deactivate does. No
  delete action — there is no `DELETE` route on the backend.
* **Classifications** (`pages/ClassificationListPage.jsx`/
  `ClassificationCreatePage.jsx`/`ClassificationDetailPage.jsx`,
  `/app/system/classifications*`, SYSTEM_ADMIN only) — identical shape
  to Categories, plus a `restricts_access` checkbox on the form and a
  plain "Yes"/"No" column/field wherever it's displayed (never
  color-only). **This flag's real effect on classified-Letter
  visibility is entirely `assert_letter_access`'s decision on the
  backend, unchanged by this phase** — the frontend only ever forwards
  the SYSTEM_ADMIN caller's explicit choice; it never computes, infers,
  or enforces access itself.
* **`services/categoryService.js`/`classificationService.js` extended**
  from Phase 5C's single `list()` export to the full create/read/
  update/activate/deactivate set, mirroring `departmentService.js`'s own
  Phase 5D extension pattern — existing zero-arg `list()` callers
  (`LetterFormPage.jsx`'s reference-data fetch) are unaffected, since
  `list(params = {})` defaults to the identical prior behavior.
* **No route or navigation redesign** — `navigationConfig.js` already
  pointed both entries at these exact paths; only `routes/index.jsx`
  changed, replacing two `PlaceholderPage`-wrapped routes with nested
  `RoleGuard` route groups identical in shape to `system/departments`.
* **The known Letter-form gap is unchanged and was not in scope** — USER/
  ADMIN still cannot assign or view a resolved category/classification
  when recording or editing a Letter (see "Known limitations" below);
  this phase only built the SYSTEM_ADMIN management screens for the
  resources themselves, per explicit instruction not to touch
  `LetterFormPage.jsx`'s selector-gating logic.

## Visual design system (Phase 5I review, Phase 5I.1 global foundation)

Phase 5I (`docs/architecture/ui-design-system.md`) is a review-only
inspection of the entire frontend's visual design against a "futuristic
enterprise command center" direction — no code was changed by it. Phase
5I.1 is the first implementation pass, **global foundation only**:

* **Tokens** (`styles/tokens.css`) — additive: `--color-text-secondary`,
  `--color-border-subtle`, `--color-surface-elevated`,
  `--color-accent`, `--color-info`/`--color-info-bg`,
  `--color-success-bg`, `--color-highlight-bg`, and a 5-value motion
  scale (`--motion-instant`/`-fast`/`-normal`/`-slow`/`-ease`). Every
  Phase 5A token is unchanged; nothing was renamed.
* **A real, pre-existing bug fixed**: the ACTIVE status badge and the
  unread-notification row both used to render with
  `--color-warning-bg` (a copy-paste artifact, found during the Phase
  5I review) — each now uses its own correct token
  (`--color-success-bg`, `--color-highlight-bg` respectively). No
  status value, label, or component behavior changed.
* **Global CSS** (`styles/global.css`) — a static atmospheric background
  wash (CSS-only, no animation), a strengthened `:focus-visible`
  treatment, a global `prefers-reduced-motion` safety net, and one
  narrow global transition rule (`color`/`background-color`/
  `border-color`/`opacity`/`box-shadow` only, never `transition: all`)
  applied to every existing interactive element with zero per-component
  edits.
* **Phase 5I.2 (App Shell & Navigation)** — `Sidebar`/`Topbar`
  visually redesigned: a small CSS-only brand mark, a 3-letter monogram
  glyph per nav item (disambiguated across all three roles' real
  labels — a single initial collides, e.g. Categories/Classifications
  both start with "C"), an active-route accent bar, a desktop collapse
  toggle (no persistence — this codebase's `localStorage` is scoped to
  auth tokens only), and a mobile drawer (`role="dialog"`, a real focus
  trap and Escape handling generalized from `ConfirmDialog`'s own
  pattern, a backdrop, closes automatically on route change).
  `navigationConfig.js`'s role-derived list is byte-for-byte unchanged.
  The AJ-OVA Labs footer (`PRODUCTION_CREDIT`) is now actually rendered
  once in `AppShell`, on every authenticated screen.
  `NotificationBell`'s polling/API/behavior is completely untouched.
* **Phase 5I.3 (Core UI Primitives)** — a new shared
  `styles/primitives.module.css` (button/table/dialog base classes,
  consumed via CSS Modules' `composes`) that `AdminPages`/
  `LetterFilters`/`DocumentUploadForm`/`DataTable`/`LetterTable`/
  `ConfirmDialog`/`ArchiveConfirmDialog`/`Topbar`/`NotificationItem` now
  reach; a global form-control base added to `global.css` (`composes`
  cannot target the descendant selectors most existing form
  duplication was written with); `StatusBadge` gained a small
  `aria-hidden` shape per tone; `EmptyState` gained a CSS-only document
  glyph; `NotificationItem`'s unread state gained a left accent bar;
  dialogs gained a short, reduced-motion-safe entrance animation. No
  Dashboard/Letter-page/Administration-page/Document-page/
  Notification-panel/Authentication-page redesign; no boot screen or
  loading glyph; no system-status indicator (no honest signal exists to
  back one).
* **Phase 5I.4A (Dashboard Visual Transformation)** — the first
  screen-level pass, `/app/dashboard` only: recomposed into a header
  (neutral eyebrow/subtitle, no invented system-health claim, grepped
  and tested for)/metrics/registry-activity/quick-actions layout;
  `SummaryCard` unified onto one accent-bar/corner-mark/tabular-numeral
  treatment; `RecentLetters` reuses the existing accent-bar-on-hover
  language and gained a real "N shown" count; `QuickActions` became
  tiles with a decorative, `aria-hidden` arrow. Every metric, fetch, and
  role-based branch in `DashboardPage.jsx` is unchanged — confirmed via
  `git diff`. No chart, trend, or fabricated comparison of any kind.
* **Phase 5I.4B (Letter Registry Visual Transformation)** — the second
  screen-level pass, the Letter registry family only
  (`LetterListPage`/`LetterFormPage`/`LetterDetailPage`/
  `LetterFilters`/`LetterTable`): a registry header (eyebrow/accent
  line, the existing `{total} total` count restyled as a chip with its
  exact text unchanged); the filter panel recomposed into a "Registry
  Search" console (the same 13 fields, grouped into four `<fieldset>`s,
  plus a decorative "N active filters" badge computed from the page's
  own existing filter count); the table gained a row accent-bar-on-hover
  and tabular reference numbers; the Letter form gained the same header
  treatment and finally composed the shared button primitives (deferred
  from Phase 5I.3, which explicitly excluded Letter pages); the detail
  page became a four-section record dossier (Correspondence/Source/
  Sender/Additional details). Category/Classification were deliberately
  **not** added to the dossier — doing so would need a new service call
  and role branch, a functional change outside this phase's visual-only
  boundary. Every field, filter key, URL parameter, sort field, payload,
  and role branch across all five files is unchanged — confirmed via
  `git diff`.
* **Phase 5I.4C (Administration Visual Transformation)** — the third
  screen-level pass, the entire administration workspace
  (Departments/Administrators/Users/Authorizations/Designations/
  Categories/Classifications, ~28 files): a console-wide eyebrow/
  accent-line/chip-count header language and consistent button
  treatment, established almost entirely by enhancing the two files
  nearly every one of these pages already shared
  (`AdminPages.module.css`/`DataTable.module.css`) rather than
  per-resource work; each of 17 list/create/detail pages then needed
  only a small, resource-specific eyebrow-text insertion.
  `AdminTransferDialog` gained real visual separation between
  current-department/target-department/consequences, with its required
  wording ("does not move or reassign any historical record") confirmed
  byte-for-byte unchanged against the exact existing test assertion.
  Every API payload, service call, role branch, and 403/404 collapsing
  behavior confirmed unchanged via `git diff` and a dedicated 107-test
  pass across all 17 Administration test files.
* **Phase 5I.4D (Documents & Notifications Visual Transformation)** —
  the fourth screen-level pass. `DocumentList` already inherited the
  Phase 5I.4C row-accent-bar table treatment for free via its shared
  `DataTable.module.css` import, so no `DocumentList`-specific CSS was
  needed; `LetterDetailPage`'s "Documents" heading gained a real,
  non-fabricated attachment count (`documents.length`); the upload form
  gained a percentage-bound progress bar shown only when a real
  percentage is known (no fake progress). The Notification panel gained
  an "Operational Signals" eyebrow and a CSS-only connector to the
  Topbar bell; notification rows gained one more static, non-animated
  unread dot alongside the existing accent bar/background/weight; the
  full notification page gained the same eyebrow/accent-line/chip-count
  header language used elsewhere. `NotificationBell` was audited and
  left unmodified (already at the target visual bar). No unread filter/
  search/category/bulk control was added (none exist in the backend
  contract); mark-read stays explicit-button-only. Every service call,
  payload, and role branch confirmed unchanged via `git diff`.
* **Phase 5I.4E (Authentication Visual Transformation)** — the fifth
  screen-level pass, the unauthenticated entrance experience
  (`LoginPage`, `SignupPage`, and the `PendingApprovalNotice`/
  `DeactivatedAccountNotice` states they render). Confirmed the
  existing composition was exactly the generic "white card + email +
  password + blue button" pattern, with the submit button never
  composed onto the Phase 5I.3 shared primitives (Authentication pages
  were explicitly deferred in that phase). Both pages now share one
  local `AuthShell` wrapper rendering a static brand mark (the same
  nested-square geometry `Sidebar.module.css` established in Phase
  5I.2, scaled up), `APP_NAME`, and the existing, previously-unrendered
  `PRODUCTION_CREDIT` line — distinguished only by a small eyebrow
  label ("Account Access" vs. "New Account Request"). The submit
  button now composes `btn btnPrimary`; both account-state notices
  gained a small `aria-hidden` color marker. No password-visibility
  toggle was added (none exists today); the animated boot/loading
  glyph remains reserved for a later phase. Every field, label,
  validation rule, submit handler, and redirect confirmed unchanged via
  `git diff`; `AuthContext.jsx` was read but not modified.
* **Phase 5I.6 (Final Polish, Manual E2E & Handover Audit)** — the
  closing audit across all nine prior visual phases. Combined
  automated, codebase-wide searches (hardcoded colors, `transition:
  all`, `outline: none`, stray `console.log`/`setTimeout`, every
  animation's reduced-motion coverage, every breakpoint, every emoji,
  branding-string consistency, and the full security-pattern set) with
  targeted reads of whatever each result needed judgment on. Found and
  fixed exactly one genuine defect: `NotificationBell`'s icon was a raw
  🔔 emoji — the one full-color, OS-rendered pictograph anywhere in the
  application — replaced with a CSS-only bell outline matching the
  restrained icon language everywhere else, with zero behavior change
  (its own 9 existing tests pass unmodified). Several other candidates
  were reviewed and confirmed intentional or already correct rather
  than changed (`NotificationPanel`'s deliberate `outline: none` on a
  non-Tab-reachable container, a one-pixel breakpoint-naming
  inconsistency with no visible consequence, the Boot screen's
  deliberately simpler background versus Authentication's) — documented
  in full in `docs/architecture/ui-design-system.md`'s own "Phase
  5I.6" section. Manual browser verification was **not performed** — no
  browser-automation tool is available in this environment. The Phase
  5I visual architecture (5I.1 through 5I.6) is now considered closed.
* **Phase 5I.6A (Sidebar Icon Identity Correction)** — a targeted fix
  found during Phase 5I.6's own manual review: the Sidebar's navigation
  "icons" were actually 3-letter monograms (`DAS`/`LET`/`DOC`/etc.), a
  deliberate Phase 5I.2 placeholder that read as text labels, not
  icons. Replaced with 9 small inline SVG icons (Dashboard/Letters/
  Documents/Notifications/Departments/Administrators/Designations/
  Categories/Classifications, plus a `Users` icon the brief's own
  suggested mapping omitted) — no icon library, no external asset.
  Every icon uses `stroke="currentColor"`, so its color simply follows
  the existing `.linkActive .linkGlyph` active-state rule, never a
  second mechanism; the old bordered 30×22px "chip" container was
  replaced with a plain, unboxed 18×18px icon box. `navigationConfig.js`,
  routes, labels, permissions, active-route logic, and Sidebar
  collapse/mobile-drawer behavior all confirmed unchanged via
  `git diff`.
* **Phase 5I.5 (Boot & Loading Experience)** — the application's
  startup/loading identity. Inspection found `AuthContext` already
  exposes a genuine `status === 'loading'` window covering the first
  session-restoration check; `App.jsx` was gated on that *existing*
  value — never a duplicated timer or a second loading flag — since it
  is the one point above `ProtectedRoute`/`RootRedirect`/every route
  that covers every entry path uniformly. A new `BootScreen` component
  renders during that window: a CSS-only "LRS Registry Glyph" (the
  same nested-square geometry `Sidebar.module.css`/
  `AuthPages.module.css` already established, plus four ticks that
  illuminate in sequence — a duration derived via `calc()` from the
  existing `--motion-slow` token, not a new invented duration) and a
  separate, real `role="status"` message ("Loading Letter Registry
  System"). `ProtectedRoute`/`RootRedirect`'s own `status ===
  'loading'` branches, `LoadingState`, and every other existing loading
  moment in the application are unchanged — this phase adds one new
  identity moment, it does not redesign existing loading states
  elsewhere. No artificial delay, fake progress, or fake initialization
  step was added; `AuthContext.jsx` was read but not modified. Full
  implementation record, including what's explicitly deferred, in
  `docs/architecture/ui-design-system.md`'s own "Phase 5I.1"/"Phase
  5I.2"/"Phase 5I.3"/"Phase 5I.4A"/"Phase 5I.4B"/"Phase 5I.4C"/"Phase
  5I.4D"/"Phase 5I.4E"/"Phase 5I.5"/"Phase 5I.6"/"Phase 5I.6A" sections.

## Source layout

| Path | Responsibility |
|---|---|
| `src/main.jsx` | React entry point; imports the global stylesheet/tokens |
| `src/App.jsx` | Provides `AuthProvider` and mounts the router; since Phase 5I.5, gates on `AuthContext`'s own existing `status === 'loading'` value to render `BootScreen` instead of `RouterProvider` for that one genuine initialization window — no duplicated timer, `AuthContext.jsx` itself unchanged |
| `src/routes/` | `router` (route tree), `ProtectedRoute` (authentication guard), `RoleGuard` (role-based navigation convenience, not security) |
| `src/context/` | `AuthContext` — the one authentication state mechanism |
| `src/services/` | `apiClient.js` (the one Axios instance), `authService.js` (login/signup/me), `letterService.js` (Phase 5C), `categoryService.js`/`classificationService.js` (Phase 5C: thin, SYSTEM_ADMIN-only `list()`-only reference-data wrappers; extended to the full create/read/update/activate/deactivate set in Phase 5H.1), `departmentService.js` (Phase 5C reference-data + Phase 5D full CRUD/lifecycle; `list()` readable by any role since Phase 5H), `adminService.js`/`userService.js` (Phase 5D), `documentService.js`/`notificationService.js` (Phase 5E), `designationService.js` (Phase 5H), `tokenStorage.js` (isolated token access), `errorNormalization.js` — no `dashboardService.js` exists; the Dashboard (Phase 5F) composes these same modules directly |
| `src/navigation/` | `navigationConfig.js` — role → nav item mapping, data only; `Dashboard` is the first entry for every role since Phase 5F, `Designations` is a SYSTEM_ADMIN-only entry since Phase 5H, otherwise unchanged since Phase 5A — its Departments/Administrators/Users/Notifications/Categories/Classifications entries already pointed at the eventual routes (the Categories/Classifications routes rendered `PlaceholderPage` until Phase 5H.1 wired in real pages) |
| `src/layouts/` | `AppShell`/`Sidebar`/`Topbar` — the authenticated app's chrome; `Topbar` renders `NotificationBell` since Phase 5E; visually redesigned in Phase 5I.2 (collapsible `Sidebar` with a mobile-drawer mode, a `Topbar` hamburger toggle, the AJ-OVA Labs footer rendered once in `AppShell`) — `navigationConfig.js`'s own role-derived data is unchanged; `Sidebar`'s nav "icons" were 3-letter monograms until Phase 5I.6A replaced them with small inline SVG icons |
| `src/pages/` | `LoginPage`/`SignupPage` (auth/account UX, Phase 5B), `LetterListPage`/`LetterFormPage`/`LetterDetailPage` (Letter registry, Phase 5C; `LetterDetailPage` gained a real Documents section in Phase 5E; `LetterFormPage` gained Source Department/Designation selectors in Phase 5H; all three visually transformed in Phase 5I.4B — a registry header, and `LetterDetailPage` recomposed into a four-section record dossier — with every field/payload/role branch unchanged), `DepartmentListPage`/`DepartmentCreatePage`/`DepartmentDetailPage`/`AdminListPage`/`AdminAuthorizePage`/`AdminDetailPage`/`UserListPage`/`UserAuthorizePage`/`UserAuthorizationsPage`/`UserDetailPage` (administration, Phase 5D; all ten gained the shared console eyebrow/accent-line header in Phase 5I.4C, via `AdminPages.module.css`, with every payload/role branch unchanged), `NotificationsPage` (Phase 5E, at `/app/notifications`), `DashboardPage` (Phase 5F, at `/app/dashboard`; visually recomposed into a header/metrics/activity/actions layout in Phase 5I.4A, with every metric and fetch unchanged), `DesignationListPage` (Phase 5H, at `/app/system/designations`; gained the same console header in Phase 5I.4C), `CategoryListPage`/`CategoryCreatePage`/`CategoryDetailPage`/`ClassificationListPage`/`ClassificationCreatePage`/`ClassificationDetailPage` (Phase 5H.1, at `/app/system/categories*`/`/app/system/classifications*`; all six gained the same console header in Phase 5I.4C), `RootRedirect`, `PlaceholderPage` (every remaining unbuilt business feature screen renders this generic placeholder — still used for `/app/documents`) |
| `src/components/` | `LoadingState`/`ErrorState`/`EmptyState` — reusable primitives (`EmptyState` gained a small CSS-only document glyph in Phase 5I.3); `BootScreen` (Phase 5I.5) — the application's one-time boot/loading identity, rendered by `App.jsx` only, not a general-purpose loading primitive (`LoadingState` remains that); `PendingApprovalNotice`/`DeactivatedAccountNotice` — account-state notices; `LetterTable`/`LetterFilters`/`Pagination`/`ArchiveConfirmDialog` — Letter registry components (Phase 5C; table/button styling consolidated onto shared primitives in Phase 5I.3; `LetterTable` gained a row accent bar and `LetterFilters` was recomposed into a grouped "Registry Search" console in Phase 5I.4B, with every filter/sort/column behavior unchanged); `StatusBadge` (Phase 5C, extended in Phase 5D, gained an `aria-hidden` shape-per-tone indicator in Phase 5I.3); `ConfirmDialog`/`AdminTransferDialog`/`DepartmentSelector`/`DepartmentForm`/`DepartmentTable`/`AdminTable`/`UserTable`/`AuthorizationTable` — administration components (Phase 5D, `DepartmentSelector` reused for Source Department in Phase 5H; `ConfirmDialog`/`ArchiveConfirmDialog` gained a shared entrance animation in Phase 5I.3; `AdminTransferDialog` gained real visual separation between current-department/target-department/consequences in Phase 5I.4C, with its required wording confirmed byte-for-byte unchanged; every admin table shares one row-accent-bar-on-hover via `DataTable.module.css`, also Phase 5I.4C); `DocumentUploadForm`/`DocumentList`/`NotificationBell`/`NotificationPanel`/`NotificationItem` — documents/notifications components (Phase 5E; `NotificationItem`'s unread state gained a left accent bar in Phase 5I.3; `NotificationBell`'s icon was a raw emoji until Phase 5I.6 replaced it with a CSS-only outline, its only change since Phase 5E); `SummaryCard`/`RecentLetters`/`QuickActions` — dashboard components (Phase 5F; unified onto one accent-bar/corner-mark card treatment, existing accent-bar-on-hover row language, and decorative-arrow tiles respectively in Phase 5I.4A); `DesignationTable` — Designation management component (Phase 5H); `CategoryForm`/`CategoryTable`/`ClassificationForm`/`ClassificationTable` — Category/Classification management components (Phase 5H.1); all of the above tables gained the same Phase 5I.4C row-accent-bar-on-hover via `DataTable.module.css` |
| `src/styles/` | `tokens.css` (design tokens — extended in Phase 5I.1 with text-secondary/border-subtle/surface-elevated/accent/info/success-bg/highlight-bg color tokens and a 5-value motion-timing scale, additive only, every Phase 5A token unchanged), `global.css` (minimal reset, `.sr-only` utility since Phase 5D; Phase 5I.1 added a static atmospheric background wash, a global reduced-motion safety net, a narrow global interaction-transition rule, and a strengthened `:focus-visible` treatment; Phase 5I.3 added the shared input/select/textarea/checkbox base every form now inherits with zero markup change), `primitives.module.css` (Phase 5I.3 — shared button/table/dialog base classes every consuming CSS Module reaches via `composes`, not a new component) |
| `src/test/` | `setup.js` — Vitest/Testing-Library wiring, shared by every test file |
| `src/utils/` | `formValidation.js` — lightweight, dependency-free form validation (auth forms, `validateLetterForm` since Phase 5C — extended in Phase 5H with an `{isEdit}` option and Source Department/Designation required-on-create checks, `validateDepartmentForm`/`validateAdminAuthorizeForm`/`validateUserAuthorizeForm` since Phase 5D, `validateDocumentFile` since Phase 5E, `validateDesignationForm` since Phase 5H, `validateCategoryForm`/`validateClassificationForm` since Phase 5H.1); `statusLabels.js` (Phase 5D) — human-readable labels for the raw enum values `StatusBadge` renders |
| `src/assets/`, `src/hooks/`, `src/constants/` | Still mostly placeholders (`constants/app.js` has real content); populated as feature work needs them |

## Conventions

* Components never call Axios directly — all HTTP goes through
  `src/services/apiClient.js` and the per-resource service modules built
  on top of it (`authService.js` today; one per backend resource as
  feature work adds them).
* Only `VITE_`-prefixed variables reach the browser. Never put a secret
  in one.
* `@` resolves to `src/` (configured in `vite.config.js`).
* Component-scoped styles use CSS Modules (`*.module.css`, native to
  Vite — no new dependency); shared values come from `src/styles/tokens.css`
  via `var(--token-name)`. No CSS/UI framework is installed — see
  `docs/architecture/frontend.md` §26 for why.
* Every backend response shape is trusted as the source of truth for
  authorization (role/department/status) — the frontend never computes
  or caches a permission decision independently. See
  `docs/architecture/frontend.md` §22/§28.

## Testing

Vitest + React Testing Library (`npm run test`). 354 tests across 48
files, run 3 consecutive times with identical results. Auth/foundation (unchanged since Phase 5B):
`services/errorNormalization.test.js`, `navigation/navigationConfig.test.js`,
`routes/ProtectedRoute.test.jsx`, `routes/routing.test.jsx`,
`context/AuthContext.test.jsx`, `pages/LoginPage.test.jsx`,
`pages/SignupPage.test.jsx`. Letter registry (Phase 5C; `LetterDetailPage.test.jsx`
gained a Documents-integration `describe` block in Phase 5E):
`components/LetterTable.test.jsx`, `components/Pagination.test.jsx`,
`pages/LetterListPage.test.jsx`, `pages/LetterDetailPage.test.jsx`,
`pages/LetterFormPage.test.jsx`. `utils/formValidation.test.js` now
covers all seven validators across Phase 5B/5C/5D/5E. Administration
(Phase 5D): `components/ConfirmDialog.test.jsx` (dialog
accessibility, focus, Escape, backdrop click, Tab-trap),
`routes/RoleGuard.test.jsx` (both usage modes, including the new
`<Outlet/>` layout-route behavior), `pages/DepartmentListPage.test.jsx`/
`DepartmentCreatePage.test.jsx`/`DepartmentDetailPage.test.jsx`,
`pages/AdminListPage.test.jsx`/`AdminAuthorizePage.test.jsx`/
`AdminDetailPage.test.jsx` (including the transfer flow, an
approval-race 409, and a transfer-destination-not-active 409),
`pages/UserListPage.test.jsx`/`UserAuthorizePage.test.jsx`/
`UserAuthorizationsPage.test.jsx`/`UserDetailPage.test.jsx` (including
the default-`ACTIVE`-filter behavior, a used-authorization 409 race, and
the 403-department-phrasing test). Documents & Notifications (Phase
5E, new): `components/DocumentUploadForm.test.jsx`,
`components/DocumentList.test.jsx`, `components/NotificationItem.test.jsx`,
`components/NotificationBell.test.jsx` (fake-timer-driven polling/pause
tests), `components/NotificationPanel.test.jsx`,
`pages/NotificationsPage.test.jsx`, `layouts/Topbar.test.jsx` (new file
— no such test previously existed) — including coverage that mark-read
never fires on Letter-link navigation, that no `is_read`/recipient
parameter is ever sent, and that a notification pointing at an
inaccessible Letter renders the ordinary generic 404. Dashboard (Phase
5F, new): `components/SummaryCard.test.jsx`, `components/
RecentLetters.test.jsx`, `components/QuickActions.test.jsx`,
`pages/DashboardPage.test.jsx` (11 tests — including per-role card/
quick-action rendering with explicit assertions that the *wrong* role's
cards/requests never fire, exact request-parameter shape proving no
`department_id` or oversized `page_size` is ever sent, independent
partial-widget failure, and that a failed card shows "Unavailable"
rather than a fabricated `0`); `navigation/navigationConfig.test.js`
extended for the new `Dashboard` entry. Source Department & Designation
(Phase 5H, new): `pages/DesignationListPage.test.jsx` (create form,
duplicate-name 409, Activate with no confirmation vs. Deactivate with a
confirmation dialog stating existing Letters are unaffected, status
filter, no delete action of any kind); `pages/LetterFormPage.test.jsx`
extended significantly (Source Department/Designation auto-fill
`source_name`/`sender_designation`, active-only options on create vs.
the complete active+inactive list on edit so an already-assigned,
now-inactive value still renders, required-on-create-only validation
via `formValidation.js`'s new `{isEdit}` option, a zero-active-
designations message with submission still correctly blocked, no
free-text Source input remains); `utils/formValidation.test.js`
extended for `validateDesignationForm` and the new `isEdit` behavior;
`navigation/navigationConfig.test.js` extended for the new
`Designations` entry. Category & Classification management (Phase
5H.1, new): `pages/CategoryListPage.test.jsx`/`CategoryCreatePage.test.jsx`/
`CategoryDetailPage.test.jsx` and the Classification equivalents (list/
create/edit/activate/Deactivate-with-confirmation, a duplicate-name 409,
an exact create-payload-shape assertion, and an explicit "never renders
a delete action" test on every page); Classification's tests
additionally cover the `restricts_access` checkbox defaulting to
`false`, sending `true` when checked, and rendering as plain "Yes"/"No"
text; `utils/formValidation.test.js` extended for
`validateCategoryForm`/`validateClassificationForm`. App Shell &
Navigation (Phase 5I.2, new): `layouts/Sidebar.test.jsx` (role-derived
navigation rendering, `aria-current` on the active route, collapse
toggle `aria-expanded`, links remain accessible while collapsed, the
mobile-drawer dialog/backdrop/Escape/focus-on-open behavior) and
`layouts/AppShell.test.jsx` (Outlet content still renders, the footer
renders exactly once, opening/closing the drawer end-to-end via the
Topbar's own hamburger button, including closing automatically after a
navigation link is selected). Core UI Primitives (Phase 5I.3, new):
`components/StatusBadge.test.jsx` (every mapped status value renders
its label as real text, the raw-value fallback, an unknown value
renders neutrally rather than throwing, and the new shape indicator is
`aria-hidden` and never the accessible content) and
`components/EmptyState.test.jsx` (the given message and the default
fallback both render, and the new glyph is decorative only) — neither
component had a dedicated test file before this phase. Dashboard Visual
Transformation (Phase 5I.4A, new): `pages/DashboardPage.test.jsx`
extended with a test that the new header subtitle renders and that no
fabricated system-health/security phrase (`/system secure|all systems
operational|encrypted|live monitoring/i`) ever appears in the rendered
page, plus a "N shown" Recent-Letters-count test and a Quick-Actions
href regression check; `components/SummaryCard.test.jsx` extended for
the new decorative corner mark being `aria-hidden`; `components/
QuickActions.test.jsx` extended for the decorative arrow being excluded
from each link's accessible name (`toHaveAccessibleName`). Every
pre-existing Dashboard assertion (wrong-role requests never fire,
independent widget failure, no fabricated zero, exact Letter-link
hrefs) passed unmodified. Letter Registry Visual
Transformation (Phase 5I.4B): no test file needed a change — the phase
was purely presentational, and all 48 existing assertions across
`pages/LetterListPage.test.jsx`, `pages/LetterFormPage.test.jsx`,
`pages/LetterDetailPage.test.jsx`, and `components/LetterTable.test.jsx`
(URL sync, sorting, filter apply/clear, role-specific rendering, Source
Department/Designation auto-fill, 422/409/403 handling, document
integration, archive confirmation wording) passed unmodified,
confirming the recomposition changed nothing behavioral. Administration
Visual Transformation (Phase 5I.4C): no test file needed a change —
a dedicated pass of all 17 Administration test files (107 tests) was
run and confirmed green, including the Admin Transfer flow's exact
"does not move or reassign any historical record" text assertion,
System-Admin-protection 404 phrasing, the 403-department-inactive test,
and every activate/deactivate/approve/revoke confirmation test.
Documents & Notifications Visual Transformation (Phase 5I.4D): no test
file needed a change — a dedicated pass of the 7 directly-relevant
test files (63 tests: `LetterDetailPage`, `DocumentList`,
`DocumentUploadForm`, `NotificationBell`, `NotificationPanel`,
`NotificationItem`, `NotificationsPage`) was run and confirmed green,
including the exact `Download scan.pdf` button name, the accessible
"Upload document" label, the exact `{ page: 1, page_size: 10 }` panel
request params, and the exact `{ page: 1 }` notification-page request
params (never an `is_read` filter). Authentication Visual
Transformation (Phase 5I.4E): no test file needed a change — a
dedicated pass of the 4 directly-relevant test files (26 tests:
`LoginPage`, `SignupPage`, `AuthContext`, `routing`) was run and
confirmed green, including the exact generic-credentials/pending/
deactivated/network-error assertions, the "never sends a role,
department, or status field" payload-shape assertion, and
`routing.test.jsx`'s `getByRole('heading', { name: /sign in/i })`
assertion after logout. Boot & Loading Experience (Phase 5I.5): 2 new
test files added. `BootScreen.test.jsx` (6 tests) covers the truthful
accessible status text, a custom-label case, the absence of any
unverified security/monitoring claim, the rendered LRS identity text,
and that the decorative glyph contributes no text of its own.
`App.test.jsx` (3 tests) covers the boot-lifecycle gate against a
lightweight `createMemoryRouter` stand-in for the real route tree — no
test depends on a fixed timeout or animation duration; the boot screen
appears only for a genuinely pending `getCurrentUser` call and
disappears once that promise resolves. Final Polish, Manual E2E &
Handover Audit (Phase 5I.6): no test file needed a change — the one
code fix this phase made (`NotificationBell`'s icon) needed none,
confirmed by `NotificationBell.test.jsx`'s existing 9 tests passing
unmodified (none of them ever asserted on the icon's content). Sidebar
Icon Identity Correction (Phase 5I.6A): no existing test needed a
change — none of `Sidebar.test.jsx`'s assertions ever queried the
glyph's own content, only each link's accessible name; one new
regression test was added confirming every navigation link renders a
decorative, `aria-hidden` `<svg>` icon. The API
layer is
mocked in every test; none of these tests requires a running backend.

Vitest's per-test timeout is raised to 10 seconds (`vite.config.js`,
Phase 5F) — the 5-second default started intermittently missing on
`LetterFormPage.test.jsx`'s character-by-character `userEvent.type`
interactions purely from worker-thread contention once the suite grew
past ~30 files (confirmed non-deterministic in isolation vs. full-suite
runs, not a logic defect); this raises headroom for every test rather
than special-casing one file.

## Known limitations

* **The system intentionally starts with zero Designations** (Phase 5H,
  by explicit business decision, not a gap) — no list was invented; a
  SYSTEM_ADMIN must add the organization's real designations at
  `/app/system/designations` before any Letter can be recorded, since
  Designation is required client-side on create. See
  `docs/architecture/source-designation.md` §16/§22.
* **No "external, non-departmental source" fallback** (Phase 5H,
  `PENDING BUSINESS CLARIFICATION`) — the Letter form's Source field is
  now exclusively a Department picker; a letter genuinely originating
  from an organization with no LRS department record has no way to be
  represented via this form (the backend's own `source_department_id`
  remains optional and `source_name` remains free text at the API
  level — this is a frontend UX choice, not a backend restriction). See
  `docs/architecture/source-designation.md` §4/§21.
* **No dedicated Designation edit/detail page** (Phase 5H, deliberate
  scope) — `PATCH /designations/{id}` exists on the backend, but only
  create/list/activate/deactivate have frontend UI; renaming a
  designation currently has no screen. See
  `docs/architecture/source-designation.md` §12/§22.
* **No dashboard chart, trend, or breakdown of any kind** (Phase 5F, a
  CONFIRMED backend-contract limitation) — no aggregate/group-by
  endpoint exists for Letters, and no audit read API exists at all;
  every such metric remained `PENDING BACKEND API` in the review and
  none was built. See `docs/architecture/dashboard.md` §12/§32.
* **No dashboard filter controls** (date range, category,
  classification, department) — left `PENDING BUSINESS CLARIFICATION`
  in the review as unconfirmed wants; none was built. See
  `docs/architecture/dashboard.md` §18/§32.
* **Administration dashboard cards cost a full-object list fetch**
  (Phase 5F, restating the same Phase 5D limitation) — Departments/
  Admins/Users have no pagination or database `COUNT`; acceptable at
  current scale. See `docs/architecture/dashboard.md` §9/§32.
* **60-second unread-count polling interval** (Phase 5E) —
  `PROVISIONAL`, centralized as `POLL_INTERVAL_MS` in
  `NotificationBell.jsx`; not backed by a confirmed business
  requirement. See `docs/architecture/document-notification-ui.md`
  §11/§27.
* **Explicit-only mark-read behavior** (Phase 5E) — implemented per an
  explicit override in the implementation brief; the underlying
  business question (mark-read-on-navigate vs. explicit-only) remains
  open. See `docs/architecture/document-notification-ui.md` §23/§27.
* **No pagination on the Document list** (Phase 5E, a CONFIRMED
  backend-contract limitation) — `GET /letters/{id}/documents` returns
  the complete result set, unlike the notification list. See
  `docs/architecture/document-notification-ui.md` §1.1/§27.
* **No `is_read` filter on the Notification list** (Phase 5E, a
  CONFIRMED backend-contract limitation) — confirmed absent; not
  invented. See `docs/architecture/document-notification-ui.md`
  §2.2/§27.
* **No document delete/replace/archive** (Phase 5E, a CONFIRMED
  backend-contract limitation) — no such endpoint exists; "replacement"
  is uploading again, leaving the prior document untouched. See
  `docs/architecture/document-notification-ui.md` §5/§27.
* **No pagination, search, or sort on Departments/Admins/Users/User-
  authorizations** (Phase 5D, a CONFIRMED backend-contract limitation)
  — unlike `GET /letters`, none of the four resources' list endpoints
  support it; every list page renders the complete matching result set
  for its active filter. See `docs/architecture/administration-ui.md`
  §11/§22.
* **Admin-purpose authorizations cannot be revoked through this
  frontend** (Phase 5D, a CONFIRMED backend-contract gap) — no
  equivalent of `DELETE /users/authorizations/{id}` exists for them.
  See `docs/architecture/administration-ui.md` §8.1/§22.
* **No department/admin/user counts appear anywhere** (Phase 5D) —
  `DepartmentResponse` has no such field. See
  `docs/architecture/administration-ui.md` §7/§22.
* **USER/ADMIN cannot assign or view a resolved category/classification
  for a Letter** (Phase 5C, a CONFIRMED backend-contract gap, unchanged
  by Phase 5H.1) — `GET /api/v1/categories`/`/classifications` are
  `require_system_admin`-only, but `POST /api/v1/letters` structurally
  excludes SYSTEM_ADMIN. The two roles that actually record/edit letters
  have no legitimate way to load the option lists; only SYSTEM_ADMIN
  (via Edit) can set either field. Phase 5H.1 built the SYSTEM_ADMIN
  management screens for Category/Classification themselves; it did not
  touch this separate `LetterFormPage.jsx` gating gap, per its own scope
  brief. See `docs/architecture/frontend.md` §36.
* **A category/classification cannot be cleared back to unassigned once
  set** — `LetterUpdate`'s "omitted field means unchanged" semantics
  make an explicit `null` indistinguishable from omitting the field;
  this form never attempts it.
* `react-router-dom@^6.24.0` and the `esbuild`/`vite` toolchain both have
  `npm audit`-reported advisories with no non-breaking fix available in
  their currently pinned major versions (a v7 React Router upgrade and a
  Vite 8 upgrade would each be a breaking stack change, out of scope for
  this phase — "use the existing stack, do not replace it"). Documented
  here rather than silently upgraded or silently ignored.
* React Router logs two harmless "future flag" deprecation warnings
  during tests (`v7_startTransition`, `v7_relativeSplatPath`) — informational
  only, not a functional issue; not addressed this phase.

The structure anticipates the remaining feature set (dashboard
analytics, reporting, an audit read API, a Designation edit/detail
page) — see `docs/architecture/frontend.md`,
`docs/architecture/document-notification-ui.md`, and
`docs/architecture/dashboard.md` for the complete design and
`docs/PROJECT_STATUS.md` for what's built versus still pending.
