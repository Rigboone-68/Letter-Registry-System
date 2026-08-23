# Letter Registry System (LRS)

**A Production of AJ-Labs**

> **Current status: Phase 5B — Authentication & Account UX implemented
> (Phase 5A Frontend Foundation implemented; Phase 5 architecture/UX
> review complete; Phase 4E Operational Activity, Notifications & Audit
> implemented; Phase 3B complete).**
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
> defect. **No Letter/Document/Notification/Administration screen exists
> yet** — every nav destination is a shared placeholder; those remain
> for later phases. See `docs/PROJECT_STATUS.md` for the full picture.

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
| **5B** | Authentication & Account UX: production Login/Signup forms (client-side validation, full ARIA wiring), reusable pending-approval/deactivated-account notices, session-restoration network-failure handling with retry, logout/redirect verification, test suite grown to 44 tests. No business feature screens. | **Complete** |
| 5C+ | Frontend feature implementation: Letters, Documents, Notifications, Administration | Not started |
| 6 | Dashboards, reporting, additional notification triggers, audit read API | Not started |

See `docs/PROJECT_STATUS.md` for what Phase 5B delivered,
`docs/architecture/frontend.md` for the full design, and known
limitations. The next phase begins only when explicitly instructed.

---

## Team

**A Production of AJ-Labs**

| Role | Name |
|---|---|
| Production | AJ-Labs |
| Developer | Ajlal |
| Tester & Quality Assurance | Afnan |
| Technical Documentation & UI/UX Support | Faiza |
