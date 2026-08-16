# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Current Phase

**Phase 2 — Database Architecture & Core Models.** Complete, including a
corrective hardening pass performed after a self-review of the initial
implementation.

Phase 2 delivered the SQLAlchemy ORM layer and the Alembic migrations for
the Letter Registry System. No authentication, API, service logic, or
frontend functionality was in scope for this phase, and none was added —
including during the hardening pass.

## Completed

* **9 core SQLAlchemy models** (`backend/app/models/`): Department, User,
  UserAuthorization, Category, Classification, Letter, LetterDocument,
  Notification, AuditLog. Full details in `docs/database/schema.md`.
* **Two Alembic migrations**: `3da4b7ee8167_core_schema_...` (baseline —
  9 tables + `alembic_version`, 5 native PostgreSQL enum types, 12 foreign
  keys, 26 indexes) and `e8a5cea2ccc6_database_hardening_...` (corrective —
  2 more indexes plus a database-level default; see "Corrections applied"
  below).
* **Department isolation groundwork**: every departmental entity carries a
  required, indexed `department_id`; enforcement of "a user only touches
  their own department's data" is designed for but deferred to a future
  service layer — see `docs/architecture/overview.md` §3.
* **Role/department invariant enforced at the database level**: a `CHECK`
  constraint rejects any `users` row where `SYSTEM_ADMIN` has a department
  or `ADMIN`/`USER` doesn't. Now covers all six role/has-department
  combinations in an automated test.
* **Case-insensitive, unique user email** via a PostgreSQL functional unique
  index (`lower(email)`), without adding a `citext` extension dependency.
* **31 automated tests**: 27 in `backend/tests/integration/test_models.py`
  (model creation, relationships, constraints, FK `RESTRICT`/`CASCADE`
  behavior, database-level defaults — against a real local PostgreSQL 17
  instance) and 4 in `backend/tests/unit/test_imports.py` (fresh-interpreter
  import checks, no database needed).
* **Documentation**: `docs/database/schema.md` and
  `docs/architecture/overview.md`, plus updates to the root README,
  `backend/README.md`, and `docs/database/README.md`.

### Corrections applied (self-review hardening pass)

A self-review of the initial Phase 2 implementation found six issues,
addressed as follows — see `docs/database/schema.md` for the technical
detail behind each:

| # | Issue | Fix |
|---|---|---|
| 1 | Order-dependent circular import: `from app.models import X` (or `from app.models.user import X`) could fail in a fresh interpreter depending on what had already been imported | `app/database/base.py` no longer imports `app.models`; consumers that need full metadata (`alembic/env.py`, `tests/conftest.py`) import it themselves. Guarded by `tests/unit/test_imports.py` |
| 2 | ORM-level `session.delete(department)` didn't cleanly hit the database's `RESTRICT` — SQLAlchemy tried to null out dependent users' `department_id` first, which instead tripped an unrelated CHECK constraint | `passive_deletes="all"` added to every `RESTRICT`/`SET NULL`-backed one-to-many relationship (Department, Category, Classification, User, and `Letter.notifications`), so the ORM defers entirely to the database's own FK action |
| 3 | `departments.status` had no index, unlike the equivalent column on Category/Classification | Added (`ix_departments_status`) |
| 4 | `notifications.is_read` had no database-level default — a row written outside the ORM would fail `NOT NULL` | Added `server_default=false()`, alongside the existing ORM-side default |
| 5 | `letter_documents.uploaded_by` had no index, unlike every other User-referencing FK in the schema | Added (`ix_letter_documents_uploaded_by`) |
| 6 | The role/department `CHECK` constraint hardcoded role strings, duplicating `UserRole`'s values | Model-side constraint now built from `UserRole.*.value`; the migration's own copy is deliberately still a literal (migrations are frozen snapshots) — see `app/models/user.py` docstring |

### Validation performed

All of the following were run against a **real, local, disposable**
PostgreSQL 17 instance (the same one installed for the original Phase 2
validation — never a shared or departmental database):

| Check | Result |
|---|---|
| `alembic upgrade head` against `lrs_dev` | Both migrations applied cleanly |
| `alembic downgrade base` → `alembic upgrade head` | Full round-trip verified after the hardening migration was added |
| `alembic revision --autogenerate` after upgrading | "No new upgrade operations detected" — migrations match models exactly |
| `pytest` against `lrs_test` | 31 passed, 0 failed, 0 warnings |
| `from app.models import User` / `from app.models.user import User` in fresh interpreters | Both succeed (previously order-dependent) |
| FastAPI app startup + `GET /health` | 200 OK, using the real `lrs_dev` connection string |
| Empirical FK behavior (raw SQL and ORM-level, against `lrs_dev`, transactional/cleaned up) | `RESTRICT` blocks Department/User deletion with a clean FK error; `CASCADE` removes LetterDocument/Notification rows when their Letter is deleted |

## In Progress

Nothing — Phase 2 is complete and the project is paused pending explicit
instruction to begin Phase 3, per the standing project rule that phases are
reviewed before the next begins.

## Pending Confirmation (from S&IT)

None of the following are implemented as final requirements — each is a
documented, minimal, reversible assumption. See `docs/database/schema.md`
§7 for the full reasoning behind each.

* **Official letter/reference number** — existence and format unconfirmed.
  No column exists for it.
* **Sender types** (`letters.received_from`) — not assumed to always be a
  government department; stored as free text.
* **Final category list** — nothing seeded; "Budget/Procurement/HR/Legal/
  Infrastructure" were requirements-gathering examples only.
* **Final classification/priority terminology** — "Important/Classified/
  Routine" were examples only; nothing seeded.
* **Departmental code format** (`departments.code`) — left nullable,
  unformatted.
* **`letters.subject` / `letters.reason` requirement-ness** — both left
  nullable pending confirmation of intake requirements.
* **Document retention requirements** — not addressed; no retention/expiry
  field exists on `letter_documents`.

## Known Limitations

* **No PostgreSQL was available in the initial development environment.**
  One was installed and configured specifically to validate this phase (see
  "Validation performed" above) rather than leaving the migration and test
  suite unverified. In an environment where PostgreSQL is genuinely
  unavailable, `pytest` skips (does not fail) the model tests — see
  `docs/database/README.md`, "Providing a local test database".
* **A pre-existing Phase 1 config bug was fixed during this phase's
  validation.** `backend/app/core/config.py`'s `CORS_ORIGINS` setting
  crashed on startup (`pydantic_settings.exceptions.SettingsError`) when
  `.env` was created by copying `.env.example` exactly as the README
  instructs, because pydantic-settings tried to JSON-decode the documented
  comma-separated value before the field's own validator ran. Fixed with a
  one-line `NoDecode` annotation (see `backend/README.md`, "Configuration").
  This was outside Phase 2's nominal scope (database architecture) but was
  fixed because it silently broke this phase's own "verify the app starts"
  validation step and every documented getting-started instruction.
* **`httpx`/Starlette deprecation warning** on `TestClient` import
  (`Using httpx with starlette.testclient is deprecated; install httpx2
  instead`) — pre-existing, noted in `requirements.txt`'s own comment.
  Not addressed in this phase; harmless for now, but will need resolving
  before Phase 3 adds real API tests.
* **No database-level enforcement of department isolation** — by design,
  deferred to a future service layer. See `docs/architecture/overview.md`
  §3 for why this cannot be a schema-level guarantee.
* **`passive_deletes="all"` (added in the hardening pass) has a documented
  SQLAlchemy caveat**: an object already loaded into a session's identity
  map before its row is removed by the database's own `ON DELETE CASCADE`
  is not automatically expunged or refreshed within that same session —
  `session.get(...)` can return a stale copy until the session is expired
  or a fresh one is used. This is inherent to the pattern, not a bug; see
  `docs/database/schema.md` §1, "ORM deletion behavior", and the test that
  demonstrates it. A future service/repository layer needs to be aware of
  this when deleting a Letter in the same session that will keep running.

## Next Recommended Phase

**Phase 3** per the root README's phase table: authentication and RBAC
(password hashing, JWT issuance/validation in `app/core/security.py`,
signup against `UserAuthorization`, login, department-derived request
context), followed by the Letter registry CRUD and document upload
endpoints that depend on it. Recommend authentication before Letter CRUD,
since department isolation enforcement (the core security requirement this
schema was built around) has nothing to derive `department_id` from until a
real authenticated request context exists.
