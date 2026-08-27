# Letter Registry System (LRS)

**A Production of AJ-Labs**

> **Current status: Phase 5I.6A — Sidebar icon identity correction
> complete (the 3-letter navigation monograms `DAS`/`LET`/`DOC`/etc.,
> a Phase 5I.2 placeholder that read as text labels rather than icons,
> replaced with 9 small inline-SVG geometric icons — grid/envelope/
> document-stack/bell/building/shield/badge/folder/layers — plus a
> person icon for the `Users` item; all keyed off the one existing
> active-state color mechanism, `navigationConfig.js`/routes/labels/
> permissions untouched). Phase 5I.6 — Final Polish, Manual E2E & Handover
> Audit complete. The closing audit across all nine prior visual phases
> (5I.1–5I.5): a full documentation re-read, a full screen inventory,
> and a codebase-wide search across visual consistency, branding, boot
> experience, responsive behavior, accessibility, motion, functional
> coherence, and the security boundary. One genuine defect found and
> fixed — `NotificationBell`'s 🔔 emoji (the one full-color, OS-rendered
> pictograph anywhere in the app) replaced with a CSS-only bell outline
> matching the restrained geometric icon language everywhere else, with
> zero behavior change. Everything else audited was either already
> consistent or a documented, intentional difference (recorded in
> `docs/architecture/ui-design-system.md`'s own "Phase 5I.6" section).
> Manual browser verification was not performed — no browser-automation
> tool is available in this environment. The Phase 5I visual
> architecture (5I.1–5I.6) is now considered closed. Phase 5I.5 Boot &
> Loading Experience implemented
> (a new `BootScreen` — a CSS-only "LRS Registry Glyph" nested-square
> mark with a sequential-tick "registry scan" animation, plus a
> truthful accessible status — gated at `App.jsx` using `AuthContext`'s
> own existing `status === 'loading'` window, never a duplicated timer;
> `AuthContext.jsx` untouched); Phase 5I.4E Authentication entrance visually
> transformed (Login/Signup share one static brand identity —
> the Sidebar's nested-square mark, `APP_NAME`, and the existing
> `PRODUCTION_CREDIT` line — with a technical eyebrow distinguishing
> the two forms, the submit button finally composed onto the shared
> button primitives, and both account-state notices gaining a small
> color-coded marker; no form field, validation rule, or auth behavior
> changed); Phase 5I.4D Documents & Notifications visually
> transformed (a real, non-fabricated attachment count and a
> percentage-bound upload progress bar in the Letter dossier's
> Documents section; an "Operational Signals" eyebrow, a static unread
> dot, and a chip-count header for the Notification panel and full
> notification page); Phase 5I.4C Administration workspace visually
> transformed (a console-wide header/table/button language across
> Departments/Administrators/Users/Authorizations/Designations/
> Categories/Classifications, achieved mainly through two shared files;
> Phase 5I.4B Letter Registry visually transformed
> (registry header, a "Registry Search" filter console, an accent-barred
> table, a record-dossier detail page, no field/filter/API changed);
> Phase 5I.4A Dashboard visually transformed; Phase 5I.3 Core UI Primitives & Interaction System
> implemented; Phase 5I.2 App Shell &
> Navigation visual implementation complete; Phase 5I.1 Global Visual
> Foundation implemented; Phase 5I Futuristic UI / Visual Architecture &
> Design System review complete; Phase 5H.1 Category &
> Classification Admin UI completed; Phase 5H Source Department &
> Designation Master Data implemented; Phase 5G Backend Dashboard
> Aggregation & Analytics
> API review complete; Phase 5F Dashboard & Operational Overview UI
> implemented; Phase 5E Documents & Notifications UI implemented; Phase
> 5D Administration & Account Management UI implemented; Phase 5C Core
> Registry UI implemented; Phase 5B Authentication & Account UX
> implemented; Phase 5A Frontend Foundation implemented; Phase 5
> architecture/UX review complete; Phase 4E Operational Activity,
> Notifications & Audit implemented; Phase 3B complete).**
> Local email/password login, JWT access tokens, role-based access
> control, System-Admin-controlled department management,
> System-Admin-controlled Admin management, and Admin-controlled User
> management are implemented and validated against a real local
> PostgreSQL instance — see `docs/architecture/authentication.md`,
> `docs/architecture/authorization.md`,
> `docs/architecture/department-management.md`,
> `docs/architecture/admin-management.md`, and
> `docs/architecture/user-management.md`. Phase 4B implemented the
> product owner's finalized Letter Registry decisions (recipient/source
> department separation, structured sender details, a required reference
> number, three Categories, a classified-access boundary), and a
> pre-commit hardening pass corrected one unconfirmed assumption
> (reference-number uniqueness — the scope was never confirmed, so the
> constraint was removed). Phase 4C then added pagination, explicit
> whitelisted sorting, and seven text-search filters to
> `GET /api/v1/letters` — but only *after* fixing a real leakage risk its
> own architecture review found first: the letter list used to filter
> classified records out in Python after fetching them, which would have
> let a paginated `total` leak how many inaccessible records existed. That
> fix now runs at the database query level, verified by live testing
> before any pagination code was added. Phase 4D first reviewed, then
> implemented, document upload/download for `LetterDocument`:
> `POST`/`GET /api/v1/letters/{letter_id}/documents` and
> `GET .../{document_id}` (upload, list, download), with a
> server-generated `<letter_uuid>/<document_uuid>.<ext>` storage path
> that never trusts client input, layered file-type/size validation
> (extension allowlist, then an authoritative magic-byte content
> signature — client-supplied `Content-Type` is never trusted), and an
> authorization chain that reuses `assert_letter_access`/
> `LetterService.get_letter` rather than a parallel document-level check
> (so classified-letter protection extends to its documents
> automatically). No schema change was needed. There is still no
> document deletion endpoint of any kind — a deliberate scope decision,
> not a gap — see `docs/architecture/document-management.md` §14/§33.
> Phase 4E then implemented audit generation and in-system
> notifications on top of its own architecture review: `AuditLog`
> (append-only — no update/delete path exists anywhere) now records
> Letter/Document/User/Admin/Department/Category/Classification/
> Authorization lifecycle events with targeted old/new field pairs, never
> a full row snapshot, and is mandatory — a write failure fails the
> whole operation, in the same transaction. `Notification` now generates
> for the one confirmed V1 trigger, a letter being registered (recipient
> strategy: the recipient department's Admins, an explicit, provisional
> default), best-effort via a database `SAVEPOINT` so a failure there
> can never block the letter itself, with a deliberately generic
> `message` (no Letter content) so a later classification change can't
> retroactively leak what was already sent.
> `GET/PATCH /api/v1/notifications*` lets a user read and mark-read only
> their own notifications. No schema change was needed. See
> `docs/architecture/audit-notifications.md`. Phase 5 then reviewed (but
> did **not** implement) the frontend: the existing skeleton
> (React 18 + Vite + React Router + Axios, none of it wired up yet) was
> inspected fresh, all 42 real backend endpoints were mapped to screens
> by role, and the review designed authentication UX, role-aware
> navigation, the Letter registry/search/document/notification UX, and
> — critically — how the frontend must render `404` identically for a
> nonexistent and an inaccessible-classified Letter, never inventing its
> own filtering on top of what the backend already returns — see
> `docs/architecture/frontend.md`. Phase 5A then implemented the
> frontend *foundation* the review designed — not any feature screen:
> routing (React Router, finally wired up), a single `AuthContext`
> restoring a session from `GET /auth/me` before any protected route
> renders (no authentication flicker), one centralized Axios client
> (auth header, two-shaped error normalization, a 401 handler that
> never fires on the login call itself), `ProtectedRoute`/`RoleGuard`,
> role-derived navigation, the `AppShell`/`Sidebar`/`Topbar` chrome, a
> small design-token set (no UI framework added), an accessibility
> baseline, and a Vitest + React Testing Library test setup (17 tests —
> none existed before). Phase 5B then turned that foundation into the
> complete V1 authentication/account experience: production Login/Signup
> forms with client-side validation and full `aria-invalid`/
> `aria-describedby` accessibility wiring; dedicated, reusable
> pending-approval and deactivated-account notices that state only what
> the backend confirms (no invented approval timeline or administrator
> contact); session restoration that now distinguishes a genuine token
> rejection (clears the token) from a network failure (keeps the token,
> shows a retry banner, never silently treats an unreachable server as
> "authenticated"); the same already-authenticated → redirect-into-app
> guard on both Login and Signup; and a test suite grown from 17 to 44
> tests. Logout remains purely client-side token removal — there is no
> server-side revocation endpoint, an accepted V1 limitation, not a
> defect. Phase 5C then turned the `/app/letters` placeholder into the
> complete V1 Letter registry: list/search (seven text filters, exact
> filters, an inclusive date range), sort (all four backend-whitelisted
> fields, accessible headers), pagination driven entirely by the
> backend's own totals, create, view, edit, and archive (a non-
> destructive status transition, worded and confirmed accordingly). A
> real, confirmed backend-contract gap was found and resolved rather
> than routed around: `GET /api/v1/categories`/`/classifications`/
> `/departments` are all SYSTEM_ADMIN-only, but `POST /api/v1/letters`
> structurally excludes SYSTEM_ADMIN — so category/classification
> selection is unavailable on Create for any role, and available on Edit
> only for SYSTEM_ADMIN, with nothing hardcoded as a workaround. The
> classified-Letter discipline Phase 5's review established — render
> `items`/`total` exactly as returned, treat every `404` identically —
> was verified directly against this implementation. Test suite grown
> from 44 to 84 tests. Phase 5D then first reviewed, then implemented,
> the Department/Admin/User management frontend: every Department/
> Admin/User/UserAuthorization endpoint, schema, service, repository,
> and model was re-read fresh, correcting two inaccurate assumptions in
> the phase's own brief along the way (the frontend did not already have
> Document/Notification UI; `AuthorizationStatus` is `ACTIVE`/`USED`/
> `REVOKED`, not `PENDING`/`EXPIRED`, and its `expires_at` field is
> never actually set by any code path). `/app/system/departments`,
> `/app/system/admins`, and `/app/admin/users` are now a complete
> Department/Administrator/User management UI — list/create/detail,
> Admin/User authorization workflows, approve/deactivate/reactivate
> lifecycle actions (System Admin protection and Admin self-targeting
> prevention are both structural — no endpoint can ever resolve a
> SYSTEM_ADMIN id or an Admin's own id, so no frontend check was needed),
> and Admin department transfer, which states verbatim that historical
> Letters are never reassigned. The backend's own read/lock-down vs.
> state-elevating asymmetry is preserved, not flattened into one generic
> "Admin manages Users" treatment — a `403` on User Approve/Reactivate is
> phrased around the *Admin's own* department, never the target account.
> Unlike Letters, none of Departments/Admins/Users/User-authorizations
> support pagination, search, or sort — every list renders the complete
> backend result set for its filter, exactly as confirmed, nothing
> invented. Test suite grown from 84 to 159 tests. See
> `docs/architecture/administration-ui.md`. Phase 5E then first
> reviewed, then implemented, the Documents & Notifications frontend:
> every `documents.py`/`notifications.py` endpoint, service,
> repository, and schema was re-read fresh and confirmed unchanged
> since Phase 4D/4E — confirming precisely *why* a plain `<a href>`
> cannot download a document (a Bearer token is required, and
> `Content-Disposition: attachment` is set automatically by the
> backend's own `FileResponse` call), that no document replace/delete
> endpoint exists or is planned ("replacement" is simply uploading
> again), and that the one generated notification message is a fixed,
> non-sensitive template safe to render as plain text. A real,
> previously-undocumented interaction was found: a notification's
> Letter link can still 404 if the recipient's own access changed since
> the notification was generated (e.g. an Admin department transfer) —
> documented as expected, non-distinguishing 404 behavior, not a bug.
> `LetterDetailPage` now has a real Documents section
> (upload/list/download, no delete/replace action, because none
> exists); `Topbar` now has a `NotificationBell` polling
> `GET /notifications/unread-count` only, every 60 seconds
> (`PROVISIONAL`); `/app/notifications` is a real paginated page.
> Mark-read is explicit-button-only — clicking a notification's Letter
> link never marks it read, an explicit override of this review's own
> provisional lean. No frontend authorization rule was added anywhere;
> a `404` renders identically whether a document is nonexistent or its
> parent Letter is classified-inaccessible. Test suite grown from 159
> to 225 tests, run 3 consecutive times with identical results. See
> `docs/architecture/document-notification-ui.md` §27 for the full
> implementation record. Phase 5F then first reviewed, then
> implemented, the Dashboard & Operational Overview frontend: every
> business endpoint (twelve mounted routers) was re-read fresh,
> confirming no dashboard/summary/aggregate/audit-read endpoint exists
> anywhere, that `GET /letters`'s `total` is a real, already department/
> classified-visibility-scoped SQL `COUNT` (so a Letter count is cheap
> and needs no frontend filtering), and that
> `GET /departments`/`/admins`/`/users`/`/categories`/`/classifications`
> have no pagination at all — each returns its complete matching result
> set, with `total` just `len()` in Python. A full metric inventory
> found every current-operational-state figure (letter counts, pending
> approvals, active departments/admins/users, unread notifications)
> already available from existing, correctly-isolated requests, while
> every historical/trend/analytical metric requires a new backend
> aggregate endpoint or the audit read API that doesn't yet exist —
> supporting, without confirming as a business requirement, an
> operational-only V1. `/app/dashboard` now renders one role-aware
> `DashboardPage`: Total/Active/Archived Letters and Unread
> Notifications for every role, Active Departments + Pending Admin
> Approvals for SYSTEM_ADMIN, Active Users + Pending User Approvals for
> ADMIN, a 5-item Recent Letters list, and role-scoped Quick Actions
> linking only to already-existing screens. No chart, trend, filter
> control, or document metric was built. No charting library is
> installed and none was added; the existing `NotificationBell` polling
> is untouched. Test suite grown to 249 tests, run 3 consecutive times
> with identical results. See `docs/architecture/dashboard.md` §32 for
> the full implementation record. Phase 5G then reviewed (but did
> **not** implement) whether the backend should provide additional
> aggregate/analytics APIs: the full backend layering, database
> indexes, and `list_letters`'s exact query construction were re-read
> fresh, confirming the existing `letter_visibility_filter`/department-
> derivation authorization logic can be reused directly for any future
> Letter aggregate (no new predicate needed), that every column a
> plausible aggregate would group or filter by is already indexed (zero
> new indexes recommended), and that `AuditLog` has no department
> column at all (audit analytics deferred entirely to a future, separate
> phase). A full metric inventory found **no metric that both needs a
> new backend endpoint and has confirmed business value** — every
> current-operational figure is already served by Phase 5F's own
> dashboard, and every analytical one is gated behind an unconfirmed
> want. A complete, ready-to-build design
> (`GET /api/v1/letters/aggregate`) is documented but explicitly not
> implemented or authorized. See
> `docs/architecture/dashboard-analytics-api.md` for the full review.
> Phase 5H then first reviewed, then implemented, two supervisor-
> requested changes from a live demonstration ahead of handover: making
> "Source" selectable from the Department list, and "Designation" a
> SYSTEM_ADMIN-managed dropdown. Two findings drove the design: first,
> `source_department_id` **already existed**, fully wired, on every
> Letter schema, with existing backend validation — it was simply never
> given a frontend control, so making Source a dropdown was mostly a
> frontend task. Second, `GET /api/v1/departments` was
> `require_system_admin`-only — the exact access gap already documented
> for Category/Classification would have silently blocked both Source
> Department *and* the new Designation dropdown for USER/ADMIN, the
> only roles that ever record a Letter — fixed with a one-line
> dependency relaxation (read-only; every write endpoint stays
> SYSTEM_ADMIN-only). `source_name` remains required and is now
> auto-filled from the selected department (the existing, already-
> confirmed product decision is not reversed); a new `Designation`
> master-data resource (model/repository/service/endpoints, plus a
> minimal SYSTEM_ADMIN management page at `/app/system/designations`)
> mirrors `Category`/`Classification` almost exactly, with the identical
> list-endpoint access relaxation applied. Historical integrity is
> solved the same way `source_department_id`/`source_name` already
> coexist: a new, nullable `designation_id` FK
> (migration `323ccfde77f4`) alongside the existing, unchanged, required
> `sender_designation` text — zero backfill, zero risk to existing
> Letters, verified with a real `upgrade`/`downgrade`/`upgrade`/`check`
> cycle. Both new fields are required only when *creating* a Letter,
> never retroactively demanded on edit. Test suite grown to 487 backend
> and 280 frontend tests, each run 3 consecutive times with identical
> results. See `docs/architecture/source-designation.md` §26 for the
> full implementation record and `docs/PROJECT_STATUS.md` for the full
> picture.

---

## 1. What LRS is

The Letter Registry System is a browser-based internal web application for
government departments. It replaces manual letter registers and scattered
spreadsheets with a single searchable record of every official letter an
organization receives, together with the scanned copy of the document itself.

It is designed to run entirely inside a private government network. It does not
depend on the public internet, cloud identity providers, or third-party SaaS.

## 2. Intended purpose

Once complete, LRS is expected to support:

* registering incoming letters with their reference details and metadata
* attaching and viewing the scanned copy of each letter
* routing and tracking letters across multiple departments
* searching and filtering the register by date, department, category, and reference
* role-based access so each user sees only what their role permits
* notifications for assignment and pending action
* administrative management of users, departments, and categories
* reporting and analysis of registry activity

The system is multi-department from the ground up. No structure in this
repository assumes a single department.

## 3. Technology stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| ORM & migrations | SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL |
| Frontend | React 18, Vite, JavaScript, React Router, Axios |
| Document storage | Server filesystem (`storage/letters/`) |
| Authentication | Local JWT (PyJWT, HS256) with Argon2id-hashed passwords — no external identity provider. See `docs/architecture/authentication.md` |

## 4. High-level architecture

```text
        Frontend (React + Vite)
                  │  HTTPS / JSON
                  ▼
        FastAPI REST API  (/api/v1)          app/api
                  │
                  ▼
        Service / business logic layer       app/services
                  │
                  ▼
        Repository / data access layer       app/repositories
                  │
                  ▼
            PostgreSQL (metadata)

        Scanned documents → server filesystem (storage/letters)
                            referenced by path from the database
```

Rules that this structure exists to enforce:

* Dependencies point **downward only**. Routers do not open database sessions;
  repositories do not import services or routers.
* **Document storage is separate from the database.** PostgreSQL stores metadata
  and a relative path; the bytes stay on disk.
* **Security concerns are centralized** in `app/core/security.py`.
* **Configuration is environment-based.** No credential, secret, or connection
  string appears in source.

## 5. Project structure

```text
letter-registry-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application factory
│   │   ├── cli.py               # python -m app.cli create-system-admin
│   │   ├── core/                # config, security (hashing + JWT), logging
│   │   ├── database/            # declarative base, engine, session
│   │   ├── models/              # ORM models            (9 core entities — Phase 2; Letter/Classification extended — 4B)
│   │   ├── schemas/             # Pydantic contracts    (auth — 3A; department — 3B.2; admin — 3B.3; user — 3B.4; letter/category/classification — 4B; document — 4D; notification — 4E)
│   │   ├── api/deps.py          # auth + RBAC dependencies (Phase 3A/3B.1)
│   │   ├── api/v1/endpoints/    # versioned routers     (auth — 3A; dev authz test — 3B.1; departments — 3B.2; admins — 3B.3; users — 3B.4; letters/categories/classifications — 4B; documents — 4D; notifications — 4E)
│   │   ├── services/            # business logic        (auth, bootstrap — 3A; authorization — 3B.1; department — 3B.2; admin — 3B.3; user — 3B.4; letter/category/classification — 4B; document/document_storage/document_validation — 4D; audit/notification — 4E)
│   │   ├── repositories/        # data access           (user, user_authorization — 3A/3B.3/3B.4; department — 3B.2; letter/category/classification — 4B; letter_document — 4D; audit_log/notification — 4E)
│   │   ├── middleware/          # request ID            (empty — later phases; audit generation now lives in the service layer instead, not middleware — see docs/architecture/audit-notifications.md §19)
│   │   └── utils/               # shared helpers        (email normalization — Phase 3A)
│   ├── alembic/                 # migration environment (4 revisions: core schema + hardening + admin authorizations + letter registry core)
│   ├── tests/{unit,integration}
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/{assets,components,layouts,pages,routes,services,hooks,context,utils,constants}
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
├── storage/letters/             # scanned letters (git-ignored)
├── docs/{architecture,api,database,user-guides}
├── scripts/
├── .gitignore
├── LICENSE
└── README.md
```

## 6. Development philosophy

* No hard-coded credentials, secrets, or connection strings — ever.
* No external authentication provider and no external service dependency; the
  system must work on an isolated intranet.
* Loosely coupled modules with a single, one-directional dependency flow.
* Security concerns centralized rather than reimplemented per module.
* Configuration supplied by the environment, differing only in values between
  development, staging, and production.
* Simple, readable solutions preferred over clever ones. This is a system other
  people will maintain for years.
* Multi-department by default; nothing is designed around one organization.
* Built incrementally — each phase is reviewed before the next begins.

## 7. Local development prerequisites

* Python 3.11 or newer
* Node.js 18 or newer, with npm
* PostgreSQL 14 or newer, running and reachable — use a disposable local
  database, never a real departmental one (see `docs/database/README.md`)
* Git

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your local values
alembic upgrade head                # creates the Phase 2 schema
python -m app.cli create-system-admin   # first run only
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`. `/health`, `/docs`, `/redoc`,
the authentication endpoints (`POST /api/v1/auth/signup`,
`POST /api/v1/auth/login`, `GET /api/v1/auth/me`), the department
management endpoints (`/api/v1/departments*`, SYSTEM_ADMIN only), the
Admin management endpoints (`/api/v1/admins*`, SYSTEM_ADMIN only), the
User management endpoints (`/api/v1/users*`, ADMIN only, scoped to the
caller's own department), the Letter registry endpoints (`/api/v1/letters*`
— USER/ADMIN create; any authenticated role reads/updates/archives,
subject to department and classified-access checks; `GET /api/v1/letters`
supports pagination, sorting, and search — see
`docs/architecture/registry-search.md`), Category/
Classification management endpoints (`/api/v1/categories*`,
`/api/v1/classifications*`, SYSTEM_ADMIN only), the document endpoints
(`/api/v1/letters/{letter_id}/documents*` — upload/list/download,
subject to the same department/classified-access rules as their parent
Letter; no deletion endpoint exists), the notification endpoints
(`/api/v1/notifications*` — any authenticated role, always scoped to the
caller's own notifications, never another user's), and five
verification-only authorization endpoints (`/api/v1/auth/test/*` — not
business functionality, see `docs/architecture/authorization.md` §7)
respond — dashboard endpoints and an audit-viewing API don't exist until
a later phase. See
`docs/architecture/authentication.md` for authentication,
`docs/architecture/authorization.md` for RBAC and department isolation,
`docs/architecture/department-management.md` for department CRUD,
`docs/architecture/admin-management.md` for the Admin lifecycle,
`docs/architecture/user-management.md` for the User lifecycle,
`docs/database/schema.md` for the schema behind all of it, and
`docs/architecture/letter-registry.md` for the Letter Registry Core
design (Phase 4A review + Phase 4B implementation).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local         # optional
npm run dev
```

The dev server starts on `http://localhost:5173` and proxies `/api` to the
backend.

> `npm install` and `pip install` have **not** been run in this repository —
> `node_modules/` and `.venv/` are intentionally absent and git-ignored.

## 8. Current development phase

| Phase | Scope | Status |
|---|---|---|
| 1 | Project foundation: structure, configuration, documentation | **Complete** |
| 2 | Database architecture & core models: SQLAlchemy models, Alembic migrations | **Complete** |
| 3A | Authentication foundation & account lifecycle: local login, JWT, signup, bootstrap | **Complete** |
| 3B.1 | RBAC & department authorization: role checks, department-isolation enforcement | **Complete** |
| 3B.2 | Department management: System Admin CRUD for departments, inactive-department authorization | **Complete** |
| 3B.3 | Admin management: System Admin authorizes/approves/deactivates/reactivates/transfers Admins | **Complete** |
| 3B.4 | User management & approval: Admin authorizes/approves/deactivates/reactivates Users, issues/revokes `UserAuthorization` — scoped to their own department | **Complete** |
| 4A | Letter Registry Core: architecture & model review against confirmed V1 requirements | **Complete** |
| 4B | Letter Registry Core: recipient/source departments, sender details, reference number, Category/Classification management, classified-access boundary, full Letter CRUD | **Complete** |
| 4C | Registry Operations & Search: pagination, whitelisted sorting, 7 text-search filters, inclusive date-range filtering — with the classified-access query-level fix applied first | **Complete** |
| 4D | Document Management: `LetterDocument` upload/list/download — storage-path safety, layered file validation, department/classified-access authorization reuse, write-then-commit failure handling. No deletion endpoint (deliberate). | **Complete** |
| 4E | Operational Activity, Notifications & Audit: `AuditLog` generation (append-only, mandatory, targeted old/new values) for Letter/Document/User/Admin/Department/Category/Classification/Authorization events; `Notification` generation for the confirmed "letter registered" trigger, best-effort via a database SAVEPOINT; `GET/PATCH /api/v1/notifications*`. No audit read API (deliberate). | **Complete** |
| 5 | Frontend & Operational UI: architecture/UX review of the React 18 + Vite + React Router + Axios skeleton (unwired since Phase 1) against all 42 real backend endpoints — auth UX, role-aware navigation, Letter/document/notification UX, classified-Letter 404 handling, route/component/API-client architecture, security, test strategy. Review only, no frontend code. | **Complete (review only)** |
| 5A | Frontend Foundation: routing wired up, `AuthContext` (session restore via `/auth/me`, login, logout), one centralized Axios client (auth header, error normalization, 401 handling), `ProtectedRoute`/`RoleGuard`, role-derived navigation, `AppShell`/`Sidebar`/`Topbar`, design tokens, a11y baseline, Vitest test setup (17 tests). No feature screens. | **Complete** |
| 5B | Authentication & Account UX: production Login/Signup forms (client-side validation, full ARIA wiring), reusable pending-approval/deactivated-account notices, session-restoration network-failure handling with retry, logout/redirect verification, test suite grown to 44 tests. No business feature screens. | **Complete** |
| 5C | Core Registry UI: Letter list/search/sort/paginate, create/view/edit/archive, driven entirely by the confirmed `GET/POST/PATCH/DELETE /api/v1/letters*` contract; a confirmed category/classification reference-data access gap resolved (not hardcoded around); test suite grown to 84 tests. No Document/Notification/Administration UI. | **Complete** |
| 5D | Administration & Account Management UI: Department/Administrator/User management screens — list/create/detail, Admin/User authorization workflows, approve/deactivate/reactivate lifecycle, Admin department transfer — driven entirely by the confirmed Department/Admin/User backend contract (no pagination/search/sort exists on any of the four resources, unlike Letters, so none was invented); test suite grown to 159 tests. No Document/Notification/Category/Classification UI. | **Complete** |
| 5E | Documents & Notifications UI: architecture/requirements review of the Document upload/list/download and Notification frontend against the confirmed `documents.py`/`notifications.py` backend contract — confirms fetch+blob is required for downloads, no document delete/replace endpoint exists, and designs the full component/service/route/security/test architecture. Review only, no frontend code. | **Complete (review only)** |
| 5E impl. | Documents & Notifications UI implementation: `DocumentList`/`DocumentUploadForm` wired into `LetterDetailPage` (upload with progress, authenticated blob download, no delete/replace action), `NotificationBell`/`NotificationPanel`/`NotificationItem` wired into `Topbar` and a real paginated `/app/notifications` page, explicit-button-only mark-read, 60-second (`PROVISIONAL`) unread-count polling — driven entirely by the confirmed Document/Notification backend contract; test suite grown to 225 tests. | **Complete** |
| 5F | Dashboard & Operational Overview UI: architecture/requirements review against all twelve mounted business routers — confirms no dashboard/aggregate/audit-read endpoint exists, that Letter counts are cheap and already correctly isolated (real SQL `COUNT`) while Department/Admin/User/Category/Classification counts cost a full-list fetch (no pagination, no DB `COUNT`), and that every historical/trend metric requires new backend work. Full metric inventory, role-specific requirements, and an operational-only V1 recommendation. Review only, no frontend code. | **Complete (review only)** |
| 5F impl. | Dashboard & Operational Overview UI implementation: `/app/dashboard` — role-aware summary cards (Letters for every role; Departments/Admins for SYSTEM_ADMIN; Users for ADMIN), a Recent Letters list, and role-scoped Quick Actions to already-existing screens — driven entirely by existing, already-isolated endpoints; no chart, trend, filter control, or new backend endpoint; test suite grown to 249 tests. | **Complete** |
| 5G | Backend Dashboard Aggregation & Analytics API: architecture/requirements review of whether new backend aggregate endpoints are justified — confirms the existing `letter_visibility_filter`/department-derivation authorization logic is directly reusable for any future aggregate, that every plausible aggregate dimension is already indexed (zero new indexes recommended), and that `AuditLog` has no department column (audit analytics deferred to a future, separate phase). Full metric inventory found no metric with both confirmed value and no existing sufficient API — recommends deferring backend aggregation entirely for V1, with a complete, ready-to-build `GET /api/v1/letters/aggregate` design documented but not implemented. Review only, no backend or frontend code. | **Complete (review only)** |
| 5H | Source Department & Designation Master Data: architecture/requirements review of two handover-demo requirements — confirms `source_department_id` already exists end-to-end on every Letter schema with existing backend validation (a frontend-only task), and that `GET /api/v1/departments` being `require_system_admin`-only would silently block both Source Department and a new Designation dropdown for USER/ADMIN unless relaxed to any authenticated role (read-only). Designs a new `Designation` master-data resource mirroring `Category`/`Classification`, with historical integrity solved via a new nullable `designation_id` FK alongside the existing, unchanged `sender_designation` text — zero backfill. A MUST-IMPLEMENT-BEFORE-HANDOVER list and implementation sequence are documented. Review only, no backend or frontend code. | **Complete (review only)** |
| 5H impl. | Source Department & Designation Master Data implementation: new `Designation` resource (model/repository/service/`GET,POST,PATCH /designations`, `POST .../activate|deactivate`) with its list endpoint deliberately readable by any authenticated role; `GET /departments` relaxed identically; new nullable `letters.designation_id` FK (migration `323ccfde77f4`, verified upgrade/downgrade/upgrade/check); `LetterFormPage.jsx` gains a Source Department selector and a Designation dropdown, both auto-filling their legacy text fields and required only on create; a minimal SYSTEM_ADMIN management page at `/app/system/designations`. Test suite grown to 487 backend / 280 frontend tests. | **Complete** |
| **5H.1** | Complete Existing Category & Classification Admin UI: a confirmed frontend completion gap found during Phase 5H's own manual E2E pass — `/app/system/categories`/`/app/system/classifications` still rendered a "planned" placeholder despite the backend (list/create/update/activate/deactivate, `SYSTEM_ADMIN`-only) being unchanged since Phase 4B. Six new pages mirror the existing Department three-page (list/create/detail-with-inline-edit) pattern exactly; `routes/index.jsx`'s two placeholder routes replaced with nested `RoleGuard` route groups; `navigationConfig.js` needed no changes. No delete action (no `DELETE` route exists); Classification's `restricts_access` flag is forwarded to the backend exactly as set, never computed or enforced client-side. Zero backend files touched. Test suite grown to 487 backend (unchanged) / 320 frontend tests. | **Complete** |
| 5I | Futuristic UI / Visual Architecture & Design System Review: comprehensive review-only inspection of the actual current frontend (every layout/component/page CSS Module, tokens, and test file) against a "futuristic enterprise command center" design direction — confirmed a real color-token bug (ACTIVE status and unread-notification rows both incorrectly reuse the warning-background token) and several duplicated CSS patterns (dialogs, tables, form fields) across otherwise-consistent screens; proposes an extended color/typography/spacing/motion token system, a collapsible-sidebar/mobile-drawer navigation redesign, a unified loading system (boot screen, skeletons, button-level progress), a status-badge icon layer, and an AJ-OVA Labs footer — all achievable with zero new dependencies. No code, test, dependency, backend, or database file was changed. Full record in `docs/architecture/ui-design-system.md`. | **Complete (review only)** |
| 5I.1 | Global Visual Foundation implementation: the first, foundation-only implementation pass against the Phase 5I proposal — extended `tokens.css` (additive color/motion tokens, no rename, no removal), extended `global.css` (a static atmospheric background wash, a strengthened focus ring, a global reduced-motion safety net, one narrow global interaction-transition rule), and fixed the confirmed ACTIVE-badge/unread-notification color bug. No page, layout, or component was redesigned; no sidebar/topbar/dashboard/Letter/administration/document/notification/authentication screen changed; no boot screen, loading animation, or visible footer was added; zero new dependencies. Test suite unchanged at 320 frontend / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| 5I.2 | App Shell & Navigation visual implementation: the second pass against the Phase 5I proposal — `Sidebar` redesigned (CSS-only brand mark, a 3-letter monogram glyph per nav item, active-route accent, a desktop collapse toggle, a mobile drawer with a real focus trap/Escape/backdrop generalized from `ConfirmDialog`'s own pattern); `Topbar` refined (hamburger toggle, clearer identity/role typography, `NotificationBell` behavior untouched); the AJ-OVA Labs footer now actually rendered once in `AppShell` on every authenticated screen. `navigationConfig.js`'s role-derived list is byte-for-byte unchanged. No table/form/dialog consolidation, no Dashboard/Letter/administration/document/notification-panel/authentication redesign, no boot screen, no loading glyph, no system-status indicator; zero new dependencies. Test suite grown to 335 frontend tests (46 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| 5I.3 | Core UI Primitives & Interaction System implementation: the third pass against the Phase 5I proposal — a new shared `styles/primitives.module.css` (button/table/dialog base classes) that `AdminPages`/`LetterFilters`/`DocumentUploadForm`/`DataTable`/`LetterTable`/`ConfirmDialog`/`ArchiveConfirmDialog`/`Topbar`/`NotificationItem` now `compose` from; a global form-control base added to `global.css` (CSS Modules' `composes` cannot target the descendant selectors most existing form duplication used); `StatusBadge` gained a shape layer (circle/diamond/square per tone, never color-only); `EmptyState` gained a CSS-only document glyph; `NotificationItem`'s unread state gained a left accent bar; dialogs gained a short, reduced-motion-safe entrance animation. No Dashboard/Letter-page/Administration-page/Document-page/Notification-panel/Authentication-page redesign, no boot screen, no loading glyph, no drag-and-drop upload; zero new dependencies. An initial overreach into `LetterFormPage.module.css` was caught and reverted before continuing. Test suite grown to 349 frontend tests (48 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| 5I.4A | Dashboard Visual Transformation: the first screen-level pass — `/app/dashboard` recomposed into a header/metrics/registry-activity/quick-actions layout; every summary card unified onto one accent-bar/corner-mark/tabular-numeral treatment; Recent Letters reuses the existing accent-bar-on-hover language and gained a real "N shown" count; Quick Actions became tiles with a decorative, `aria-hidden` arrow; one subtle whole-page entrance fade, no chart/trend/fabricated comparison, no invented system-health or security claim (grepped and tested for). Every metric, fetch, and role-based branch in `DashboardPage.jsx` is confirmed unchanged via `git diff`; zero new dependencies. Test suite grown to 354 frontend tests (48 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| 5I.4B | Letter Registry Visual Transformation: the second screen-level pass — `LetterListPage`/`LetterFormPage`/`LetterDetailPage`/`LetterFilters`/`LetterTable` recomposed with the same registry header language; the filter panel became a "Registry Search" console (same 13 fields, grouped into four fieldsets, plus a decorative active-filter-count badge); the table gained a row accent bar and tabular numerals; the Letter form finally composed the shared button primitives (deferred from 5I.3); the detail page became a four-section record dossier. Category/Classification deliberately not added to the dossier (would need a new fetch, not a visual change). Every field, filter key, URL parameter, sort field, payload, and role branch confirmed unchanged via `git diff`; zero new dependencies. Test suite unchanged at 354 frontend tests (48 files) / 487 backend tests — no test needed to change — run 3 consecutive times with identical results. | **Complete** |
| 5I.4C | Administration Visual Transformation: the third screen-level pass — the entire administration workspace (Departments/Administrators/Users/Authorizations/Designations/Categories/Classifications, ~28 files). Exploited a key structural finding: nearly every page already shared `AdminPages.module.css`/`DataTable.module.css`, so a console-wide eyebrow/accent-line/chip-count header language, consistent button treatment, and one-family row-accent-bar table hover were established almost entirely in those two shared files, cascading to all seven resources; each of 17 list/create/detail pages then needed only a small, resource-specific eyebrow-text insertion. `AdminTransferDialog` gained real visual separation between current-department/target-department/consequences, with its required wording confirmed byte-for-byte unchanged against the exact existing test assertion. Every API payload, service call, role branch, confirmation semantic, and 403/404 collapsing behavior confirmed unchanged via `git diff` and a dedicated 107-test pass; zero new dependencies. Test suite unchanged at 354 frontend tests (48 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| 5I.4D | Documents & Notifications Visual Transformation: the fourth screen-level pass — Documents (within the Letter dossier) and Notifications (Topbar bell, panel, full `/app/notifications` page). `DocumentList` already inherited the Phase 5I.4C table treatment for free via its shared `DataTable.module.css` import; `LetterDetailPage` gained a real, non-fabricated attachment count (`documents.length`); the upload form gained a percentage-bound progress bar (shown only when a real percentage is known, no fake progress); the Notification panel gained an "Operational Signals" eyebrow and a CSS-only connector to the Topbar bell; notification rows gained one more static (non-animated) unread dot alongside the existing accent bar/background/weight; the notification page gained the same eyebrow/accent-line/chip-count header used everywhere else. `NotificationBell` audited and left unmodified (already at the target bar). No unread filter/search/category/bulk control added (none exist in the backend contract); mark-read stays explicit-button-only; every service call, payload, and role branch confirmed unchanged via `git diff`; zero new dependencies. Test suite unchanged at 354 frontend tests (48 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| **5I.4E** | Authentication Visual Transformation: the fifth screen-level pass — the unauthenticated entrance experience (`LoginPage`, `SignupPage`, and the `PendingApprovalNotice`/`DeactivatedAccountNotice` states they render). Confirmed the existing composition was exactly the generic "white card + email + password + blue button" pattern, with the submit button never composed onto the Phase 5I.3 shared primitives (Authentication pages were explicitly deferred in that phase). Both pages now share one local `AuthShell` wrapper rendering a static brand mark (the same nested-square geometry `Sidebar.module.css` established in Phase 5I.2, scaled up), `APP_NAME`, and the existing, previously-unrendered `PRODUCTION_CREDIT` line — distinguished only by a small eyebrow label ("Account Access" vs. "New Account Request"). The submit button now composes `btn btnPrimary`; both account-state notices gained a small `aria-hidden` color marker. No password-visibility toggle was added (none exists today, none was requested); the animated boot/loading glyph remains reserved for a later phase. Every field, label, validation rule, submit handler, and redirect confirmed unchanged via `git diff`; `AuthContext.jsx` was read but not modified; zero new dependencies. Test suite unchanged at 354 frontend tests (48 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| **5I.5** | Boot & Loading Experience: a new `BootScreen` component/CSS module and a small gate in `App.jsx`, using `AuthContext`'s own existing `status === 'loading'` window (never a duplicated timer, never a new loading flag) to render a distinctive "Precision Ledger" identity moment — a CSS-only "LRS Registry Glyph" (the existing nested-square brand geometry plus four ticks that illuminate in sequence, a duration derived via `calc()` from the existing `--motion-slow` token) and a real, truthful `role="status"` message ("Loading Letter Registry System") — instead of the bare spinner every other loading moment already uses (deliberately left unreplaced). `ProtectedRoute`/`RootRedirect`'s own `status === 'loading'` branches are untouched. No artificial delay, fake progress, or fake initialization step was added; `AuthContext.jsx` was read but not modified; zero new dependencies. Test suite grown to 363 frontend tests (50 files) / 487 backend tests, run 3 consecutive times with identical results. | **Complete** |
| **5I.6** | Final Polish, Manual E2E & Handover Audit: the closing audit across all nine prior visual phases — a full documentation re-read, a full screen inventory, and a codebase-wide search (hardcoded colors, `transition: all`, `outline: none`, stray `console.log`/`setTimeout`, every animation's reduced-motion coverage, every breakpoint, every emoji, branding-string consistency, and the full JWT/token/localStorage/role/department-id/recipient/storage-path/signed-URL security pattern set) combined with targeted reads. One genuine defect found and fixed: `NotificationBell`'s 🔔 emoji — the one full-color, OS-rendered pictograph in the entire application — replaced with a CSS-only bell outline, zero behavior change (confirmed by its own 9 existing tests passing unmodified). Several other candidates were reviewed and confirmed intentional or already correct, not defects (documented in full in `docs/architecture/ui-design-system.md`'s own "Phase 5I.6" section) — including `NotificationPanel`'s deliberate `outline: none` on its non-Tab-reachable container, a one-pixel breakpoint-naming nitpick with no visible consequence, and the Boot screen's deliberately simpler background versus Authentication's. Manual browser verification was **not performed** — no browser-automation tool is available in this environment. Test suite unchanged at 363 frontend tests (50 files) / 487 backend tests, run 3 consecutive times with identical results. The Phase 5I visual architecture (5I.1–5I.6) is now considered closed. | **Complete** |
| **5I.6A** | Sidebar Icon Identity Correction: a targeted fix found during final visual verification — the Sidebar's navigation "icons" (Phase 5I.2) were actually 3-letter monograms, a deliberate placeholder that manual review confirmed read as text labels, not icons. Replaced with 9 small inline SVG icons (Dashboard/Letters/Documents/Notifications/Departments/Administrators/Designations/Categories/Classifications, plus a `Users` icon the brief's own suggested mapping omitted), each using `stroke="currentColor"` so its color follows the existing `.linkActive .linkGlyph` active-state rule rather than a second mechanism; the bordered "chip" container was replaced with a plain 18×18px unboxed icon box. `navigationConfig.js`, routes, labels, permissions, active-route logic, and collapse/mobile-drawer behavior all confirmed unchanged via `git diff`; zero new dependencies. Test suite grown to 364 frontend tests (50 files, +1) / 487 backend tests, run 3 consecutive times with identical results (one incidental backend flake reproduced as passing on rerun, confirmed unrelated). | **Complete** |
| 6 | Additional notification triggers, audit read API, dashboard analytics (if a specific breakdown/trend is ever confirmed wanted), a Designation edit/detail page | Not started |

See `docs/PROJECT_STATUS.md` for what Phase 5H, 5H.1, 5I, 5I.1, 5I.2,
5I.3, 5I.4A, 5I.4B, 5I.4C, 5I.4D, 5I.4E, 5I.5, 5I.6, and 5I.6A delivered,
`docs/architecture/source-designation.md`
§26 for the Phase 5H implementation record, and
`docs/architecture/ui-design-system.md` for the Phase 5I visual
architecture review and the Phase
5I.1/5I.2/5I.3/5I.4A/5I.4B/5I.4C/5I.4D/5I.4E/5I.5/5I.6/5I.6A
implementation records. The next phase begins only when explicitly
instructed.

---

## Team

**A Production of AJ-Labs**

| Role | Name |
|---|---|
| Production | AJ-Labs |
| Developer | Ajlal |
| Tester & Quality Assurance | Afnan |
| Technical Documentation & UI/UX Support | Faiza |
