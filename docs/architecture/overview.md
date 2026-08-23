# Architecture Overview — Roles, Hierarchy, and Department Isolation

**Status:** Phase 3B (Roles & Access Management) is fully delivered, Phase
4B built the Letter Registry Core on top of it — the first real
departmental *business* resource, not just a management resource — Phase
4C added operations/search on top of that, Phase 4D implemented
document upload/list/download for `LetterDocument`, extending the same
authorization chain (`assert_letter_access`) to per-letter document
attachments rather than adding a second one, and Phase 4E implemented
audit-trail generation (append-only, mandatory, same-transaction) and
in-system notification generation (best-effort, via a database
`SAVEPOINT`) for the events and the one confirmed trigger its own
architecture review identified — an audit read API, when eventually
built, is designed to delegate to that same `assert_letter_access` chain
a third time, not invent a fourth, but was not itself built this phase.
Phase 5 then reviewed the frontend that will eventually expose all of
this — role-aware navigation, and, critically, a design discipline
requiring the frontend to render `404` identically for a nonexistent
and an inaccessible-classified Letter, never re-implementing
classified-access filtering client-side — Phase 5A implemented that
review's *foundation* (routing, a single `AuthContext` sourcing role/
department/status from `GET /auth/me` or the login response's own
`UserPublic` only, one centralized API client, protected routes,
role-derived navigation, the app shell), Phase 5B then implemented the
complete authentication/account experience on top of that foundation
(login, signup, pending-approval, deactivated-account, session
restoration, logout, redirects), Phase 5C then implemented the complete
Letter registry on top of both — list/search/sort/paginate, create/
view/edit/archive — rendering `items`/`total` exactly as the backend
returns them and every Letter `404` identically, and Phase 5D then
implemented the Department/Administrator/User management UI — the
System Admin's authority over Departments and Admins, and an Admin's
authority over Users within their own department, both now have a real
frontend exercising exactly the role/department checks
`app/services/authorization.py` and `app/api/deps.py` already enforce,
verified directly against this implementation rather than only
designed for it. Phase 5E then reviewed, and implemented, the
Documents/Notifications frontend against `documents.py`/
`notifications.py` — both confirmed unchanged since Phase 4D/4E,
re-verifying that a document download requires an authenticated
fetch (the same Bearer-token requirement every other endpoint in this
system has, no exception) and that a notification's access rule is
per-account ownership alone, never department/role scoping. The
Letter detail page now has a real Documents section and `Topbar` now
has a `NotificationBell`, both built with no frontend authorization
rule of any kind layered on top of the backend's own access
decisions — a `404` renders identically whether a document is
nonexistent or its parent Letter is classified-inaccessible, the same
discipline every prior phase's own frontend work already held to. See
`document-notification-ui.md` §27 for the full implementation record.
This document explains the roles and hierarchy
the database schema is
built to support, how a caller's identity is established (Phase 3A), how
role/department authorization decisions are enforced on top of that
identity (Phase 3B.1), how departments themselves are managed (Phase
3B.2), how Admin accounts are authorized, approved, and managed by System
Admin (Phase 3B.3), how regular User accounts are authorized, approved,
and managed by an Admin, scoped to that Admin's own department (Phase
3B.4), and how a User/Admin now records, retrieves, updates, and archives
Letters within that same department boundary, with an additional
classified-access narrowing for certain letters (Phase 4B). See §4, "What
is implemented vs. deferred", [`authentication.md`](authentication.md)
for authentication, [`authorization.md`](authorization.md) for the RBAC/
department-isolation design, [`department-management.md`](department-management.md)
for department CRUD, [`admin-management.md`](admin-management.md) for the
Admin lifecycle, [`user-management.md`](user-management.md) for the User
lifecycle, [`letter-registry.md`](letter-registry.md) for the Letter
Registry Core (Phase 4A review + Phase 4B implementation), and
[`registry-search.md`](registry-search.md) for the Phase 4C
implementation of listing/filtering/search/pagination, and
[`document-management.md`](document-management.md) for the Phase 4D
architecture review of document upload/download — review and design
only; no upload/download code exists yet.

## 1. The hierarchy

```text
System Admin
    ↓
Departments
    ↓
Admins
    ↓
Users
    ↓
Letters
```

## 2. Roles

### System Admin

System-wide authority. Not bound to any department —
`users.department_id` is `NULL` for this role (enforced by
`ck_users_role_department_pairing`, see `docs/database/schema.md` §2.2).
As of Phase 3A, the first System Admin is created by a server-side CLI
bootstrap command, never through public signup — see
[`authentication.md`](authentication.md) §8. As of Phase 3B.2, a System
Admin can create, list, retrieve, update, activate, and deactivate
departments (`POST`/`GET`/`PATCH /api/v1/departments...` —
[`department-management.md`](department-management.md)). As of Phase
3B.3, a System Admin also authorizes Admin candidates, approves them,
deactivates/reactivates Admin accounts, and moves an Admin between
departments (`/api/v1/admins*` —
[`admin-management.md`](admin-management.md)) — using the *same* signup
workflow a regular User goes through, not a separate one. Managing
Categories and Classifications remains future work (§4). As of Phase
4D, a System Admin can also upload, list, and download any Letter's
documents regardless of department — the one place document access is
deliberately *not* restricted the way Letter *creation* is (System Admin
still cannot create a Letter, having no department to record one
against) — see [`document-management.md`](document-management.md) §33.

### Admin

Bound to exactly one department (`users.department_id` is required for this
role, same constraint), and — as of Phase 3B.3 — a department may have any
number of Admins (zero, one, or many; no uniqueness constraint enforces a
single Admin per department). As of Phase 3B.4, an Admin authorizes User
candidates, approves them, and deactivates/reactivates User accounts,
scoped strictly to their own department (`/api/v1/users*` —
[`user-management.md`](user-management.md)). As of Phase 4B, an Admin also
has the same Letter CRUD access as a User in their department — create,
read, update, archive — narrowed only by the classified-access boundary
(`/api/v1/letters*` — [`letter-registry.md`](letter-registry.md) §9). As of Phase 4D, an Admin's document upload/list/download access
on a Letter follows the same department boundary as its Letter access —
[`document-management.md`](document-management.md) §16-17. An
Admin **cannot** authorize or manage other Admins, approve or create
Admin accounts, or change their own role or department — every
Admin-management operation still requires `SYSTEM_ADMIN`; see
[`admin-management.md`](admin-management.md) §11. An Admin is enforced to
be able to act only within their own department —
[`authorization.md`](authorization.md) §3 — and only while that department
is `ACTIVE`; see [`department-management.md`](department-management.md)
§5 and [`user-management.md`](user-management.md) §5 for how that rule
splits into three different strengths depending on the User-management
action (Letter access, by contrast, applies the plain, undifferentiated
rule uniformly — see [`letter-registry.md`](letter-registry.md) §9).

### User

Also bound to exactly one department. As of Phase 4B, registers/reads/
edits/archives Letters for their own department — but not another
department's, and not another user's classified letters unless they
recorded it themselves (`/api/v1/letters*` —
[`letter-registry.md`](letter-registry.md) §8-9). As of Phase 4D, the
same rule gates a User's access to a Letter's documents
(`/api/v1/letters/{letter_id}/documents*` —
[`document-management.md`](document-management.md) §16-17) — there is no
separate document-level permission check to bypass or fall out of sync
with the Letter-level one. A User account is
created via signup against an Admin-issued `UserAuthorization`, starting
`PENDING_APPROVAL` — as of Phase 3B.4, an Admin (scoped to their own
department) approves it, the same way a System Admin approves an Admin
candidate — see [`authentication.md`](authentication.md) §5 and
[`user-management.md`](user-management.md) §1. Department-isolation
enforcement for a User is in place at the dependency layer —
[`authorization.md`](authorization.md) §3 — and, as of Phase 4B, is
exercised against Letters via `recipient_department_id` specifically, not
`source_department_id` (which carries no authorization meaning at all —
see [`letter-registry.md`](letter-registry.md) §5). As of Phase 3B.2, a
User's department-scoped operations are also blocked whenever their
department is `INACTIVE` — [`department-management.md`](department-management.md)
§5 — without touching the User row itself.

## 3. Department isolation

Department isolation is the core security requirement this schema exists to
support:

* Every departmental entity — `User`, `UserAuthorization`, `Letter` — carries
  a department reference: `department_id` on `User`/`UserAuthorization`, and
  (as of Phase 4B) `recipient_department_id` specifically on `Letter` —
  `Letter` also carries `source_department_id`, which is a descriptive fact
  about a letter's origin, never an authorization boundary (see
  [`letter-registry.md`](letter-registry.md) §5).
* A `User`'s own `department_id` is the **only** source of truth for which
  department's data they can touch — enforced by the service layer on every
  write and read, never derived from client input.
* **This is not, and cannot be, enforced by the database schema alone** —
  nothing at the schema level stops a single `INSERT` from writing an
  arbitrary `recipient_department_id` into `letters`. What the schema
  *does* guarantee is that the column exists, is required (`NOT NULL`), and
  is indexed (`ix_letters_recipient_department_id`, plus the composite
  `ix_letters_recipient_department_received_at` for "this department's
  letters by date"). The actual guarantee — that a caller can never write or
  read another department's letter — is enforced entirely at the service
  layer, described below, not by a database constraint.
* **The enforcement point, implemented as of Phase 4B**: `recipient_department_id`
  on a new Letter (and `department_id` on a new User, via authorization) is
  always derived from the authenticated caller's own `department_id`, never
  accepted as client input — `LetterCreate`
  (`app/schemas/letter.py`) has no field for it at all, so there is nothing
  for a client-supplied value to bind to, not just a value that gets
  ignored.

This is why the brief for Phase 2 explicitly said "do not rely on frontend
filtering to enforce department isolation" — the schema was designed so
backend-level enforcement (a `WHERE recipient_department_id =
:current_user_department` clause added by the service/repository layer,
always, not optionally) would be straightforward to add later; Phase 4B is
where that actually happened.

**Phase 3A added the identity this depends on; Phase 3B.1 added the
enforcement mechanism; Phase 4B is the first phase where it protects a
real departmental *business* resource, not only management resources.**
`get_current_user` (`app/api/deps.py`) reliably answers "who is calling,
and what is their `department_id`" for any authenticated request.
`app/services/authorization.py:assert_department_access` (and its FastAPI
wrapper, `require_department_access`) is the one reusable place that turns
that identity into an allow/deny decision — SYSTEM_ADMIN bypasses,
ADMIN/USER must match their own `department_id` exactly, and the target
department must be `ACTIVE`. Signup already applied the same underlying
principle in its own narrow scope since Phase 3A (a new User's
`department_id` comes from their `UserAuthorization`, never from the
signup request body). Phase 3B.4 first exercised the check as a genuine
resource-level guard (User management); Phase 4B built
`assert_letter_access` (`app/services/authorization.py`) directly on top
of it for `Letter` — department isolation first, then a further
classified-access narrowing for certain letters — see
[`letter-registry.md`](letter-registry.md) §5/§8 for the full design and
[`authorization.md`](authorization.md) §7 for the verification-only
endpoints that first proved the underlying mechanism, before any real
resource existed to protect.

## 4. What is implemented vs. deferred

### Implemented (Phase 2 — database)

* Full SQLAlchemy 2.x model layer for all nine core entities (Department,
  User, UserAuthorization, Category, Classification, Letter,
  LetterDocument, Notification, AuditLog) — see `docs/database/schema.md`.
* Two Alembic migrations creating and hardening the complete schema:
  tables, native PostgreSQL enum types, foreign keys, indexes, and
  constraints — see `docs/database/schema.md` §1 and §6 for what the
  second (corrective) migration changed and why.
* Database-level enforcement of: department name/user email/category
  name/classification name uniqueness; the role↔department pairing
  invariant; restrictive foreign keys that prevent orphaning historical
  records, configured so ORM-level deletes surface that restriction
  cleanly rather than attempting to null out dependent rows first (see
  `docs/database/schema.md` §1, "ORM deletion behavior").
* Model-level tests (`backend/tests/integration/test_models.py`, plus
  `backend/tests/unit/test_imports.py` for import-graph regressions), run
  against a real local PostgreSQL instance.

### Implemented (Phase 3A — authentication foundation)

* Local email/password authentication with Argon2id hashing and JWT access
  tokens — no external identity provider. Full design in
  [`authentication.md`](authentication.md).
* `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`,
  `GET /api/v1/auth/me` — the first real API endpoints and the first use
  of the `app/services/` and `app/repositories/` layers.
* `get_current_user` (`app/api/deps.py`) — establishes an authenticated
  request's identity (`User`, freshly loaded and status-checked from the
  database on every call); the foundation Phase 3B's authorization
  decisions will sit on top of, but does not itself make any
  role/department decision.
* Account lifecycle enforcement (`PENDING_APPROVAL`/`ACTIVE`/`DEACTIVATED`)
  at login and on every authenticated request.
* Race-safe signup against `UserAuthorization`, and a CLI bootstrap for the
  first System Admin.

### Implemented (Phase 3B.1 — RBAC & department authorization)

* Role-check dependencies — `require_system_admin`, `require_admin`,
  `require_admin_or_system_admin`, `require_user_or_admin`
  (`app/api/deps.py`) — each composed on top of `get_current_user`, never
  re-deciding authentication.
* Department-isolation enforcement — `assert_department_access`
  (`app/services/authorization.py`, framework-agnostic) and its FastAPI
  wrapper `require_department_access` — SYSTEM_ADMIN bypasses,
  ADMIN/USER must match their own `department_id`. Full design in
  [`authorization.md`](authorization.md).
* Five verification-only endpoints
  (`app/api/v1/endpoints/dev_authz_test.py`) exercising every dependency
  above end-to-end over real HTTP — not business functionality, see
  [`authorization.md`](authorization.md) §7.
* 42 new tests (16 unit, 26 integration against a real PostgreSQL test
  database), including explicit negative-security tests proving a
  client-supplied `department_id` cannot be used to escalate access.

### Implemented (Phase 3B.2 — department management)

* `POST`/`GET`/`PATCH /api/v1/departments`, `.../{id}`,
  `.../{id}/activate`, `.../{id}/deactivate` — SYSTEM_ADMIN only, full
  design in [`department-management.md`](department-management.md).
* `app/services/department_service.py`, `app/repositories/department_repository.py`,
  `app/schemas/department.py` — following the same layered architecture,
  not a second one.
* A small, documented extension to `assert_department_access` (Phase
  3B.1): ADMIN/USER department-scoped operations are now also blocked
  while their department is `INACTIVE`, without modifying any User row —
  [`department-management.md`](department-management.md) §5.
* A schema-level fix (not a migration — see
  [`database/schema.md`](../database/schema.md)): `Department.name`/`code`
  now use explicitly named unique constraints instead of the `unique=True`
  shorthand, so `Base.metadata.create_all()` (test database) and the
  Alembic migration (real database) produce identical constraint names —
  found while building duplicate-detection error messages for this phase.
* 36 new tests against a real PostgreSQL test database, covering every
  item in the brief's Authorization/Creation/Retrieval/Update/Status/
  Security test lists.

### Implemented (Phase 3B.3 — Admin management)

* `POST /api/v1/admins/authorizations`, `GET /api/v1/admins`,
  `GET /api/v1/admins/{id}`, `POST .../approve`, `.../deactivate`,
  `.../reactivate`, `PATCH .../department` — all SYSTEM_ADMIN only. Full
  design in [`admin-management.md`](admin-management.md).
* `UserAuthorization` extended with one column, `purpose`
  (`AuthorizationPurpose`: `USER` | `ADMIN`), rather than a parallel
  `AdminAuthorization` table — one migration, backfill-safe, tested with
  an actual pre-existing row. `AuthService.signup` (Phase 3A, unchanged
  endpoint) now derives the created User's role from this field, so a
  USER-purpose authorization can never produce an ADMIN and vice versa —
  by construction, not by a separate check. No second signup endpoint or
  workflow was created.
* Multiple Admins per department, deliberately unbounded — no unique
  constraint added on `users.department_id`.
* Admin department transfer, proven not to rewrite any historical
  `Letter.department_id` — a direct, tested consequence of a Phase 2
  design decision (letters store their own department, never re-derived
  from the recording user), not new code written for this phase; see
  [`admin-management.md`](admin-management.md) §9.
* `app/services/admin_service.py`, extensions to the existing
  `UserRepository`/`UserAuthorizationRepository` (no new repository
  created, per the brief's explicit preference), `app/schemas/admin.py` —
  same layered architecture, reusing `require_system_admin` (Phase 3B.1)
  rather than adding a new dependency.
* 47 new tests against a real PostgreSQL test database, covering every
  item in the brief's Authorization/Workflow/Approval/Lifecycle/Multiple-
  Admins/Department-Transfer/Self-Protection/System-Admin-Protection/
  Race-Safety lists.

### Implemented (Phase 3B.4 — User management)

* `POST /api/v1/users/authorizations`, `GET /api/v1/users/authorizations`,
  `DELETE /api/v1/users/authorizations/{id}`, `GET /api/v1/users`,
  `GET /api/v1/users/{id}`, `POST .../approve`, `.../deactivate`,
  `.../reactivate` — all `ADMIN` only, scoped to the caller's own
  department. Full design in [`user-management.md`](user-management.md).
* **The first phase where `assert_department_access` (Phase 3B.1) is
  exercised as a genuine resource-level, cross-department check** — every
  prior caller (`SYSTEM_ADMIN`) was global, so this machinery had only
  ever run against verification-only endpoints or short-circuited via the
  `SYSTEM_ADMIN` bypass. `app/services/user_service.py` uses three
  different isolation strengths depending on the action (read/lock-down
  vs. state-elevating) — see [`user-management.md`](user-management.md)
  §5.
* **The project's first authorization revocation endpoint** —
  `AuthorizationStatus.REVOKED` has existed on the enum since Phase 2 but
  was never settable until now. Creator-scoped (only the Admin who created
  an authorization may revoke it), idempotent for an already-revoked row,
  rejected for an already-used one — see
  [`user-management.md`](user-management.md) §9.
* `app/services/user_service.py`, extensions to the existing
  `UserRepository`/`UserAuthorizationRepository` (no new repository
  created, same convention Phase 3B.3 established), `app/schemas/user.py`
  — same layered architecture, reusing `require_admin` (Phase 3B.1) rather
  than adding a new dependency.
* 53 new tests against a real PostgreSQL test database, covering every
  item in the brief's Authorization/Workflow/Listing/Details/Approval/
  Deactivation/Reactivation/Revocation/Cross-Department-Security/Self-
  Protection/Lifecycle/Race-Safety lists.

### Implemented (Phase 4A review + Phase 4B — Letter Registry Core)

* **Phase 4A** confirmed the Letter Registry Core requirements against the
  existing Phase 2 schema field by field, found two requirements already
  fully satisfied with no gap (date received vs. recorded; letter content
  as text and/or document), and identified one real architectural gap —
  `Letter.department_id` could not represent both a source/sending
  department and a recipient/owning department at once. No code was
  written in 4A; `alembic check` confirmed zero drift.
* **Phase 4B** implemented the product owner's six finalized decisions
  resolving that gap and every other Phase 4A open question that had an
  answer: migration `48ec742d9e8f` split `department_id` into
  `recipient_department_id` (the isolation boundary — same field
  `assert_department_access`/`assert_letter_access` now check) and added
  `source_name`/`source_department_id` (the letter's origin, carrying no
  authorization meaning), required structured sender details, a required
  manually-entered `reference_number`, and seeded exactly three
  `Category` rows. A same-phase pre-commit hardening pass then found
  that `reference_number`'s uniqueness had been implemented as a
  *global* database constraint on an unconfirmed assumption (the
  business confirmed "must be unique", never the scope) and removed it
  (migration `c887ab35e4a3`) rather than keep or replace it with another
  guess. See [`letter-registry.md`](letter-registry.md) §2-4, §14.
* **`assert_letter_access`** (`app/services/authorization.py`) is
  `Letter`'s first-ever use of `assert_department_access` as a resource-
  level check, plus a classified-access narrowing on top —
  `Classification.restricts_access` (new column) makes a letter invisible
  to a `USER` who didn't record it, even within their own department;
  `SYSTEM_ADMIN` and `ADMIN` are never narrowed by it. Explicitly
  documented as a provisional default — the exact visibility matrix
  remains open. See [`letter-registry.md`](letter-registry.md) §8.
* `app/services/letter_service.py`, `category_service.py`,
  `classification_service.py` and their repositories/schemas/endpoints —
  the same four-layer architecture every phase since 3A has used. Category
  and Classification management (System-Admin-only CRUD) mirror
  `department_service.py`'s established pattern exactly, closing the
  "schema-only since Phase 2" gap Phase 4A identified.
* `DELETE /api/v1/letters/{id}` archives (`status -> ARCHIVED`) — never a
  physical SQL `DELETE`, continuing rather than reopening Phase 2's
  original decision.
* 67 new tests against a real PostgreSQL test database, plus a full
  live-server verification against `lrs_dev` exercising the classified-
  access boundary across every role.

### Implemented (Phase 4C — Registry Operations & Search)

* Confirmed every field requested as searchable already existed on
  `Letter` before implementation began — nothing invented. See
  [`registry-search.md`](registry-search.md) §1/§5.
* **Fixed a real architectural risk found in this phase's own
  architecture review, before adding the feature that would have
  exposed it**: the (Phase 4B) `list_letters` implementation used to
  filter classified letters *after* fetching them from the database, in
  Python — harmless while no pagination existed, but a genuine count/
  pagination leakage risk once it did.
  `app/services/authorization.py:letter_visibility_filter` moved the
  same rule into the SQL query itself, and
  `app/repositories/letter_repository.py:list_letters` derives its
  `COUNT` and paginated `items` from one identical filtered statement —
  verified by two dedicated regression tests and a live `lrs_dev` check.
  See [`registry-search.md`](registry-search.md) §1.
* Implemented pagination (`page`/`page_size`, bounded), explicit
  whitelisted sorting (`LetterSortField`/`SortOrder` enums, stable via a
  secondary id-sort), seven case-insensitive contains-match text
  filters (escaped against literal `%`/`_`), and inclusive
  `received_from`/`received_to` date-range filtering, all `AND`-
  combined — exactly the design the review recommended, `pg_trgm`/
  full-text search still not adopted.
* Added `ix_letters_reference_number` (migration `9fa970ffa560`) — the
  one index the review concluded was justified.
* 43 new tests
  (`tests/integration/test_letter_search.py`), full suite **387
  passed, 0 failed**, re-run 3 consecutive times.

### Implemented (Phase 4D — Document Management)

Built on this phase's own architecture review — see
[`document-management.md`](document-management.md) §1-32 for the
review and §33 for the full implementation record.

* **Storage foundation** — `app/services/document_storage.py`.
  `STORAGE_PATH` is resolved to an absolute path fresh on every call
  (never cached), created if missing. Every filesystem path segment is
  server-generated: `<letter_uuid>/<document_uuid>.<ext>`, with the
  extension chosen from a fixed map keyed by the already magic-byte-
  validated content type — never a client-supplied filename or
  extension. **One deliberate deviation from the review's own §7
  recommendation**: the implementation brief's literal example
  (`<letter_uuid>/<document_uuid>.<ext>`, no department/year/month
  grouping layer) was followed exactly as specified, rather than the
  review's own recommended reconciliation with the Phase 1
  department/year/month convention — see `storage/README.md`, updated
  to match what was actually built and explicit about the gap.
* **Layered file validation** — `app/services/document_validation.py`.
  Extension allowlist → size limit
  (`settings.MAX_DOCUMENT_SIZE_BYTES`, still labeled an architectural
  recommendation, not a confirmed limit) → an authoritative magic-byte
  content-signature check (hand-rolled, not a `python-magic`/libmagic
  dependency) → extension/content-type agreement. Client-supplied
  `Content-Type` is read but never trusted by any validation decision.
* **Authorization chain (CRITICAL) — reused, not duplicated.**
  `DocumentService` resolves and authorizes the parent Letter via the
  existing `LetterService.get_letter` (which already applies
  `assert_letter_access` — [`authorization.md`](authorization.md)) before
  ever touching a document; a thin `assert_document_access` delegate was
  also added to `app/services/authorization.py` for any future caller
  holding an already-loaded `LetterDocument`. Classified-letter
  protection extends to its documents automatically, by construction —
  live-verified against `lrs_dev` (a non-recording USER denied a
  classified letter's documents with the identical `404` a nonexistent
  one gets; a SYSTEM_ADMIN retains full cross-department access, per the
  brief's explicit instruction not to invent a separate document
  permission hierarchy).
* **Deletion policy (CRITICAL) — implemented exactly as recommended,
  the one recommendation with zero deviation.** No document deletion
  endpoint exists, physical or soft — `grep` for `@router.delete` in
  `app/api/v1/endpoints/documents.py` returns nothing. Uploading again
  simply adds another `LetterDocument`; nothing removes a prior one.
* **Retrieval** — `GET /api/v1/letters/{letter_id}/documents` (metadata
  list, no `storage_path` field on the response — `LetterDocument`'s
  equivalent of never serializing `password_hash`) and
  `GET .../{document_id}` (binary download, streamed via Starlette's
  `FileResponse`; `Content-Type` always the server-validated
  `mime_type`; the download filename sanitized against header
  injection; `X-Content-Type-Options: nosniff` on every response).
* **Write-then-commit failure handling** — the file is written to its
  final path before the database row is committed; a DB failure after a
  successful write rolls back and deletes the now-orphaned file as
  compensation (directly tested, not just asserted).
* **Zero schema change** — `LetterDocument` is untouched; `alembic
  check` confirms zero drift both before and after this phase. The
  review's own `checksum_sha256` recommendation was explicitly not
  implemented, per the brief's own instruction.
* 38 new tests
  (`tests/integration/test_document_management.py`), full suite **425
  passed**, re-run 3 consecutive times, plus a live-server verification
  against `lrs_dev` (upload/download round-trip, cross-department and
  classified-access denial, SYSTEM_ADMIN cross-department access, MIME
  spoofing rejection, no `storage_path` leakage, no unauthenticated
  access) — all test data removed afterward.

### Implemented (Phase 4E — Operational Activity, Notifications & Audit)

Built on this phase's own architecture review — see
[`audit-notifications.md`](audit-notifications.md) §1-30 for the review
and §31 for the full implementation record.

* **Audit foundation** — `app/services/audit_service.py:AuditService.record`,
  the single, reusable service-level audit-write mechanism (no event
  bus, no SQLAlchemy event listeners). Append-only by construction — no
  `update`/`delete` method exists on `AuditLogRepository`, and no
  audit-mutation endpoint exists anywhere (confirmed by a dedicated test
  hitting a plausible audit URL and getting `404`/`405`).
* **Mandatory, same-transaction (CRITICAL)** — `record` only `flush()`es,
  never `commit()`s/`rollback()`s; the caller's own existing
  `session.commit()` is what makes a write failure fail the whole
  operation. Proven, not just asserted: a dedicated test forces
  `AuditService.record` to raise and confirms the triggering Letter
  creation never survives a rollback.
* **Actor vs. target, enforced structurally** — every audited service
  method takes an explicit `actor_id`/caller parameter, never inferring
  it from the target resource; four `AdminService` methods that
  previously received no caller identity at all now do
  (`approve_admin`, `deactivate_admin`, `reactivate_admin`,
  `change_admin_department`).
* **Targeted old/new values only** — e.g.
  `LETTER_CLASSIFICATION_CHANGED` stores only `classification_id`;
  general edits store `{"changed_fields": [...]}"` (field *names*, never
  values). Verified a Letter's `text_content` and a User's
  `password_hash` never appear in any audit row.
* **Wired into Letter, Document, User, Admin, Department, Category,
  Classification, and Authorization lifecycle events** — exactly the
  events named in the implementation brief, no more; "Letter recipient
  department changed" and User "department changed" were confirmed
  (again) not to exist as operations and were not invented.
* **Notification foundation** — `app/services/notification_service.py`,
  the one CONFIRMED V1 trigger (a letter registered), wired into
  `LetterService.create_letter`. Recipient strategy — the recipient
  department's ACTIVE Admins — remains an explicit PROVISIONAL default,
  not promoted to confirmed by having been built.
* **Best-effort via a real `SAVEPOINT` (CRITICAL)** — wrapped in
  `session.begin_nested()`, the same mechanism `tests/conftest.py`'s
  `db_session` fixture already used for an analogous reason. Proven
  against a failure genuinely inside the savepoint (the repository's own
  `create()` forced to raise, not the whole method replaced): the Letter
  and its audit row still commit, and the failure is logged at
  `WARNING`.
* **Generic notification content (CRITICAL)** — `message` never
  interpolates Letter subject/content; verified with a deliberately
  sensitive test subject that never appears in the generated text.
* **`GET/PATCH /api/v1/notifications*`** — list (paginated), unread
  count, mark-read (idempotent), mark-all-read — every route
  unconditionally scoped to `current_user`, for every role including
  `SYSTEM_ADMIN`; a mismatched notification id 404s, matching the
  enumeration-resistant shape already established for Letters and
  Documents.
* **Zero schema change** — `alembic check` confirms zero drift both
  before and after this phase.
* 33 new tests
  (`tests/integration/test_audit.py`, `test_notifications.py`), full
  suite **458 passed**, re-run 3 consecutive times, plus a live-server
  verification against `lrs_dev` (letter registration → audit row +
  per-Admin notifications; cross-Admin notification denial; mark-read/
  read-all isolation; unauthenticated denial) — all test data removed
  afterward.

### Reviewed (Phase 5 — Frontend & Operational UI)

Full design in [`frontend.md`](frontend.md). At the time of this review,
no frontend code existed — `frontend/src/App.jsx` still rendered only a
static Phase 1 placeholder; see "Implemented (Phase 5A)" immediately
below for what changed since.

* **Inspected the actual current state, not assumed** — confirmed the
  frontend stack is already chosen (React 18.3.1, Vite 5.3.1,
  react-router-dom 6.24.0, axios 1.7.2, all in `package.json`) but
  completely unwired (no router mounted, no HTTP service module, no
  state management, no CSS framework, no test framework); mapped all 42
  real backend endpoints (verified via the live OpenAPI schema, not
  memory) to screens by role.
* **One gap found in the task's own suggested System Admin nav
  structure** — it omitted Letters/Documents, but `SYSTEM_ADMIN` is
  confirmed to have full cross-department Letter/Document read/update/
  archive access (it just cannot create one); recommended adding a
  System Admin Letters screen rather than silently following an
  incomplete suggestion.
* **Classified Letter UX (CRITICAL)** — the frontend must never
  independently filter, label, or infer classified-letter existence; it
  renders exactly what the API returns (`items`/`total` already exclude
  inaccessible letters at the query level — Phase 4C) and treats every
  `404` identically, with no distinguishing language.
* **A real, unresolvable-without-a-backend-change gap identified**: the
  frontend cannot proactively detect that a caller's own department has
  gone `INACTIVE` (no field exposes department status to the caller) —
  only reactively, via a `403` on the next action.
* **Two error-body shapes exist and must both be handled** — a plain
  `{"detail": "<string>"}` for raised `HTTPException`s vs. FastAPI's own
  array-shaped `{"detail": [...]}` for Pydantic validation failures — a
  precise, previously-undocumented integration detail this review
  surfaced by reading the actual endpoint code, not assumed.
* **Document downloads require the same bearer auth as every other
  endpoint** — no plain `<a href>` can carry it; recommended fetch +
  blob URL, with "open in a shareable new-tab URL" flagged as a real V1
  limitation, not silently worked around.
* Recommended keeping the stack exactly as installed — no React Query,
  no state-management library, no CSS/UI framework — at V1 scale, per
  this review's own repeated "don't add complexity without a
  demonstrated need" instruction. A route/component/API-client
  architecture and a prioritized test strategy were both designed, not
  implemented at review time. No frontend or backend file was touched
  during the review.

### Implemented (Phase 5A — Frontend Foundation)

Built directly on Phase 5's own review, above — no new architecture
decisions were made, only the ones already recommended were built.

* **Routing wired up** — `react-router-dom` (installed since Phase 1,
  unused until now) now backs a real route tree
  (`frontend/src/routes/index.jsx`): `/`, `/login`, `/signup`, and a
  `/app` subtree gated by `ProtectedRoute`, matching §19's design.
* **`AuthContext`** — the single authentication state mechanism (§22),
  `status: 'loading' | 'authenticated' | 'unauthenticated'`, `user`
  always the `UserPublic` object most recently returned by
  `POST /auth/login` or `GET /auth/me` — never decoded from the JWT.
  Session restoration validates any stored token against `/auth/me`
  before any protected route renders (§9), avoiding an authentication
  flicker.
* **One centralized Axios client** (§21) — the auth header, both
  confirmed backend error-body shapes normalized into one predictable
  `{status, message, fieldErrors}`, and a single 401 handler that clears
  the session and lets `ProtectedRoute` redirect — except on the
  login/signup/session-restore calls themselves, which opt out
  (`skipAuthRedirect`) and handle their own 401/403 locally, exactly as
  the review specified.
* **Token storage isolated to one module** (`services/tokenStorage.js`)
  — `localStorage` for V1, documented in `frontend/README.md` as the
  same PROVISIONAL placeholder §28 named, not silently promoted to a
  final decision.
* **`ProtectedRoute` (authentication only) and `RoleGuard` (role-based
  navigation convenience only) as two separate components** — matching
  §12's explicit instruction not to conflate the two; neither provides
  real security, which remains entirely backend-enforced.
* **Role-derived navigation** (`navigation/navigationConfig.js`) — data
  only, matching §13's per-role lists exactly (including the System
  Admin Letters/Documents addition §6 identified), never a department id
  anywhere in it.
* **`AppShell`/`Sidebar`/`Topbar`** (§14) — current user's identity, role
  indicator, logout control, and role-derived nav, with every unbuilt
  destination rendering one shared `PlaceholderPage`, not a one-off stub
  per screen.
* **A small design-token set** (§26) — CSS Modules + `styles/tokens.css`,
  no UI framework added, exactly as recommended.
* **An accessibility baseline** (§25) — semantic nav/buttons, visible
  focus states, associated form labels, `role="status"`/`role="alert"`
  on the loading/error primitives.
* **Test infrastructure established** (§30) — none existed before;
  Vitest + React Testing Library now do, with 17 tests covering
  authentication state transitions, protected-route behavior, role
  navigation configuration, and API error normalization, exactly the
  four areas §30/the implementation brief named as the minimum.
* **No feature screen exists** — Letters, Documents, Notifications, and
  every administrative screen remain the one shared placeholder; no
  dashboard, no audit UI. No backend file was touched — confirmed by
  `git status` and a full backend regression run (458 passed,
  unaffected) before and after.

### Implemented (Phase 5B — Authentication & Account UX)

Built directly on Phase 5A's foundation, above — turns the minimal
`LoginPage`/`SignupPage` into the complete V1 authentication/account
experience; still no business feature screen.

* **Production `LoginPage`/`SignupPage`** — client-side required-field
  and email-format validation (`utils/formValidation.js`, no form
  library), `aria-invalid`/`aria-describedby` wiring every field to its
  own error, a disabled submit button with a loading label while a
  request is in flight, and the previous error cleared the instant a new
  submission begins. Server-side validation remains authoritative.
* **`PendingApprovalNotice`/`DeactivatedAccountNotice`** — two new
  reusable components rendered in place of the form. Both state only
  what the backend confirms — no invented approval timeline, no invented
  administrator contact, no implication a deactivated account was
  deleted. `DeactivatedAccountNotice` has no "logout" action because
  there is no scenario where the frontend can show it to an
  already-authenticated user — the backend's distinct deactivation
  message is raised only by `POST /auth/login`; a mid-session
  deactivation surfaces as a generic `401`, already handled centrally.
* **Session restoration now distinguishes *why* `GET /auth/me` failed**
  — a definite rejection still clears the stored token; a network
  failure does not (the credential might still be valid), and instead
  surfaces a retry-capable banner via a new `restoreError`/
  `retryRestoreSession` pair on `AuthContext` — a server outage is never
  silently treated as a successful authenticated state, matching the
  same discipline §9/§22 already established for the definite-rejection
  case.
* **A real Phase 5A gap closed**: `SignupPage` gained the same
  already-authenticated → redirect guard `LoginPage` already had.
* **A design tension resolved by re-reading the backend, not guessed**:
  whether `AuthContext.login()` should make a separate `/auth/me` call
  after login. It doesn't — `POST /auth/login`'s own `TokenResponse.user`
  is already the identical, freshly-queried, backend-authoritative
  `UserPublic` object a follow-up call would return, so no redundant
  round trip was added. The actual governing rule — never derive
  authorization from decoded JWT claims — was already satisfied (no
  JWT-decoding code exists anywhere in this codebase) and remains so.
* **Test suite grown from 17 to 44 tests** — new coverage for both
  forms' every UX state (success, invalid credentials, pending,
  deactivated, validation, loading, network failure), the exact signup
  payload shape sent to the backend (proving `role`/`department_id`/
  `status` can never be injected), session-restoration network failure
  and its retry, and an end-to-end logout → `/login` redirect test.
* **No backend file was touched** — confirmed by `git status` and a full
  backend regression run (458 passed, unaffected) before and after.
* **Logout remains purely client-side** — no server-side revocation
  endpoint exists or was added; an already-issued JWT stays valid until
  it naturally expires. Documented as an accepted V1 limitation, not a
  defect.

### Implemented (Phase 5C — Core Registry UI)

Built directly on Phase 5A's foundation and Phase 5B's authentication
UX, above — the `/app/letters` and `/app/system/letters` placeholders
are now a complete V1 Letter registry.

* **List/search/sort/pagination** — one `LetterListPage` mounted at both
  routes, adapting to `user.role` rather than duplicating pages. The
  seven confirmed text filters, `status`, and an inclusive received-date
  range are available to every role; sorting covers all four
  backend-whitelisted fields. Filter/sort/page state lives in the URL
  (`useSearchParams`), so refresh, back/forward, and bookmarking all
  preserve registry state. Pagination renders the backend's own
  `page`/`page_size`/`total`/`total_pages` — never recomputed
  client-side.
* **CONFIRMED backend-contract gap found and resolved, not routed
  around**: `GET /api/v1/categories`/`/classifications`/`/departments`
  are all `require_system_admin`-only, but `POST /api/v1/letters`
  structurally excludes SYSTEM_ADMIN — no role that can create/edit a
  Letter can ever load those reference-data lists. `category_id`/
  `classification_id` never appear on Create (any role); on Edit they
  appear only for SYSTEM_ADMIN. Nothing was hardcoded as a workaround —
  confirmed by grep, zero category/classification/department names
  appear anywhere outside test fixtures.
* **Classified-record safety, re-verified against this implementation
  (CRITICAL)** — `items`/`total` render exactly as the backend returns
  them; a `404` on a Letter — nonexistent, wrong-department, or
  classified-and-inaccessible, all three collapsed identically by the
  backend — renders the same generic "Letter not found," verified by a
  test asserting the rendered text contains neither "classif" nor
  "permission."
* **Create/edit/archive** — one `LetterFormPage` for both create and
  edit, field set matching `LetterCreate`/`LetterUpdate` minus the
  documented category/classification gap and a deliberate
  `source_department_id` scope simplification. Archive
  (`ArchiveConfirmDialog`) never says "delete" or "permanent" —
  `DELETE /api/v1/letters/{id}` is confirmed, from the endpoint's own
  summary, to be a soft status transition, never physical deletion.
* **Role-aware UX** — USER and ADMIN treated identically, matching
  `LetterService`'s own docstring ("USER and ADMIN share identical
  access within their own `recipient_department_id`"); SYSTEM_ADMIN gets
  a resolved Department column and no create action, matching
  `POST /letters`'s own `require_user_or_admin` dependency.
* **Test suite grown from 44 to 84 tests** — new coverage for list
  success/empty/error/pagination/filter-reset/clear/sort, classified-404
  safety, create/edit validation and exact payload shape (proving
  `recipient_department_id`/`recorded_by`/`status` can never be
  injected), archive confirmation and non-permanent wording, and
  role-based UI differences.
* **No backend file was touched** — confirmed by `git status` and a full
  backend regression run (458 passed, unaffected) before and after.

### Implemented (Phase 5D — Administration & Account Management UI)

Built directly on Phase 5D's own architecture review
([`administration-ui.md`](administration-ui.md)) — no new architecture
decisions, only the ones already recommended, built.

* **Department management** (SYSTEM_ADMIN) — list/create/detail with
  inline edit, activate (unconfirmed, purely restorative)/deactivate
  (confirmed, explains the operational impact on every Admin/User in
  that department).
* **Administrator management** (SYSTEM_ADMIN) — list (status +
  department filters), a dedicated Authorize form, and a detail page
  whose actions are entirely status-gated per the backend's own
  lifecycle: Approve (confirmed, not idempotent), Deactivate + Transfer
  (`ACTIVE` only), Reactivate (`DEACTIVATED` only, not confirmed).
* **Admin department transfer** — states verbatim, using the backend's
  own confirmed guarantee, that historical Letters are never
  reassigned; destination limited to `ACTIVE` departments.
* **User management** (ADMIN, own department only) — list, a
  single-field Authorize form (`UserAuthorizationCreate` has no
  `department_id` at all — the strongest possible structural guarantee
  against department-injection for this form), a separate department-
  wide Authorizations list with creator-scoped Revoke, and a detail page
  with the same status-gated action set as Admins, one level down.
* **The backend's read/lock-down vs. state-elevating asymmetry
  preserved, not flattened** — a `403` on User Approve/Reactivate is
  phrased around the *Admin's own* department, never the target
  account; Deactivate (which can never return that `403`) shows no such
  warning. Verified by a dedicated test.
* **System Admin protection and Admin self-targeting prevention are
  both structural** — confirmed directly in the backend's own
  role-filtered repository lookups (`find_admin_by_id`/
  `find_user_by_id`); no endpoint can ever resolve a SYSTEM_ADMIN id or
  an Admin's own id, so no frontend check exists for either case.
* **Every confirmed backend gap respected, not routed around** — no
  pagination/search/sort UI (none exists on any of the four resources);
  no department field on the User authorization form; no revoke action
  for Admin-purpose authorizations (no such endpoint exists); no
  department/admin/user counts anywhere (no such field exists).
* **Test suite grown from 84 to 159 tests**, run 3 consecutive times
  with identical results.
* **No backend file was touched** — confirmed by `git status` and a full
  backend regression run (458 passed, unaffected) before and after.

### Reviewed, then implemented (Phase 5E — Documents & Notifications UI)

Full design in [`document-notification-ui.md`](document-notification-ui.md).
`documents.py`/`document_service.py`/`document_storage.py`/
`document_validation.py` and `notifications.py`/
`notification_service.py`/`notification_repository.py` were all
re-read fresh and confirmed byte-for-byte unchanged since Phase 4D/4E.

* **Confirmed, precisely, why a document download needs an
  authenticated fetch, not a plain `<a href>`** — the same Bearer-token
  requirement every endpoint in this system has; `Content-Disposition:
  attachment` is set automatically by the backend's own `FileResponse`
  call whenever a `filename` is passed, forcing a real download once
  fetched as a blob.
* **Confirmed the document lifecycle is upload-only** — no replace, no
  delete, no per-document archive concept; "replacement" is simply
  uploading again, leaving the prior document row and file completely
  untouched.
* **Confirmed the one generated notification message is safe to render
  as plain text** — a fixed, server-authored template with exactly one
  non-sensitive interpolated value (a Letter's reference number), never
  the Letter's subject/content/classification.
* **A real, previously-undocumented interaction found**: a
  notification's Letter link can still 404 if the recipient's own
  access changed since the notification was generated (e.g. an Admin
  department transfer, Phase 5D's own confirmed instant-effect
  behavior) — documented as expected, identically-rendered 404
  behavior, never a distinguishing message.
* **Confirmed notification recipient isolation is structural** — no
  endpoint anywhere accepts a `recipient_user_id` parameter; every
  read/write is scoped to the caller's own id at the query level.
* Full component (`DocumentList`/`DocumentUploadForm`,
  `NotificationBell`/`NotificationPanel`/`NotificationItem`), service
  (`documentService.js`/`notificationService.js`), route (no new route
  for Documents; `/app/notifications` fills an already-slotted
  placeholder), error-handling, accessibility, a 15-item security
  threat review, and a test plan were all designed during the review.
  No frontend or backend file was touched during the review itself.

**Then implemented, same phase, second pass** — every component/
service/route above was built exactly as designed, with no new
architecture decisions:

* **Documents** — `DocumentUploadForm` (client-side pre-checks only,
  explicitly labeled as UX, never authoritative) and `DocumentList`
  (metadata + Download only — no Delete/Replace/Archive, because no
  such endpoint exists) integrated directly into `LetterDetailPage`,
  replacing its prior placeholder. Download uses an authenticated blob
  fetch through the existing API client, never a plain `<a href>`.
* **Notifications** — `NotificationBell` in the existing `Topbar`
  polls `GET /notifications/unread-count` only, every 60 seconds
  (`PROVISIONAL`), paused while the tab is hidden; `NotificationPanel`
  (dropdown) and `NotificationsPage` (`/app/notifications`, real
  pagination via Phase 5C's `Pagination` component) both share one
  `NotificationItem`. Mark-read is **explicit-button-only** — clicking
  a notification's Letter link never marks it read, an explicit
  override of this review's own PROVISIONAL "mark on navigate" lean,
  applied deliberately rather than silently.
* **No frontend authorization rule was added anywhere** — a document
  or notification-linked Letter that is inaccessible renders the same
  generic `404` this project has used since Phase 4B/5C, with nothing
  in the frontend attempting to explain why.
* **Test suite grown from 159 to 225 tests**, run 3 consecutive times
  with identical results and clean stderr output.
* **No backend file was touched** — confirmed by `git status` and a
  full backend regression run (458 passed, unaffected) before and
  after. Full implementation record: `document-notification-ui.md`
  §27.

### Explicitly deferred (not yet implemented)

* **Document deletion for `LetterDocument`** — a deliberate Phase 4D
  scope decision (see [`document-management.md`](document-management.md)
  §14), not a gap: `LetterDocument` has no lifecycle/status field to
  soft-delete into, and no requirement confirms deletion is needed.
* **The exact classification value list and the exact classified-
  visibility matrix** — both deliberately left open by the product owner;
  see [`letter-registry.md`](letter-registry.md) §12.
* System Admin handover.
* **Dashboards** — not implemented; see
  [`audit-notifications.md`](audit-notifications.md) §20 for where a
  future dashboard should read from.
* **An audit-viewing/read API** — `AuditLog` is now written to (Phase
  4E), but nothing exposes it through the API; a deliberate scope
  decision (§9 of that doc), not a gap — the access-control question
  (SYSTEM_ADMIN-only vs. department-scoped ADMIN) is deliberately left
  PENDING.
  See [`authorization.md`](authorization.md) §12,
  [`department-management.md`](department-management.md) §10,
  [`admin-management.md`](admin-management.md) §13,
  [`user-management.md`](user-management.md) §12,
  [`letter-registry.md`](letter-registry.md) §13, and
  [`document-management.md`](document-management.md) §25 for each prior
  phase's own historical planned-event list — all now implemented via
  [`audit-notifications.md`](audit-notifications.md) §31, not a sixth
  competing list.
* **Notification triggers beyond "letter registered"** — the one
  CONFIRMED V1 trigger is implemented; document upload, classification/
  category changes, and User/Admin/Department lifecycle notifications
  all remain unimplemented, exactly as
  [`audit-notifications.md`](audit-notifications.md) §12 recommends
  deferring until confirmed.
* Full frontend authentication/authorization/department/Admin/User/
  Letter-management UI — deliberately deferred, see
  [`authentication.md`](authentication.md) §15; unchanged this phase.
* **A revoke endpoint for ADMIN-purpose `UserAuthorization` rows** — Phase
  3B.4 added revocation only for USER-purpose authorizations; see
  [`user-management.md`](user-management.md) §12, "Known limitations".

See `docs/PROJECT_STATUS.md` for the current phase-by-phase plan and what's
pending S&IT confirmation before some of these can be designed.

## 5. Layering rule (unchanged from Phase 1)

```text
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. Phase 2 added the bottom of this stack
(the ORM models). Phase 3A populated every other layer for the first time
— `app/api/v1/endpoints/auth.py` (thin, translates service exceptions to
HTTP), `app/services/auth_service.py` / `bootstrap_service.py` (business
rules, transaction boundaries), `app/repositories/user_repository.py` /
`user_authorization_repository.py` (the only code that queries `User`/
`UserAuthorization`). Phase 3B.1 added one more layer explicitly named in
the brief — "Dependencies / Authorization", sitting between API and
Services — populated by `app/api/deps.py`'s role-check dependencies and
`app/services/authorization.py`'s framework-agnostic department rule.
Phase 3B.2 added a second full vertical slice through every layer for a
new resource (`app/api/v1/endpoints/departments.py` →
`app/services/department_service.py` →
`app/repositories/department_repository.py`), reusing the Phase 3B.1
authorization layer rather than duplicating its checks. Phase 3B.3 adds a
third slice (`app/api/v1/endpoints/admins.py` →
`app/services/admin_service.py`) that deliberately does **not** add a
fourth repository — it extends the existing `UserRepository`/
`UserAuthorizationRepository` instead, since Admin accounts are `User`
rows and Admin authorizations are `UserAuthorization` rows; a dedicated
`AdminRepository` would have queried the same two tables a second way for
no benefit. Phase 3B.4 adds a fourth slice
(`app/api/v1/endpoints/users.py` → `app/services/user_service.py`) on the
same principle — regular User accounts and their authorizations are the
same two tables again, so this phase extends `UserRepository`/
`UserAuthorizationRepository` a second time rather than adding a fifth
repository. Phase 4B adds three more full vertical slices for genuinely
new resources — `app/api/v1/endpoints/letters.py` →
`app/services/letter_service.py` → `app/repositories/letter_repository.py`,
plus `categories.py`/`category_service.py`/`category_repository.py` and
`classifications.py`/`classification_service.py`/`classification_repository.py`
— the first new repositories since Phase 3B.2, because `Letter`/
`Category`/`Classification` are genuinely distinct tables, not another
view onto `User`/`UserAuthorization` the way Admin/User management were.
All of it uses this same structure rather than inventing a second one,
per the brief's explicit instruction in every phase so far.
