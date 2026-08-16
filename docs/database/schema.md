# Database Schema — Phase 2 Core Models

**Status:** Phase 2 complete, including a corrective hardening pass from a
self-review. This document describes the schema as implemented by
SQLAlchemy models in `backend/app/models/` and two Alembic migrations
(`backend/alembic/versions/`): `3da4b7ee8167` (baseline) and `e8a5cea2ccc6`
(hardening — two missed indexes and a database-level default; see §1,
"ORM deletion behavior" and §6, "Indexes"). No API, service, or repository
layer exists yet — this is the data layer only.

For the roles/hierarchy this schema supports, see
[`docs/architecture/overview.md`](../architecture/overview.md).

---

## 1. Conventions used throughout this schema

### UUID strategy

Every table's primary key is a `UUID`, generated **client-side** in Python
(`uuid.uuid4()`, via `app/models/mixins.py:UUIDPrimaryKeyMixin`) rather than
by a PostgreSQL server-side default. This was chosen over
`gen_random_uuid()`/`uuid_generate_v4()` so the schema does not depend on the
`pgcrypto` or `uuid-ossp` extension being installed and enabled in every
environment — a plain PostgreSQL install works with no extra setup. The
tradeoff is that a row inserted by raw SQL (outside the ORM) must supply its
own UUID; this schema does not currently need that path.

### Timestamp strategy

Every timestamp column is **timezone-aware**
(`sqlalchemy.DateTime(timezone=True)`, which PostgreSQL stores as
`timestamptz`). Naive datetimes are never used anywhere in this schema.
`created_at`/`updated_at` pairs (`app/models/mixins.py:TimestampMixin`) use a
database-side `server_default=func.now()` (and `onupdate=func.now()` for
`updated_at`), so the value is correct even for a row written outside the
ORM — application code never needs to set these.

`received_at` (Letter) and `uploaded_at` (LetterDocument) are business facts,
not audit metadata, so they are **not** defaulted to "now" — they must be
supplied explicitly and represent when something actually happened in the
real world.

### Enums

Every constrained-choice field (`role`, account `status`, letter `status`,
authorization `status`, and the shared active/inactive `status` used by
Department/Category/Classification) is a **native PostgreSQL `ENUM` type**,
not a plain string with application-side validation. See
`app/models/enums.py`. This means the database itself rejects a value that
isn't one of the defined labels — "arbitrary role strings" are not
possible even if a bug or a future raw-SQL script tries to insert one.

The `active_status` type (`ACTIVE`/`INACTIVE`) is intentionally **shared**
across Department, Category, and Classification rather than declared three
times, because all three mean exactly the same thing: this reference entity
is currently usable or retired. The type is defined once, as a single Python
object, and reused — see the comment in `app/models/enums.py` for why that
matters for migration correctness (it avoids duplicate `CREATE TYPE`
statements).

### Never physically deleted

Department, User, Category, and Classification rows are **never physically
deleted** by this schema's design — each has a `status` enum with an
inactive/deactivated value instead. This is not just a convention; it is why
every foreign key pointing at these four tables uses `ON DELETE RESTRICT`
(see §5) — the database itself refuses a delete that would orphan historical
records, as defense in depth beyond "the application just doesn't expose a
delete button."

### Model import and registration strategy

`app/database/base.py` defines `Base` and nothing else — it does not import
`app.models`. Each model module imports `Base` *from* `app.database.base`,
which is a one-directional dependency (`app.models.*` → `app.database.base`,
never the reverse). An earlier version of `base.py` also imported every
model at its own bottom "so Alembic can see them", which created a genuine,
order-dependent circular import: `from app.models import User` (or `from
app.models.user import User`) as the first touch of either module in a
fresh interpreter raised `ImportError: cannot import name 'X' from partially
initialized module 'app.models'`. It only appeared to work because every
entry point in this repository happened to import `app.database.base`
before ever touching `app.models`.

Code that needs every model registered on `Base.metadata` — `alembic/env.py`
and `tests/conftest.py` are the two that currently need this — imports
`app.models` itself, explicitly, in addition to importing `Base`:

```python
from app.database.base import Base
import app.models  # noqa: F401 — registers every model on Base.metadata
```

`tests/unit/test_imports.py` guards against regressing this: it runs
`from app.models import X` and `from app.models.user import X` in genuinely
fresh subprocesses (a same-process import would be contaminated by whatever
conftest.py already imported, and wouldn't reproduce the bug).

### ORM deletion behavior

Every one-to-many relationship whose child foreign key is `RESTRICT` (or, in
one case, `SET NULL`) is declared with `passive_deletes="all"` — e.g.
`Department.users`, `Department.letters`, `Category.letters`,
`User.letters_recorded`, `User.audit_logs`. Without it, SQLAlchemy's default
behavior when the "one" side of such a relationship is deleted is to load
the child collection (if not already loaded) and issue an `UPDATE ... SET
<fk> = NULL` for each child *before* the parent's `DELETE` — attempting to
orphan the children rather than trusting the database's own foreign-key
action. For `Department.users` specifically, that attempted `UPDATE` used to
fail against the unrelated `ck_users_role_department_pairing` CHECK
constraint (every user reachable via `department.users` is, by construction,
ADMIN or USER — exactly the roles that constraint requires a department
for), so a delete was still blocked, but by a confusing error that had
nothing to do with the actual foreign key relationship, and — for other,
nullable-FK relationships elsewhere in the schema — this same default
behavior could have silently set a child's FK to NULL instead of leaving
the RESTRICT to do its job at all.

`passive_deletes="all"` (not the weaker `passive_deletes=True`) tells
SQLAlchemy: do not load or act on this collection during a parent delete
under any circumstances, even if it's already loaded in the session —
trust the database's `ON DELETE` action entirely. This is the documented
SQLAlchemy pattern for exactly this scenario ("typically used when a
triggering or error raise scenario is in place on the database side"). The
one relationship that does **not** use it is `Letter.documents`, which has
ORM-level `cascade="all, delete-orphan"` instead (SQLAlchemy rejects
combining `passive_deletes="all"` with `delete`/`delete-orphan` cascade) —
each `LetterDocument` is a true owned child with no life of its own, so the
ORM actively managing its deletion (including when removed from the
collection without deleting the parent `Letter`) is the *intended* behavior
there, not the bug this fix addresses.

One consequence worth knowing: because `passive_deletes="all"` means the
ORM never touches the child collection, an object already loaded into a
session's identity map before its row is cascade-deleted by the database
(e.g. `Notification.letter_id` → `ON DELETE CASCADE`) will not be
automatically expunged or refreshed — `session.get(...)` on it returns the
stale in-memory copy until the session is expired or a fresh session is
used. `tests/integration/test_models.py::test_letter_deletion_cascades_documents_and_notifications`
calls `db_session.expire_all()` before asserting this, and documents why.

See `tests/integration/test_models.py` (sections "ON DELETE RESTRICT —
Department", "ON DELETE RESTRICT — User", "ON DELETE CASCADE — Letter") for
the regression tests, all run against a real PostgreSQL instance.

---

## 2. Tables

### 2.1 `departments`

The isolation boundary the whole system is built around — see
[Department isolation](../architecture/overview.md#department-isolation) in
the architecture doc.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `name` | varchar(255), NOT NULL, UNIQUE | |
| `code` | varchar(50), UNIQUE, nullable | S&IT has not confirmed a coding convention — see §7 |
| `status` | `active_status` enum, NOT NULL, default `ACTIVE`, indexed | Index added in `e8a5cea2ccc6` — Category and Classification already indexed their equivalent `status` column; Department, arguably the most-filtered "active/inactive" table, had been missed |
| `created_at` / `updated_at` | timestamptz | |

`code` is nullable *and* unique: PostgreSQL treats multiple `NULL`s in a
unique column as distinct from one another, so any number of departments may
go without a code at once.

### 2.2 `users`

A person with an LRS account. See
[System Admin / Admin / User](../architecture/overview.md#roles) for what
each role means.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `full_name` | varchar(255), NOT NULL | |
| `email` | varchar(320), NOT NULL | Uniqueness enforced by a functional index, not a plain column constraint — see below |
| `password_hash` | varchar(255), NOT NULL | No plaintext password column exists anywhere in this schema. Nothing computes this value yet — that is Phase 3+ (`app/core/security.py`) |
| `role` | `user_role` enum, NOT NULL | `SYSTEM_ADMIN` \| `ADMIN` \| `USER` |
| `department_id` | UUID, FK → `departments.id` ON DELETE RESTRICT, nullable | NULL only for `SYSTEM_ADMIN` — enforced by a CHECK constraint, see below |
| `status` | `user_status` enum, NOT NULL, default `PENDING_APPROVAL` | `PENDING_APPROVAL` \| `ACTIVE` \| `DEACTIVATED` |
| `created_at` / `updated_at` | timestamptz | |

**Case-insensitive unique email.** Rather than a plain `UNIQUE` constraint on
`email` *plus* separate case-insensitive comparison logic, this schema uses
a single PostgreSQL functional unique index:

```sql
CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));
```

This is the one source of truth for "is this email already registered" —
`alice@example.gov` and `ALICE@example.gov` collide, and the database
enforces that at write time. `citext` was considered and rejected: it would
require enabling a PostgreSQL extension for a problem a plain functional
index already solves without any extra dependency (the instruction was
explicitly "do not overengineer this if it introduces unnecessary
complexity").

**Role/department pairing.** A `CHECK` constraint enforces the rule from the
brief — "ADMIN and USER must have a department, SYSTEM_ADMIN must not" — at
the database level:

```sql
CONSTRAINT ck_users_role_department_pairing CHECK (
  (role = 'SYSTEM_ADMIN' AND department_id IS NULL)
  OR (role IN ('ADMIN', 'USER') AND department_id IS NOT NULL)
)
```

This constraint only protects a row's column values at write time. A
multi-step workflow such as "promote this user to SYSTEM_ADMIN and clear
their department" is a transaction the constraint cannot express or
validate holistically — that belongs in the service layer in a later phase,
as the brief anticipated.

In the model (`app/models/user.py`), this constraint's condition string is
built from `UserRole.SYSTEM_ADMIN.value` / `.ADMIN.value` / `.USER.value`
rather than typed-out literals, so it can't silently drift from the enum —
the compiled SQL is identical either way (`role = 'SYSTEM_ADMIN' ...`), this
just removes one place a rename could go unnoticed. The Alembic migration
that created this constraint still contains its own literal copy of the
same text, deliberately: migrations are frozen, self-contained snapshots
(see the baseline migration's own docstring), not live references to
`app/models/enums.py`. If `UserRole` ever changes, both the model's
condition *and* a new corrective migration need updating by hand — there's
no mechanism that does both from one edit, and there shouldn't be, since a
new role isn't guaranteed to simply join the existing ADMIN/USER bucket.
`tests/integration/test_models.py::test_role_department_pairing_constraint`
is parametrized over all six role/has-department combinations, so a role
added without updating this constraint surfaces as a failing test.

### 2.3 `user_authorizations`

A pre-approval that a given email may sign up, for a given department. **Not
the same thing as a `User`** — see the model docstring
(`app/models/user_authorization.py`) and §8 below for why this is a separate
table.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `email` | varchar(320), NOT NULL | Not unique — see below |
| `department_id` | UUID, FK → `departments.id` ON DELETE RESTRICT, NOT NULL | |
| `authorized_by` | UUID, FK → `users.id` ON DELETE RESTRICT, NOT NULL | Must eventually be an ADMIN — service-layer rule, not a DB constraint (see below) |
| `status` | `authorization_status` enum, NOT NULL, default `ACTIVE` | `ACTIVE` \| `USED` \| `REVOKED` |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz, nullable | |

`email` has no uniqueness constraint: the same address can legitimately be
authorized, used, revoked, and re-authorized over its lifetime. Preventing
more than one *ACTIVE* authorization for the same email at once is a
service-layer rule (it depends on reading current state, not just a column
value), not a schema constraint.

The requirement that `authorized_by` must reference an ADMIN-role user is a
rule about **who is allowed to call** "authorize this email" — a workflow
permission check, not a fact derivable from the row's own columns — so it is
intentionally left for the service layer once the authorization API exists,
per the brief's own instruction ("do not enforce all role-specific business
rules only at the database layer").

### 2.4 `categories`

A subject-matter grouping for letters (e.g. Budget, HR, Legal), managed by
System Admin.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `name` | varchar(255), NOT NULL, UNIQUE | |
| `description` | text, nullable | |
| `status` | `active_status` enum, NOT NULL, default `ACTIVE` | |
| `created_at` / `updated_at` | timestamptz | |

No category values are seeded. The final list is not confirmed by S&IT — see
§7 and `docs/PROJECT_STATUS.md`.

### 2.5 `classifications`

A priority/sensitivity marker for letters (e.g. Important, Classified,
Routine) — deliberately a **separate table from Category**, not a shared
list, because the two vary independently: a "Budget" letter can be Routine
or Classified, and merging them would force every category to be
re-declared per priority level.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `name` | varchar(255), NOT NULL, UNIQUE | |
| `description` | text, nullable | |
| `status` | `active_status` enum, NOT NULL, default `ACTIVE` | |
| `created_at` / `updated_at` | timestamptz | |

Terminology is not confirmed by S&IT — see §7.

### 2.6 `letters`

The central business entity — see
[Department isolation](../architecture/overview.md#department-isolation) for
how `department_id` is meant to be used once a service layer exists.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `department_id` | UUID, FK → `departments.id` ON DELETE RESTRICT, NOT NULL | Every letter belongs to exactly one department |
| `received_from` | varchar(500), NOT NULL | Sender — free text, not assumed to always be a government department (unconfirmed by S&IT, §7) |
| `subject` | varchar(500), nullable | Useful for search; exact requirement-ness unconfirmed by S&IT (§7) |
| `reason` | text, nullable | Purpose for which the letter was received; nullable for the same reason as `subject` |
| `category_id` | UUID, FK → `categories.id` ON DELETE RESTRICT, nullable | Categorization workflow (who assigns it, when) is still being defined |
| `classification_id` | UUID, FK → `classifications.id` ON DELETE RESTRICT, nullable | Same as above |
| `received_at` | timestamptz, NOT NULL | When the *physical* letter was received — distinct from `created_at` (when the row was entered into LRS) |
| `recorded_by` | UUID, FK → `users.id` ON DELETE RESTRICT, NOT NULL | Who entered the letter into LRS |
| `text_content` | text, nullable | A letter may be represented by text instead of (or alongside) a scanned document |
| `status` | `letter_status` enum, NOT NULL, default `ACTIVE` | `ACTIVE` \| `ARCHIVED`. Archive *behavior* is not implemented — only the status value a future feature will set |
| `created_at` / `updated_at` | timestamptz | |

**No reference/letter number column exists.** Its existence and exact format
are unconfirmed by S&IT (see §7) — adding one now would mean guessing a
government numbering convention. This is a deliberate omission, not an
oversight.

**Department isolation is not enforced here.** This model does not (and, as
a single table, cannot) stop a caller from writing an arbitrary
`department_id`. Enforcing "a User can only create/see letters for their own
department" is explicitly a service-layer concern for Phase 3+, where
`department_id` will be derived from the authenticated user's session, never
accepted as client input. See
[Department isolation](../architecture/overview.md#department-isolation).

### 2.7 `letter_documents`

Metadata for one file attached to a Letter — deliberately a **separate
table**, not columns on `letters`, because a single letter may eventually
have multiple attachments; one `storage_path` column on `letters` would cap
every letter at exactly one document.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `letter_id` | UUID, FK → `letters.id` ON DELETE CASCADE, NOT NULL | See "Cascade" note below |
| `document_type` | varchar(50), nullable | Plain string, not an enum — the set of meaningful types isn't confirmed, and an unrecognized value here is harmless (unlike `role`/`status`) |
| `original_filename` | varchar(500), NOT NULL | |
| `storage_path` | varchar(1000), NOT NULL | **Relative/logical** path into `storage/letters/` (see `STORAGE_PATH` in `app/core/config.py`) — never a machine-specific absolute path |
| `file_size` | bigint, nullable | |
| `mime_type` | varchar(255), nullable | |
| `uploaded_by` | UUID, FK → `users.id` ON DELETE RESTRICT, NOT NULL, indexed | Added in the hardening migration (`e8a5cea2ccc6`) — was the one User-referencing FK in this schema without an index; every sibling (`recipient_user_id`, `audit_logs.user_id`, `user_authorizations.authorized_by`) already had one |
| `uploaded_at` | timestamptz, NOT NULL | |

This table stores **metadata only** — no binary content is stored in
PostgreSQL. Upload handling, path generation, and file I/O are entirely out
of scope for this phase; `storage_path` is just a string column until a
storage service exists to interpret it.

### 2.8 `notifications`

An in-system notification for a User. V1's only known trigger is "a letter
was registered" (per the brief), but no notification is ever generated by
this phase — that requires a future letter-registration workflow to write
these rows.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `recipient_user_id` | UUID, FK → `users.id` ON DELETE RESTRICT, NOT NULL | |
| `letter_id` | UUID, FK → `letters.id` ON DELETE CASCADE, nullable | Nullable to avoid forcing a schema change the first time a non-letter notification type is needed — see model docstring |
| `notification_type` | varchar(100), NOT NULL | Plain string, same reasoning as `document_type` |
| `message` | text, NOT NULL | |
| `is_read` | boolean, NOT NULL, default `false` (both `server_default` and ORM `default`) | The database-level default was added in `e8a5cea2ccc6` — the column was already `NOT NULL` but previously had only a Python-side default, so a row written outside the ORM had no safe fallback. `ALTER COLUMN ... SET DEFAULT` is metadata-only; it doesn't rewrite existing rows |
| `created_at` | timestamptz, NOT NULL | |
| `read_at` | timestamptz, nullable | |

No delivery mechanism (email, push, WebSocket) exists or is assumed. V1 is
an in-system notification center only, per the brief.

### 2.9 `audit_logs`

An accountability trail: who changed what, when, and to what value. No row
is written by this phase — automatic audit-log generation is future work;
only the table exists so later phases have a stable place to write to.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → `users.id` ON DELETE SET NULL, nullable | Nullable for system-generated actions with no human actor (e.g. a scheduled job) — not because Users can be deleted |
| `action` | varchar(100), NOT NULL | Plain string; the full action vocabulary isn't confirmed yet |
| `entity_type` | varchar(100), NOT NULL | Names which table `entity_id` points into |
| `entity_id` | UUID, nullable | No FK — the target table varies per row, so one FK constraint can't cover it |
| `old_values` / `new_values` | JSONB, nullable | See below |
| `created_at` | timestamptz, NOT NULL | |

`old_values`/`new_values` use **JSONB**, not JSON: PostgreSQL indexes and
queries JSONB efficiently and stores it more compactly; this schema has no
requirement to preserve the exact original key ordering or whitespace that
only plain JSON retains.

---

## 3. Relationships

```text
Department
  ├── users                  (User.department_id)
  ├── user_authorizations    (UserAuthorization.department_id)
  └── letters                (Letter.department_id)

User
  ├── department                    (User.department_id → Department)
  ├── authorizations_created        (UserAuthorization.authorized_by → User)
  ├── letters_recorded              (Letter.recorded_by → User)
  ├── documents_uploaded            (LetterDocument.uploaded_by → User)
  ├── notifications                 (Notification.recipient_user_id → User)
  └── audit_logs                    (AuditLog.user_id → User)

Category
  └── letters                (Letter.category_id)

Classification
  └── letters                (Letter.classification_id)

Letter
  ├── department              (Letter.department_id → Department)
  ├── category                (Letter.category_id → Category, nullable)
  ├── classification          (Letter.classification_id → Classification, nullable)
  ├── recorded_by_user        (Letter.recorded_by → User)
  ├── documents                (LetterDocument.letter_id, cascade)
  └── notifications             (Notification.letter_id, cascade)
```

Relationship names on the `User` side are deliberately specific
(`letters_recorded`, `documents_uploaded`, `authorizations_created`) rather
than a generic `letters`/`documents`, because a `User` relates to `Letter`
and `LetterDocument` in exactly one role each in this schema (the recorder,
the uploader) — a vague name would suggest ambiguity that doesn't exist yet,
and would become actively wrong if a second relationship (e.g. "letters
assigned to this user") is added later.

---

## 4. Enums

| Type | Values | Used by |
|---|---|---|
| `user_role` | `SYSTEM_ADMIN`, `ADMIN`, `USER` | `users.role` |
| `user_status` | `PENDING_APPROVAL`, `ACTIVE`, `DEACTIVATED` | `users.status` |
| `authorization_status` | `ACTIVE`, `USED`, `REVOKED` | `user_authorizations.status` |
| `letter_status` | `ACTIVE`, `ARCHIVED` | `letters.status` |
| `active_status` | `ACTIVE`, `INACTIVE` | `departments.status`, `categories.status`, `classifications.status` (shared) |

All five are native PostgreSQL `ENUM` types (`CREATE TYPE ... AS ENUM (...)`),
not plain strings.

---

## 5. Foreign key behavior

| From → To | `ON DELETE` | Why |
|---|---|---|
| `users.department_id` → `departments.id` | `RESTRICT` | Departments are never physically deleted; RESTRICT is defense in depth |
| `letters.department_id` → `departments.id` | `RESTRICT` | Deactivating a department must not orphan or delete its letters |
| `letters.category_id` → `categories.id` | `RESTRICT` | Retiring a category must not delete letters tagged with it |
| `letters.classification_id` → `classifications.id` | `RESTRICT` | Same reasoning |
| `letters.recorded_by` → `users.id` | `RESTRICT` | Deactivating a user must not delete or orphan the letters they recorded |
| `user_authorizations.department_id` → `departments.id` | `RESTRICT` | Same reasoning as `letters.department_id` |
| `user_authorizations.authorized_by` → `users.id` | `RESTRICT` | Historical authorizations must keep pointing at a real admin |
| `letter_documents.letter_id` → `letters.id` | **`CASCADE`** | See below |
| `letter_documents.uploaded_by` → `users.id` | `RESTRICT` | Same reasoning as `letters.recorded_by` |
| `notifications.recipient_user_id` → `users.id` | `RESTRICT` | |
| `notifications.letter_id` → `letters.id` | **`CASCADE`** | See below |
| `audit_logs.user_id` → `users.id` | `SET NULL` | Preserves the audit row even in the (currently impossible, but defended-against) case a user row is removed |

**Why `letter_documents.letter_id` and `notifications.letter_id` cascade,
unlike everything else in this table.** Every other `RESTRICT` above
protects a *shared reference entity* (Department, Category, Classification,
User) from being deleted while something still points at it — those
entities are independently meaningful and are never deleted by this
schema's design. `LetterDocument` and `Notification` are different: each row
is a true **owned child** of exactly one `Letter` and has no meaning without
it. Cascading here only matters if a `Letter` row is ever physically removed
— which does not happen in normal operation (V1 has no delete endpoint;
"archiving" is the `letter_status.ARCHIVED` status, not a delete) — so this
is a safety net for deliberate manual cleanup, not a path the application
exercises.

---

## 6. Indexes

| Table | Index | Reason |
|---|---|---|
| `departments` | `status` | Added in `e8a5cea2ccc6`. Filtering active/inactive departments — was missing while Category/Classification had the equivalent (self-review finding) |
| `users` | `uq_users_email_lower` (unique, functional, `lower(email)`) | Case-insensitive login lookup and uniqueness — the single source of truth for "is this email taken" |
| `users` | `department_id`, `role`, `status` | Filtering users by department (isolation), by role, by account status — all frequent lookups once an admin UI exists |
| `user_authorizations` | `email` (functional, `lower(email)`) | Case-insensitive lookup during signup |
| `user_authorizations` | `department_id`, `authorized_by`, `status` | Admin views: "authorizations for my department", "who did I authorize" |
| `letters` | `department_id` | Department isolation — the single most important filter in the whole system |
| `letters` | `department_id, received_at` (composite) | The primary expected access pattern: "this department's letters, ordered by receipt date" |
| `letters` | `received_at`, `recorded_by`, `category_id`, `classification_id`, `status`, `subject` | Each is an explicitly required filter/search dimension (brief §18) |
| `letter_documents` | `letter_id`, `uploaded_by` | `uploaded_by` added in `e8a5cea2ccc6` — every other User-referencing FK in this schema was already indexed; this one had been missed |
| `notifications` | `recipient_user_id, is_read` (composite) | The primary expected query: "this user's unread notifications" |
| `notifications` | `letter_id` | FK lookup |
| `audit_logs` | `user_id`, `entity_type`, `created_at` | Each is an explicitly required filter dimension (brief §18) |
| `audit_logs` | `entity_type, entity_id` (composite) | The primary expected query: "audit trail for this specific record" |

Not every column is indexed — e.g. `categories`/`classifications.description`
have no index, because no described access pattern needs one yet and an
unused index only adds write overhead. Postgres does **not** automatically
index foreign key columns, so every FK column that has a genuine expected
lookup pattern is indexed explicitly above.

---

## 7. Requirements pending S&IT confirmation

These are documented assumptions, not final requirements. See
`docs/PROJECT_STATUS.md` for the authoritative, living list.

* **Official letter/reference number** — format and even existence
  unconfirmed. No column exists for it yet.
* **Sender types** (`letters.received_from`) — not assumed to always be a
  government department; kept as free text rather than a foreign key to
  another entity.
* **Final category list** — no categories are seeded; the examples discussed
  during requirements gathering (Budget, Procurement, HR, Legal,
  Infrastructure) are not hard-coded anywhere.
* **Final classification/priority terminology** — "Important" / "Classified"
  / "Routine" are examples only, not seeded or hard-coded.
* **Departmental code format** (`departments.code`) — left nullable and
  unformatted until S&IT confirms a convention.
* **`letters.subject` and `letters.reason` requirement-ness** — both left
  nullable; it's unconfirmed whether either should be mandatory at intake.
* **Document retention requirements** — not addressed by this schema at all;
  `letter_documents` has no expiry/retention field because no requirement
  has been given yet.

---

## 8. Why some entities are separate tables (not flags/columns)

* **`UserAuthorization` vs. `User`** — a `UserAuthorization` can exist (and
  be revoked) before anyone signs up against it, and its lifecycle belongs
  to the admin who granted access, not to an account that may never be
  created. Merging the two would force `User` rows to exist for people who
  never completed signup, which undermines "a `User` row always means a real
  account holder" — a property the department-isolation model in
  `docs/architecture/overview.md` depends on.
* **`LetterDocument` vs. `Letter`** — a letter may eventually have multiple
  attachments; one `storage_path` column caps a letter at exactly one file.
* **`Classification` vs. `Category`** — the two vary independently (see
  §2.5); merging them would force re-declaring every category per priority
  level.
* **`AuditLog`** — a government correspondence system needs an
  accountability trail answering "who changed what, when, what was it
  before, what is it now" independent of any single entity's own
  `updated_at` column (which only ever holds the *latest* value, not the
  history).

---

## 9. Local development

See `backend/README.md` for setup and `docs/database/README.md` for how to
apply this migration and run the model tests locally.
