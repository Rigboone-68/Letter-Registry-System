# Letter Registry System (LRS)

**A Production of AJ-Labs**

> **Current status: Phase 1 — project foundation only.**
> This repository contains the folder structure, configuration scaffolding, and
> documentation for the system. **No application functionality is implemented.**
> There is no authentication, no database model, no endpoint, no dashboard, and
> no upload handling. Features are added module by module in later phases.

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
| Authentication (planned) | Local JWT with hashed passwords — no external identity provider |

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
│   │   ├── core/                # config, security, logging
│   │   ├── database/            # declarative base, engine, session
│   │   ├── models/              # ORM models            (empty — Phase 2+)
│   │   ├── schemas/             # Pydantic contracts    (empty — Phase 2+)
│   │   ├── api/v1/endpoints/    # versioned routers     (empty — Phase 2+)
│   │   ├── services/            # business logic        (empty — Phase 2+)
│   │   ├── repositories/        # data access           (empty — Phase 2+)
│   │   ├── middleware/          # request ID, audit     (empty — Phase 2+)
│   │   └── utils/               # shared helpers        (empty — Phase 2+)
│   ├── alembic/                 # migration environment (no revisions yet)
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
* PostgreSQL 14 or newer, running and reachable
* Git

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your local values
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`. Only `/health`, `/docs`, and
`/redoc` respond in Phase 1.

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
| **1** | Project foundation: structure, configuration, documentation | **Complete** |
| 2 | Database models, migrations, authentication and RBAC | Not started |
| 3 | Letter registry CRUD and document upload/viewing | Not started |
| 4 | Dashboards, search, notifications, reporting | Not started |
| 5 | Administration, audit trail, deployment hardening | Not started |

Phase 2 begins only when explicitly instructed.

---

## Team

**A Production of AJ-Labs**

| Role | Name |
|---|---|
| Production | AJ-Labs |
| Developer | Ajlal |
| Tester & Quality Assurance | Afnan |
| Technical Documentation & UI/UX Support | Faiza |
