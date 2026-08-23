# Letter Registry System (LRS)

**A Production of AJ-Labs**

> **Current status: Phase 5F — Dashboard & Operational Overview UI
> implemented (Phase 5E Documents & Notifications UI implemented; Phase
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
> the full implementation record and `docs/PROJECT_STATUS.md` for the
> full picture.

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
| **5F impl.** | Dashboard & Operational Overview UI implementation: `/app/dashboard` — role-aware summary cards (Letters for every role; Departments/Admins for SYSTEM_ADMIN; Users for ADMIN), a Recent Letters list, and role-scoped Quick Actions to already-existing screens — driven entirely by existing, already-isolated endpoints; no chart, trend, filter control, or new backend endpoint; test suite grown to 249 tests. | **Complete** |
| 6 | Additional notification triggers, audit read API, Category/Classification management UI, dashboard analytics (if ever confirmed) | Not started |

See `docs/PROJECT_STATUS.md` for what Phase 5F delivered,
`docs/architecture/dashboard.md` §32 for the full implementation
record, and known limitations. The next phase begins only when
explicitly instructed.

---

## Team

**A Production of AJ-Labs**

| Role | Name |
|---|---|
| Production | AJ-Labs |
| Developer | Ajlal |
| Tester & Quality Assurance | Afnan |
| Technical Documentation & UI/UX Support | Faiza |
