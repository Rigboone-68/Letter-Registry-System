# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Current Phase

**Phase 4D — Document Management: Implementation.** Complete. Builds
directly on this phase's own prior architecture review: `LetterDocument`
upload, listing, and download are now implemented —
`POST`/`GET /api/v1/letters/{letter_id}/documents` and
`GET .../{document_id}` — with a server-generated, UUID-based storage
path that never trusts client input, layered file-type/size validation
(extension allowlist, then an authoritative magic-byte content
signature — client-supplied `Content-Type` is never trusted), and an
authorization chain that reuses `LetterService.get_letter`/
`assert_letter_access` rather than a new, parallel document-level check,
so classified-letter protection extends to its documents automatically.
No document deletion endpoint exists, of any kind — an explicit,
deliberate scope decision matching the review's own recommendation, not
a gap. No schema change was needed; `alembic check` confirms zero drift.
38 new tests, full suite **425 passed**, re-run 3 consecutive times, plus
a live-server verification against `lrs_dev` with real minted JWTs. Full
design and implementation record in
`docs/architecture/document-management.md` §33.

**One deliberate deviation from the review's own §7 recommendation**:
the implementation brief's literal example
(`<letter_uuid>/<document_uuid>.<ext>`, no department/year/month
grouping) was followed exactly as specified, rather than the review's
own recommended reconciliation with the Phase 1 storage convention —
`storage/README.md` now documents what was actually built and is
explicit about the gap between the two.

**Not in scope for this phase, and not added:** document deletion
(physical or soft), document replacement as a distinct endpoint (upload
again instead), OCR, antivirus/malware scanning, cloud storage, backup
automation, notifications, automatic audit logging, frontend upload UI,
or a `checksum_sha256` column (recommended by the review, explicitly
deferred by the implementation brief).

This implementation phase was preceded, in this same phase, by an
architecture-and-requirements-review-only pass — no code was written
until the review's recommendations were approved; see "Completed" below
for both, in order.

## Completed

### Phase 4D — Document Management implementation

* **`POST /api/v1/letters/{letter_id}/documents`** (upload),
  **`GET /api/v1/letters/{letter_id}/documents`** (metadata list, no
  `storage_path` field on the response), and
  **`GET /api/v1/letters/{letter_id}/documents/{document_id}`**
  (streamed binary download) — nested under Letter on purpose, per the
  review's own §19 recommendation, so the letter-first authorization
  chain is structurally unavoidable rather than a discipline to remember.
* **Storage foundation** (`app/services/document_storage.py`) —
  `STORAGE_PATH` resolved to an absolute path fresh on every call (never
  cached at import time), created if missing. Every filesystem path
  segment is server-generated:
  `<STORAGE_PATH>/<letter_uuid>/<document_uuid>.<ext>`, the extension
  chosen from a fixed map keyed by the already magic-byte-validated
  content type — never a client-supplied filename or extension. Writes
  are staged to a uniquely-named temp file and atomically renamed into
  place. **One deliberate deviation from the review's own §7
  recommendation**: the implementation brief's literal example (this
  exact flat, no-department/year/month-grouping structure) was followed
  as an explicit instruction, rather than the review's own recommended
  reconciliation with the Phase 1 `storage/README.md` convention — that
  file now documents what was actually built and is explicit about the
  gap, rather than silently updated to match either.
* **Layered file validation** (`app/services/document_validation.py`) —
  extension allowlist → size limit
  (`settings.MAX_DOCUMENT_SIZE_BYTES`, 10 MB default, still labeled an
  architectural recommendation in `config.py`/`.env.example`, not a
  confirmed organizational limit) → an authoritative magic-byte
  content-signature check (hand-rolled byte-prefix checks for
  PDF/JPEG/PNG, a UTF-8/control-character heuristic for text —
  deliberately no `python-magic`/libmagic dependency, given the small
  fixed type set and the native-install friction such a dependency adds
  on Windows) → extension/content-type agreement (a `.pdf` upload whose
  bytes are actually a PNG is rejected as mismatched). Client-supplied
  `Content-Type` is read but never consulted by any validation decision
  — confirmed live by uploading real PNG bytes under a `.pdf` filename
  and declared `Content-Type: application/pdf` (`422`, rejected).
* **Authorization chain (CRITICAL) — reused, not duplicated.**
  `DocumentService` resolves and authorizes the parent Letter via the
  existing `LetterService.get_letter` (already applying
  `assert_letter_access`) before ever touching a document — no new
  department/classification logic was written. A thin
  `assert_document_access` delegate was also added to
  `app/services/authorization.py` for any future caller holding an
  already-loaded `LetterDocument`, per the review's own suggestion. Every
  document route uses `get_current_user` only (not
  `require_user_or_admin`) so SYSTEM_ADMIN retains the same system-wide
  access to documents it already has to Letters — deliberately different
  from `POST /letters`, which excludes SYSTEM_ADMIN for a structural
  reason (no department to record a letter against) that doesn't apply
  to attaching a document to an *existing* letter.
* **Deletion policy (CRITICAL) — implemented exactly as recommended,
  the one recommendation with zero deviation.** No document deletion
  endpoint exists, physical or soft (`grep` for `@router.delete` in
  `app/api/v1/endpoints/documents.py` returns nothing). Uploading again
  is the only way to add a document; nothing removes a prior one.
* **Write-then-commit failure handling** — the file is written to its
  final path *before* the database row is committed; a DB failure after
  a successful write rolls back the transaction and deletes the
  now-orphaned file as compensation. Both failure branches (DB failure
  after a successful write; storage failure before any DB write) are
  directly tested, not just asserted.
* **Zero schema change.** `LetterDocument` is untouched;
  `alembic check` against `lrs_dev` reports "No new upgrade operations
  detected" both before and after this phase. The review's own
  `checksum_sha256` recommendation (§12) was explicitly not implemented,
  per the implementation brief's own instruction not to add it yet.
* **`python-multipart` added as a new dependency** (`requirements.txt`)
  — required by FastAPI/Starlette to parse `multipart/form-data` upload
  requests; no application code imports it directly.
* **38 new tests**
  (`tests/integration/test_document_management.py`) — file acceptance
  (PDF/JPEG/PNG/TXT) and rejection (bad extension, HTML, MIME spoofing,
  malformed content, oversized, empty), path security (five malicious-
  filename variants plus a direct containment-check test), authorization
  (USER/ADMIN own vs. other department, SYSTEM_ADMIN cross-department,
  classified-letter recorder vs. non-recorder, wrong-letter/document
  pairing, nonexistent letter/document), historical integrity
  (deactivated uploader still represented, archived letters keep their
  documents and stay downloadable), storage guarantees (UUID-based
  server-controlled path, no `storage_path` in any response, no static
  route exposes storage, correct download headers), and failure handling
  — against a real PostgreSQL test database, with an autouse
  `storage_root` fixture redirecting every test's `STORAGE_PATH` to a
  per-test temporary directory (the filesystem equivalent of
  `db_session`'s per-test rollback isolation).
* **Full suite: 425 passed** (387 baseline + 38 new), re-run 3
  consecutive times, identical results.
* **Live-server verification against `lrs_dev`**, real minted JWTs, real
  HTTP — see "Validation performed" below.
* **Documentation**: `docs/architecture/document-management.md` §33
  (new implementation record), `storage/README.md` (updated to match
  what was actually built), plus updates to the root README,
  `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4D — Document Management architecture & requirements review

* **Inspected the actual current repository state, not assumed** —
  confirmed `LetterDocument` (`document_type`, `original_filename`,
  `storage_path`, `file_size`, `mime_type`, `uploaded_by`, `uploaded_at`)
  is byte-for-byte unchanged since the Phase 2 baseline + hardening
  migrations; confirmed zero application code (service/repository/
  schema/endpoint) exists above the model layer; confirmed no
  `StaticFiles` mount exists in `app/main.py`; confirmed `.gitignore`
  excludes `storage/letters/*` except `.gitkeep`; confirmed only two
  Phase 2 model-level tests touch `LetterDocument` (multi-document
  attachment, CASCADE-on-physical-delete), with no upload/validation/
  security test existing anywhere.
* **Surfaced a real, previously-unnoticed documentation conflict** — the
  pre-existing Phase 1 `storage/README.md` path convention
  (`<department-code>/<year>/<month>/<letter-uuid>.<ext>`) has no
  document-identifier segment, structurally assuming one file per
  letter; this conflicts with the schema's already-confirmed 1-to-many
  `Letter → LetterDocument` capability. Not silently resolved — reconciled
  with a recommended combined convention
  (`<department-id>/<year>/<month>/<letter-uuid>/<document-uuid>.<ext>`)
  that keeps Phase 1's department/year/month grouping and adds
  multi-document support, using `department.id` rather than the
  nullable, unconfirmed-format `department.code`. See
  `docs/architecture/document-management.md` §7.
* **Two CRITICAL findings resolved by design, not new code**:
  (1) department isolation for documents must derive from
  `LetterDocument.letter_id → Letter.recipient_department_id`, never
  `uploaded_by.department_id` (a User can change departments) —
  `LetterDocument` already has no department field of its own, so there
  is nothing to misuse; (2) classified-document access must chain
  through the existing `assert_letter_access`
  (`app/services/authorization.py`, Phase 4B/4C) via a thin future
  `assert_document_access` delegate, never a new parallel check — so
  classified-letter protection extends to attachments automatically. See
  §16-17.
* **Document deletion policy (CRITICAL) — recommended that V1 build no
  deletion endpoint at all**, physical or soft. Physical deletion would
  break this project's established never-physically-delete principle
  (Department/User/Category/Classification/Letter all archive, never
  delete); soft-delete would need a new lifecycle/status field
  `LetterDocument` doesn't have today; and no confirmed requirement asks
  for document deletion in the first place. See §14.
* **Document replacement policy — resolved without a schema change.**
  "Replacing" a document is recommended to mean simply uploading another
  document for the same letter (the old one stays) — already fully
  supported by the existing multi-document capability, the safest option
  against historical-record loss. A "mark as superseded" concept would
  need a new field and isn't adopted without further business
  confirmation. See §13.
* **Layered file validation strategy designed (not implemented)**:
  extension allowlist, never-trust-client-`Content-Type`, magic-byte
  signature verification as the authoritative check, size limit — with
  an explicit note that type validation is not a substitute for
  antivirus scanning (out of scope). A 10 MB default size limit is
  labeled an ARCHITECTURAL RECOMMENDATION, not a confirmed organizational
  limit — none was given. See §8-9.
* **Checksum field recommended as an additive future column**
  (`checksum_sha256`, nullable, no uniqueness constraint — two different
  letters can legitimately share an identical attachment) — the only
  schema change any recommendation in this review implies, and not
  created this phase. See §12, §28.
* **Text-content relationship clarified without a schema change** —
  `Letter.text_content` (typed/transcribed content) and a `LetterDocument`
  with `mime_type="text/plain"` (an uploaded `.txt` file) are
  complementary, not redundant; the model already supports both. The
  *workflow* question (which one a User is expected to use) is marked
  PENDING BUSINESS CLARIFICATION. See §10.
* **API design recommended**: documents nested under their Letter
  (`GET /api/v1/letters/{letter_id}/documents/{document_id}`) rather than
  a flat `/api/v1/documents/{id}`, so the letter-first authorization
  chain is structurally unavoidable, not just a discipline. Content-Type
  on download always server-controlled from the validated `mime_type`,
  never re-trusted from a client header. See §19.
* **Transaction/failure-handling strategy designed** for five scenarios
  (DB-row-created-but-file-write-fails, file-succeeds-but-DB-fails,
  interrupted upload, duplicate upload, storage-directory-unavailable) —
  recommended ordering is write-file-then-commit-DB-row, biasing failures
  toward the recoverable outcome (an orphaned file, cleanable later) over
  the unrecoverable one (a DB row referencing a file that was never
  written). See §23.
* **16+ scenario test plan designed, not implemented** — file-type
  validation, path/storage safety, authorization (cross-department,
  classified-access, IDOR/enumeration), historical integrity, failure
  handling, and static-file-exposure regression. See §29.
* **No migration, model, service, repository, schema, endpoint, or test
  file touched** — confirmed by `git status` before/after; this phase
  produced documentation only.
* **Documentation**: `docs/architecture/document-management.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  and `docs/architecture/overview.md`.

### Phase 4C — Registry Operations & Search implementation

### Phase 4C — Registry Operations & Search implementation

* **Fixed the query-level classified-access gap first**, exactly as
  planned. `app/services/authorization.py:letter_visibility_filter(user)`
  returns a SQLAlchemy boolean expression (`None` for
  `SYSTEM_ADMIN`/`ADMIN`; the classified-access rule as a `WHERE`
  fragment for `USER`), consumed by
  `app/repositories/letter_repository.py:list_letters`, which builds
  **one** filtered statement and derives both the `COUNT` and the
  paginated `items` query from it — structurally impossible for the two
  to disagree about which rows are visible. Verified by two dedicated
  regression tests and a live `lrs_dev` check (see "Validation
  performed" below).
* **Pagination** — `page`/`page_size` (defaults `1`/`25`, `page_size`
  capped at `100`, both FastAPI-validated), envelope extended with
  `page`/`page_size`/`total_pages` (the existing `items`/`total` keys
  unchanged).
* **Sorting** — `sort_by`/`sort_order` via `LetterSortField`/`SortOrder`
  enums (an invalid value is `422` before the endpoint runs — never a
  raw client string reaching `ORDER BY`), default `received_at desc`,
  stabilized with a secondary sort on `Letter.id`.
* **Search/filters** — `reference_number`, `subject`, `sender_name`,
  `sender_designation`, `sender_department`, `source_name`,
  `source_location` (case-insensitive contains, `ILIKE`-escaped against
  literal `%`/`_` in the search term); `received_from`/`received_to`
  (inclusive, rejected with `422` if reversed); `category_id`/
  `classification_id`/`status`/`department_id` (exact, `department_id`
  unchanged Phase 4B behavior — SYSTEM_ADMIN-only, silently ignored
  otherwise). All combine with `AND`.
* **Lightweight list response** — `LetterListItem`
  (`app/schemas/letter.py`) omits `text_content`/`reason`;
  `GET /api/v1/letters/{id}` unchanged, still returns the full
  `LetterResponse`.
* **Migration `9fa970ffa560`** — adds `ix_letters_reference_number` (a
  plain, non-unique B-tree index; re-added after Phase 4B's hardening
  pass removed the unique constraint that used to imply one). No other
  index added — a B-tree index gives `ILIKE '%contains%'` no benefit.
* **43 new tests** (`tests/integration/test_letter_search.py`) — the two
  highest-priority ones prove the central fix directly:
  `test_classified_record_excluded_from_total_count` and
  `test_classified_record_excluded_across_all_pages`.
* **No physical Letter deletion, no reference-number uniqueness
  reintroduced, no Phase 4D functionality** — confirmed explicitly, see
  "Explicit Scope Confirmation" in the phase's own final report.
* **Documentation**: `docs/architecture/registry-search.md` updated from
  recommendation to implementation record, plus updates to the root
  README, `backend/README.md`, and `docs/architecture/overview.md`.

### Phase 4B — Letter Registry Core implementation, plus a pre-commit hardening pass

Complete. Builds directly on Phase 4A's review: the
product owner resolved all six pending business decisions, and this
phase implemented them — a Letter registry with recipient/source
department separation, required structured sender details, a required
manually-entered reference number, exactly three seeded Categories,
Classification management with a real (though intentionally provisional)
classified-access authorization boundary, and full Letter CRUD (create/
list/get/update/archive) scoped by department and, for classified
letters, further narrowed for non-recording Users. A follow-up hardening
pass, before anything was committed, then reviewed the whole
implementation for correctness/security and found one real defect:
reference-number uniqueness had been implemented as a *global* database
constraint on an assumption the business never actually confirmed (only
"must be unique" was said, never the scope) — the constraint was removed
rather than kept on a guess or replaced with a different guessed scope.
Everything else reviewed (DELETE/archival safety, sender-field
placeholders, source/sender semantics, classified-access boundary,
department isolation, historical identity, input security) was
re-verified against actual code and found already correct. Full design
in `docs/architecture/letter-registry.md`, hardening findings in its §14.
Not in scope for that phase: file upload/download (the `LetterDocument`
relationship remains schema-only), dashboards, automatic notification
generation, automatic audit logging, full-text search, frontend, System
Admin handover, or an ADMIN-purpose authorization-revocation endpoint (a
pre-existing Phase 3B.4 gap, unrelated to that phase).

### Phase 4B hardening pass — pre-commit correctness/security review

* **Reference-number uniqueness — the one real defect found.** Migration
  `c887ab35e4a3` drops `uq_letters_reference_number`. The finalized
  business decision said reference numbers "must be unique" but never
  specified the scope (global? per receiving department? per source? per
  year?); the initial implementation guessed "global", which a real
  multi-department registry could easily violate legitimately (two
  departments each issuing their own overlapping numbering). No
  replacement scope was invented — duplicates are now accepted anywhere,
  pending an actual business answer. `reference_number` remains required
  (`NOT NULL`). Dead code removed alongside it:
  `DuplicateReferenceNumberError`, the `try/except IntegrityError`
  blocks in `LetterService.create_letter`/`update_letter`, and the
  unused `LetterRepository.find_by_reference_number`.
* **DELETE/archival safety — re-verified, no change needed.** Confirmed
  via `grep` (not just re-reading prior documentation) that no code path
  issues a SQL `DELETE` against a `Letter` row — `archive_letter` only
  sets `status = ARCHIVED`. Already the safest available reading of
  "Delete Letter, subject to authorization" against this project's
  standing "letters are never physically deleted" principle.
* **Sender-field migration placeholders — confirmed safe.** The literal
  string `'MIGRATION-PLACEHOLDER'` (and `'MIGRATED-<row-id>'` for
  reference numbers) cannot be mistaken for real business data, and no
  real production data could exist regardless (this project has never
  been deployed).
* **Classification security, department isolation, historical identity,
  input security — all re-verified directly against current code and
  existing tests**, confirmed to match what was previously reported, no
  changes needed. See `docs/architecture/letter-registry.md` §14 for the
  full, itemized findings using its CONFIRMED/ARCHITECTURAL/PROVISIONAL/
  PENDING taxonomy.
* **344 tests total — unchanged.** Three tests were rewritten in place
  (asserting the new, correct behavior — duplicates now succeed rather
  than being rejected) rather than deleted and replaced, so the count
  didn't move. Re-run 3 consecutive times, all green.
* **No new migration needed beyond the one hardening fix** — `alembic
  check` confirms zero drift; no historical migration file was modified.

### Phase 4B — Letter Registry Core implementation

* **Six finalized business decisions implemented exactly as specified** —
  see `docs/architecture/letter-registry.md` §2 for each, and §0 for the
  CONFIRMED/IMPLEMENTATION-DECISION/PENDING framework used throughout so
  nothing implemented here is silently guessed.
* **Migration `48ec742d9e8f`** — renamed `letters.department_id` ->
  `recipient_department_id` and `letters.received_from` -> `source_name`
  (data-preserving renames, not recreated columns); added
  `source_department_id`/`source_location`/`sender_address` (nullable)
  and `sender_name`/`sender_designation`/`sender_department`/
  `reference_number` (required, safely backfilled for any pre-existing
  row using the standard add-nullable -> backfill -> tighten pattern);
  added `uq_letters_reference_number` (later removed — see below); added
  `classifications.restricts_access`; seeded exactly three `categories`
  rows (General Letter, Notification, Office Order). Verified against a
  real pre-existing `Letter` row inserted before the migration ran (not
  just an empty table), and a full `upgrade -> downgrade -> upgrade`
  round-trip — see "Validation performed" below.
* **Migration `c887ab35e4a3` (hardening pass)** — drops
  `uq_letters_reference_number`, added by the migration above on an
  unconfirmed global-uniqueness assumption; see the hardening-pass
  section above and `docs/architecture/letter-registry.md` §2.3/§14.
* **`app/services/authorization.py:assert_letter_access`** — the
  classified-access authorization boundary, built on top of (not
  duplicating) `assert_department_access`. Department isolation always
  gates first; `SYSTEM_ADMIN` retains complete access; a `USER` who is
  not a classified letter's own recorder is denied even within their own
  department. Documented explicitly as a conservative, provisional
  default — the exact visibility matrix remains open (see "Remaining
  Known Issues").
* **`app/services/letter_service.py`, `category_service.py`,
  `classification_service.py`**, their repositories, Pydantic schemas,
  and `/api/v1/letters*`, `/api/v1/categories*`, `/api/v1/classifications*`
  endpoints — the same four-layer architecture every phase since 3A has
  used. `recorded_by`/`recipient_department_id` always derived from the
  authenticated caller, never client-supplied (no field for either
  exists on `LetterCreate`).
* **"Delete" is archival** (`status -> ARCHIVED`), never a physical SQL
  `DELETE` — a continuation of Phase 2's original decision, not a change
  to it.
* **Reference-number uniqueness — implemented, then removed the same
  phase.** Originally enforced at the database level
  (`uq_letters_reference_number`), race-safe (attempt-then-catch
  `IntegrityError`, the same pattern `DepartmentService` established in
  Phase 3B.2). A follow-up hardening pass found the *scope* of "must be
  unique" was never actually confirmed by the business and removed the
  constraint (migration `c887ab35e4a3`) rather than keep a guess — see
  the hardening-pass section above.
* **67 new automated tests** across `test_letter_registry.py` (50,
  covering every lettered item A-X in the brief's test list),
  `test_category_management.py` (8), `test_classification_management.py`
  (9) — against a real PostgreSQL test database — plus a full live-server
  verification against `lrs_dev` with real JWTs (letter creation,
  duplicate-reference rejection, cross-department 404s, the classified-
  access boundary exercised across recorder/same-department-non-recorder/
  Admin/SYSTEM_ADMIN, update, and archive).
* **Documentation**: `docs/architecture/letter-registry.md` (finalized
  decisions + implementation record), plus updates to the root README,
  `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4A — Letter Registry Core architecture review

* **Full inspection of the existing Letter-adjacent schema** — `Letter`,
  `LetterDocument`, `Category`, `Classification`, `Department`, `User`,
  `AuditLog`, `Notification` models, both existing migrations, and
  `docs/database/schema.md` — confirmed, not assumed: no repository,
  Pydantic schema, service, or API endpoint exists yet for `Letter`/
  `Category`/`Classification`; Phase 4A is the first phase to write any
  code above the model layer for these three entities (and it wrote
  documentation only).
* **Confirmed a real architectural gap**: the existing
  `Letter.department_id` is a single field, but the confirmed V1
  requirements need two independent department-shaped facts — the
  sending/source department and the recipient/owning department. A single
  column cannot represent both. Recommended a `recipient_department_id`
  field (the field department-isolation authorization should check,
  functionally a clarification of what `department_id` already means
  today) plus a separate source-side representation — not implemented
  this phase. See `docs/architecture/letter-registry.md` §5.
* **Confirmed two requirements are already fully satisfied by existing
  Phase 2 design, with no gap**: the "date received vs. date recorded"
  distinction (`received_at` vs. `created_at`, already two separate
  columns) and "letter content, text or document or both"
  (`text_content` + the existing `LetterDocument` 1:N relationship).
  Neither needed a new column.
* **Confirmed `recorded_by`'s historical-identity guarantee (`RESTRICT`,
  not `CASCADE`/`SET NULL`) is already correct** — verified directly
  against the model and existing passing tests, not re-implemented.
* **Flagged, not resolved, six pending business clarifications**:
  source-department representation (free text vs. FK to a real
  `Department`), exact sender-detail sub-fields, reference-number
  uniqueness/issuing-authority/format, whether "Budget" belongs to
  Category or Classification (the same word appeared as a Category
  example in Phase 2 and a Classification example in this phase's brief),
  whether "Classified" needs to actually restrict visibility or is a
  label only, and source-location/sender-details nullability. See
  `docs/architecture/letter-registry.md` §21.
* **Identified a Phase 4B prerequisite**: System-Admin Category and
  Classification management (list/create/update/activate-deactivate)
  does not exist yet — both tables are schema-only since Phase 2, with
  zero rows and zero endpoints. `Letter.category_id`/`classification_id`
  cannot reference anything real until that management surface exists.
* **No schema, migration, repository, service, endpoint, or test change**
  — this phase produced documentation only, per its explicit scope
  boundary. `alembic check`: "No new upgrade operations detected."
* **Documentation**: `docs/architecture/letter-registry.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3B.4 — User management

* **User authorization, ADMIN only** — `POST /api/v1/users/authorizations`.
  Unlike Admin authorization, the request has no `department_id` field at
  all — it is always derived from the calling Admin's own department.
  Validates the Admin's own department is `ACTIVE`, the email doesn't
  already belong to an active User, and no unresolved USER authorization
  already exists for it.
* **User signup reuses the existing `/auth/signup` endpoint** — no third
  authentication workflow. Race-safety (`SELECT ... FOR UPDATE`) is
  unchanged from Phase 3A/3B.3 and re-verified for an Admin-issued
  USER-purpose authorization specifically with a genuine two-thread
  concurrency test.
* **User approval** — `POST /api/v1/users/{id}/approve`. Not idempotent,
  same one-time-event reasoning as Admin approval (Phase 3B.3).
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's *own* department to be `ACTIVE`, re-checked on
  every call. Deactivation is unconditional — allowed even if the Admin's
  department has itself been deactivated, a deliberate design decision
  (see "Three isolation strengths" below) since lock-down actions must
  stay possible precisely when a department is in a bad state.
* **Three different isolation strengths, not interchangeable** — read and
  lock-down actions (list/get/deactivate/revoke) require only that the
  target belong to the Admin's own department; state-elevating actions
  (authorize/approve/reactivate) additionally require the Admin's own
  department to be `ACTIVE`. Documented and tested explicitly, not just an
  incidental side effect — see `docs/architecture/user-management.md` §5.
* **The project's first authorization revocation endpoint** —
  `DELETE /api/v1/users/authorizations/{id}`. `AuthorizationStatus.REVOKED`
  has existed since Phase 2 but had no endpoint setting it until now.
  Creator-scoped (only the Admin who created an authorization may revoke
  it — stricter than the department-wide visibility of the listing
  endpoint), idempotent for an already-revoked row, rejected (`409`) for
  an already-used one, and never deletes the row.
* **Cross-department isolation exercised against a real resource for the
  first time** — every prior phase's caller (`SYSTEM_ADMIN`) was global,
  so `assert_department_access` had only ever run against
  verification-only endpoints or short-circuited via the SYSTEM_ADMIN
  bypass. An Admin in Department A gets an identical `404` (not `403`)
  attempting to view, approve, deactivate, or reactivate a User in
  Department B — indistinguishable from that id not existing at all,
  hiding cross-department existence, not merely blocking action on it.
* **User self-protection requires no special-case code** — the same
  structural pattern Phase 3B.3 used for System Admin protection:
  `find_user_by_id` filters by role `USER`, so an Admin's own id (role
  `ADMIN`) 404s on every lifecycle endpoint without a dedicated
  "is this the caller's own id" check.
* **53 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Listing/
  Details/Approval/Deactivation/Reactivation/Revocation/Cross-Department-
  Security/Self-Protection/Lifecycle/Race-Safety lists, plus a full
  live-server verification against `lrs_dev` (authorize → signup →
  pending login rejected → approve → login → access → deactivate → stale
  JWT rejected → reactivate → same stale JWT works again; cross-department
  rejection; revoked authorization cannot sign up).
* **Documentation**: `docs/architecture/user-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3B.3 — Admin management (see previous entries below for detail)

* **Admin authorization, SYSTEM_ADMIN only** —
  `POST /api/v1/admins/authorizations`. Validates the destination
  department exists and is `ACTIVE`, the email doesn't already belong to
  an active Admin, and no unresolved ADMIN authorization already exists
  for it. `authorized_by` is always the caller's own id.
* **Admin signup reuses the existing `/auth/signup` endpoint** — no second
  authentication workflow. Role is derived from whichever authorization is
  found (`purpose=ADMIN` → role `ADMIN`, otherwise role `USER`) — a USER
  authorization can never produce an ADMIN and vice versa, by
  construction. Race-safety (`SELECT ... FOR UPDATE`) is unchanged from
  Phase 3A and re-verified for the ADMIN path specifically with a genuine
  two-thread concurrency test.
* **Admin approval** — `POST /api/v1/admins/{id}/approve`. Not idempotent
  (unlike every other status-changing endpoint in this project so far):
  approving an already-`ACTIVE` or `DEACTIVATED` Admin is rejected with
  `409`, since approval is a one-time event, not a toggle.
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's department to be `ACTIVE`, re-checked on every
  call (even the already-`ACTIVE` idempotent case), since an Admin can end
  up `ACTIVE` while their department is `INACTIVE` (Phase 3B.2
  deactivation never touches `User` rows).
* **Multiple Admins per department, deliberately unbounded** — no
  `department_id UNIQUE` constraint added, per the brief's explicit
  instruction.
* **Admin department transfer, proven historically safe** —
  `Letter.department_id` is independently stored (Phase 2 design), never
  re-derived from the recording user, so moving an Admin between
  departments cannot retroactively change any letter they already
  recorded. Verified directly (row-level assertion after a real transfer),
  not just asserted from the schema.
* **System Admin accounts are structurally unreachable through
  `/api/v1/admins/*`** — a `user_id` resolving to `SYSTEM_ADMIN` gets the
  same `404` as a nonexistent id, via the same repository method
  (`find_admin_by_id`) that filters by role.
* **Admin self-protection requires no special-case code** — every
  Admin-management endpoint is `require_system_admin`-only (reused
  unchanged from Phase 3B.1, no new dependency), so an Admin can never
  reach any of these endpoints regardless of which `user_id` they target,
  including their own.
* **47 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Approval/
  Lifecycle/Multiple-Admins/Department-Transfer/Self-Protection/System-
  Admin-Protection/Race-Safety lists, plus a full live-server verification
  against `lrs_dev` (authorize → signup → pending → approve → login →
  escalation attempts rejected → department transfer → deactivate → old
  token rejected).
* **Documentation**: `docs/architecture/admin-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, and `docs/database/schema.md`.

### Phase 3B.2 — Department management (see previous entries below for detail)

* **Department CRUD, SYSTEM_ADMIN only** — `POST`/`GET`/`PATCH
  /api/v1/departments`, `.../{id}`, `.../{id}/activate`,
  `.../{id}/deactivate`. New departments are always `ACTIVE`; `status` is
  never editable through the generic update endpoint, only through the
  two dedicated, idempotent activate/deactivate endpoints.
* **Race-safe duplicate detection** — no pre-check; every create/update
  attempts the write and relies on PostgreSQL's own unique constraints,
  catching `IntegrityError` and reporting exactly which field
  (`name`/`code`) conflicted via `409`.
* **Historical data preserved on deactivation** — no User, Letter, or any
  other row is deleted, modified, or reassigned when a department becomes
  `INACTIVE`; verified directly (row-by-row) in tests, not just asserted.
* **Inactive-department authorization extension** —
  `assert_department_access` (Phase 3B.1) now also requires an
  ADMIN/USER's own department to be `ACTIVE`; SYSTEM_ADMIN is completely
  unaffected and retains full access to inactive departments for
  historical/administrative purposes. Reactivating a department restores
  access immediately, with no cached decision anywhere.
* **A real schema-naming bug found and fixed** (not a migration —
  `alembic check` still reports zero drift): `Department.name`/`code`'s
  unique constraints were unnamed (`unique=True` shorthand), so the test
  database (`Base.metadata.create_all()`) and the real, migration-built
  database silently used different auto-generated constraint names. Fixed
  by naming both explicitly to match the existing migration. The same
  latent issue remains on `categories.name`/`classifications.name`,
  documented but not fixed (out of this phase's scope).
* **36 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Creation/Retrieval/
  Update/Status/Security lists, plus a full live-server verification
  against `lrs_dev` (creation → duplicate rejection → list/get/update →
  deactivate-blocks-user → reactivate-restores-access).
* **Documentation**: `docs/architecture/department-management.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, `docs/architecture/authorization.md`,
  and `docs/database/schema.md`.

### Phase 3B.1 — RBAC & department authorization

* **Role-check dependencies** (`app/api/deps.py`) —
  `require_system_admin`, `require_admin`, `require_admin_or_system_admin`,
  `require_user_or_admin`, each composed on top of `get_current_user` via
  FastAPI's own `Depends()` mechanism, never re-deciding authentication.
* **Department-isolation enforcement** — `assert_department_access`
  (`app/services/authorization.py`, framework-agnostic — no FastAPI
  import) and its FastAPI wrapper `require_department_access`
  (`app/api/deps.py`). SYSTEM_ADMIN bypasses; ADMIN/USER must match their
  own `department_id` exactly — not an existence check, a made-up UUID is
  rejected identically to a real foreign one.
* **Generic, non-leaking 403s** — one fixed message for every role/
  department authorization failure; never names the role required, the
  department requested, or the caller's own department.
* **Five verification-only endpoints**
  (`app/api/v1/endpoints/dev_authz_test.py`, tagged
  `dev-authorization-test` in OpenAPI, no frontend) — exist solely because
  no real protected resource exists yet in this phase for the
  authorization dependencies to attach to; documented for removal once
  Phase 4 adds one.
* **42 new automated tests**: 16 in `backend/tests/unit/test_authorization.py`
  (pure function/dependency logic, no database) and 26 in
  `backend/tests/integration/test_authorization.py` (real JWTs, real
  database-backed Users, real HTTP requests — including every scenario in
  the brief's Role/Department/Deactivation/Negative-security test lists).
* **Documentation**: `docs/architecture/authorization.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3A — Authentication foundation (see previous entries below for detail)

* **Local email/password authentication** — no external OAuth provider;
  see `docs/architecture/authentication.md` §1.
* **Argon2id password hashing** via `argon2-cffi`, centralized password
  policy (8-128 characters), never a manual hash comparison.
* **JWT access tokens** (PyJWT, HS256, `SECRET_KEY`-signed) — creation,
  validation, expiration, and rejection of tampered/malformed/`alg:none`
  tokens.
* **Bootstrap System Admin** — `python -m app.cli create-system-admin`,
  refuses to run if an active System Admin already exists.
* **Authorized signup** — `POST /api/v1/auth/signup`, race-safe
  consumption of `UserAuthorization` (`SELECT ... FOR UPDATE`), role/
  department/status always derived server-side, never client-supplied.
* **Pending-approval account lifecycle** — new accounts start
  `PENDING_APPROVAL` and cannot log in until (a future phase's) Admin
  approval.
* **Login** — `POST /api/v1/auth/login`, account-enumeration-resistant,
  status-aware (pending/deactivated rejected with distinct messages after
  a correct password, not before).
* **Current-user endpoint** — `GET /api/v1/auth/me`, backed by
  `get_current_user` (`app/api/deps.py`), the identity-establishment
  dependency Phase 3B's authorization checks will build on.
* **65 new automated tests** across `backend/tests/unit/test_security.py`,
  `test_email_utils.py`, and `backend/tests/integration/test_auth_bootstrap.py`,
  `test_auth_signup.py`, `test_auth_login.py`, `test_auth_current_user.py`
  — including a genuine two-thread/two-connection concurrency test proving
  the signup race-condition fix.
* **Documentation**: `docs/architecture/authentication.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 2 — Database architecture (see previous entries below for detail)

* 9 core SQLAlchemy models, two Alembic migrations (baseline + hardening),
  31 model-level tests. Full detail in `docs/database/schema.md`.

### Corrections applied during Phase 2 (self-review hardening pass)

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

### Validation performed — Phase 4D implementation

All against the same real, local, disposable PostgreSQL 17 instance
used for every prior phase (`lrs_dev` for manual checks, `lrs_test` for
the suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest tests/` (full suite) against `lrs_test` | **425 passed**, 0 failed, 0 skipped (387 baseline + 38 new). Re-run 3 consecutive times, identical results |
| `alembic check` against `lrs_dev` | "No new upgrade operations detected" — this phase needed no schema change |
| No test writes into the real `storage/letters/` tree | Confirmed by `find storage/letters -type f` before/after the full suite run — only `.gitkeep` present both times; the autouse `storage_root` test fixture redirects every test's `STORAGE_PATH` to a per-test `tmp_path` |
| Live-server verification against `lrs_dev`, real minted JWTs, a running `uvicorn` instance | Upload as the recording USER (`201`); download — content byte-for-byte identical to what was uploaded (`200`); cross-department USER upload and download (`404`, both); SYSTEM_ADMIN upload to a letter in a department it doesn't belong to (`201` — confirms system-wide access); non-recording USER in the *same* department denied a classified letter's documents (`404`); the recording USER allowed (`201`); unsupported extension `.docx` (`422`); MIME spoofing — `.pdf` filename/declared `Content-Type`, real PNG bytes — rejected (`422`); metadata list response confirmed free of any `storage_path` field; nonexistent document id (`404`); unauthenticated request (`401`) |
| Live download response headers | `Content-Type: application/pdf` (server-validated, not client-supplied), `Content-Disposition: attachment; filename="..."`, `X-Content-Type-Options: nosniff` |
| Files written during live verification, confirmed and cleaned up | `storage/letters/<letter_id>/<document_id>.pdf` for each upload — matches the documented convention exactly; all removed after verification |
| All live-verification data removed afterward | Departments/Users/Letters/`LetterDocument` rows deleted via direct session cleanup; `lrs_dev`'s `categories` table reconfirmed unchanged (still exactly 3 seeded rows) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored (see "Known Limitations" for a local-environment note about this file, unrelated to what was committed) |

**Environment note, not a Phase 4D defect**: a bare `pytest` invocation
from `backend/` also tries to collect
`app/api/v1/endpoints/dev_authz_test.py` as a test module (its filename
incidentally matches pytest's default `*_test.py` discovery pattern),
producing one collection error unrelated to any test in this suite.
Confirmed pre-existing (not introduced by this phase) by stashing every
Phase 4D change and reproducing the identical error against the
unmodified tree. `pytest tests/` (scoped explicitly) avoids it; that
scoped form is what every count above uses, and what `backend/README.md`
now documents.

### Validation performed — Phase 4D review

An architecture review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic tests (the same standard applied to Phase
4A's review):

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no model, migration, repository, schema, service, endpoint, or test file touched |
| `alembic check` | "No new upgrade operations detected" — no migration was created, consistent with a read-only review |
| Direct reads of `app/models/letter_document.py`, `app/models/letter.py`, `app/core/config.py`, migrations, tests, `app/main.py`, `.gitignore`, `storage/README.md` | Confirmed empirically (not from Phase 4A memory) that `LetterDocument` is unchanged since Phase 2, no `StaticFiles` mount exists, and only two model-level tests touch the entity |
| `grep` across `app/services/`, `app/repositories/`, `app/schemas/`, `app/api/` for `LetterDocument`/`storage_path`/`STORAGE_PATH`/`upload`/`download` | Zero real matches — confirms zero application code exists above the model layer for documents |

### Validation performed — Phase 4C

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **387 passed**, 0 failed, 0 skipped (344 baseline + 43 new). Re-run 3 consecutive times, identical results |
| `alembic upgrade head` against `lrs_dev` (new migration `9fa970ffa560`) | Applied cleanly (`c887ab35e4a3 -> 9fa970ffa560`) |
| `alembic downgrade -1` -> `alembic upgrade head` | Full round-trip verified — `ix_letters_reference_number` correctly absent after downgrade, correctly present again after re-upgrade |
| `alembic check` | "No new upgrade operations detected" |
| Live-server verification against `lrs_dev` with real JWTs — the central fix, proven end-to-end | 3 ordinary letters + 2 classified letters (recorded by a different User) created in one department; the non-recording User's `GET /api/v1/letters` returned `total: 3` (not 5), with no `HIDDEN`-tagged reference number appearing in `items`; the same query paginated at `page_size=2` still reported `total: 3`/`total_pages: 2` across both pages; the department's Admin and a SYSTEM_ADMIN both correctly saw `total: 5` |
| Live sort + search + filter combined | `?subject=live&sort_by=reference_number&sort_order=asc` returned exactly the visible (non-classified) letters, correctly ordered |
| `git status` review | No secrets tracked; `.env` confirmed gitignored; no historical migration file modified |

All data created during manual verification was deleted from `lrs_dev`
afterward, except the three seeded `categories` rows (unchanged,
permanent V1 configuration); `lrs_dev` otherwise empty again.

### Validation performed — Phase 4B

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **344 passed**, 0 failed, 0 skipped (277 baseline + 67 new). Re-run 3 times consecutively with identical results — no flakiness introduced |
| `alembic upgrade head` against `lrs_dev` | Applied cleanly (`a223396c9eac -> 48ec742d9e8f`) |
| `alembic downgrade -1` -> `alembic upgrade head` | Full round-trip verified — the schema after re-upgrading was byte-identical to the first upgrade (indexes, constraints, columns all present, correctly named) |
| Migration tested against a real pre-existing row (not just an empty table) | A `Letter` row inserted via raw SQL *before* the migration ran was correctly preserved: `recipient_department_id` retained the exact original `department_id` value, `source_name` retained the original `received_from` value, and the new required columns were backfilled to clearly-marked, uniquely-identifiable placeholder values (`MIGRATION-PLACEHOLDER` / `MIGRATED-<row-id>`) |
| `alembic check` | "No new upgrade operations detected" — models match the applied migration exactly |
| FastAPI app startup + `GET /health` + full OpenAPI schema generation | 200 OK; `/api/v1/letters*`, `/api/v1/categories*`, `/api/v1/classifications*` all present with expected methods |
| Full Letter lifecycle, run for real against `lrs_dev` via real HTTP with real minted JWTs, two departments | Category list confirmed seeded with exactly the three finalized names; letter created with real category + a `restricts_access=True` classification; duplicate reference number -> `409` **(superseded — see hardening pass below; `uq_letters_reference_number` no longer exists, duplicates now succeed)**; cross-department `GET` -> `404`; a *second* User in the *same* department who did not record the letter -> `404`; the recording User, an Admin in the same department, and SYSTEM_ADMIN -> `200`; update by the recorder -> `200`; archive -> `200` with `status=ARCHIVED`; archived letter still retrievable (confirming soft-delete, not physical deletion) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward, except the three seeded `categories` rows (General Letter,
Notification, Office Order) — those are the intended, permanent V1
configuration, not test artifacts, so they were deliberately left in
place; `lrs_dev` otherwise empty again.

### Validation performed — Phase 4B hardening pass

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **344 passed**, 0 failed, 0 skipped. Re-run 3 consecutive times, identical results |
| `alembic upgrade head` / `downgrade -1` / `upgrade head` against `lrs_dev` (new migration `c887ab35e4a3`) | Full round-trip verified — `uq_letters_reference_number` correctly absent after upgrade, correctly restored after downgrade, correctly absent again after re-upgrade |
| `alembic check` | "No new upgrade operations detected" |
| `grep` for `session.delete` targeting `Letter` across `app/` | Zero matches — confirms `DELETE /api/v1/letters/{id}` never issues a physical `DELETE`, code-level, not just documentation |
| `grep` for hardcoded category names in application logic | Zero matches outside docstrings/comments — Category validation is pure FK + `ACTIVE`-status, no string literals |
| `git status` review | No secrets tracked; `.env` confirmed gitignored; no historical migration file modified |

No live-server re-verification was performed for this specific pass —
the fix (dropping a constraint) is fully covered by the automated
migration round-trip above and the rewritten
`test_letter_registry.py` assertions (duplicates now return `201`, not
`409`), which is direct, repeatable evidence at least as strong as a
one-off manual `curl` session.

### Validation performed — Phase 4A

An architecture review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic tests:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no model, migration, repository, schema, service, endpoint, or test file touched |
| `alembic check` | "No new upgrade operations detected" — no migration was created, consistent with a read-only review |
| `pytest` (full suite) against `lrs_test` | **277 passed**, 0 failed, 0 skipped — unchanged from the Phase 3B.4 hardening pass baseline, confirming the review itself introduced zero regressions (expected, since nothing executable changed) |
| Directory listing of `app/repositories/`, `app/schemas/`, `app/api/v1/endpoints/` | Confirmed empirically (not from memory) that no `Letter`/`Category`/`Classification` repository, schema, or endpoint file exists yet |
| `git log -p` / direct model reads for `Letter.recorded_by`, `Letter.department_id` | Confirmed `RESTRICT` (not `CASCADE`/`SET NULL`) on `recorded_by`, and that `department_id` is an independently-stored column, not derived — both by reading the actual current file content, not assumed from prior-phase memory |

### Validation performed — Phase 3B.4 hardening pass

A follow-up pass after Phase 3B.4's own report, scoped to exactly three
things: (1) fix the one flaky test noted in that report, (2) assess
whether the documented "no ADMIN-purpose authorization revocation" gap is
an actual vulnerability, (3) verify the "`AuthorizationStatus.REVOKED`
existed since Phase 2" claim against real git/migration history. No
Letter functionality, frontend, System Admin handover, or new business
functionality was touched.

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **277 passed**, 0 failed, 0 skipped (274 baseline + 3 new regression tests proving the revocation-scope questions below) |
| Full suite re-run 5 times consecutively | 277/277 passed every time — no flakiness |
| `test_me_with_tampered_token_is_rejected` alone, 20 consecutive isolated runs | 20/20 passed — deterministic (was previously observed to fail ~6% of the time) |
| `alembic check` | "No new upgrade operations detected" — this pass touched only test code and documentation, no models or schema |
| `git log` / `git log -p` on `app/models/enums.py` and `backend/alembic/versions/*.py` | Confirmed `AuthorizationStatus.REVOKED` was present in the very first Phase 2 baseline migration (`3da4b7ee8167`, `down_revision=None`) — both the Python enum and the actual PostgreSQL native enum type. Never modified by the hardening migration (`e8a5cea2ccc6`) or the Phase 3B.3 migration (`a223396c9eac`). The Phase 3B.4 report's claim was **accurate**; no documentation correction needed |
| ADMIN-purpose authorization revocation security assessment (7 questions, see `docs/architecture/user-management.md` §13) | **No vulnerability found.** Absence of an ADMIN-purpose revoke endpoint is a documented capability gap, not an exploitable hole — see that section for the full reasoning. Left unimplemented, as instructed |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` was already empty from the prior pass (no new manual
`lrs_dev` verification was needed for this hardening pass, since nothing
it touched is only reachable via a running server).

### Validation performed — Phase 3B.4

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **274 passed**, 0 failed, 0 skipped at the time of the original 3B.4 report. A subsequent hardening pass found and fixed one pre-existing flaky test (`test_me_with_tampered_token_is_rejected`, Phase 3A) — see "Validation performed — Phase 3B.4 hardening pass" below for the corrected, deterministic result (277 passed, 5/5 consecutive full-suite runs) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.4 required no schema change; `AuthorizationStatus.REVOKED` already existed on the enum since Phase 2, this phase is simply the first to set it |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2/3B.3 tests re-run as part of the full suite | All still pass — no regression |
| Full User lifecycle, run for real against `lrs_dev` via real HTTP with real minted JWTs, two departments and two Admins | Authorize (department correctly derived from the Admin, not client-supplied) → `201`; candidate signup → role `USER`, status `PENDING_APPROVAL`; login while pending → `403`; Admin approves → `200`, status `ACTIVE`; login → valid JWT; protected access → `200`; Admin deactivates → `200`; same stale JWT → `401`; Admin reactivates → `200`; same stale JWT → `200` again (status re-checked live, no re-login needed) |
| Cross-department rejection, run for real | Admin A: `GET`/`approve`/`deactivate` on a Department B User all → `404` (not `403` — existence hidden); Admin A's user listing excludes Department B entirely |
| Revocation, run for real | Admin A creates an authorization → Admin B (different department) attempts revoke → `404`; Admin A revokes own authorization → `200`, `REVOKED`; signup attempt against the revoked authorization → `403` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.3

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1/3B.2 (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **221 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic upgrade` → `downgrade` → `upgrade` → `alembic check` | New migration `a223396c9eac` (adds `user_authorizations.purpose`) round-trips cleanly; zero drift afterward |
| Migration backfill, tested against an actual pre-existing row (not just an empty table) | A row inserted via raw SQL *before* the migration ran was correctly backfilled to `purpose='USER'` after `upgrade` |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2 tests re-run as part of the full suite | All still pass — no regression |
| Full Admin lifecycle, run for real against `lrs_dev` via `curl` with real minted JWTs | Authorize → `201`; candidate signup → role `ADMIN`, status `PENDING_APPROVAL`; login while pending → `403`; approve → `200`, status `ACTIVE`; login → valid JWT; Admin attempting to create a department → `403`; Admin attempting to deactivate self → `403`; System Admin department-transfer → `200`; deactivate → `200`; deactivated Admin's still-unexpired token on a subsequent request → `401` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.2

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1 (`lrs_dev` for manual checks, `lrs_test` for the suite
— never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **174 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.2 required no schema change (the constraint-naming fix changed only how the model declares an existing constraint, not the constraint itself) |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1 tests re-run as part of the full suite | All still pass — no regression |
| Full department CRUD, run for real against `lrs_dev` via `curl` with a real minted SYSTEM_ADMIN JWT | Create → `201`; duplicate name → `409`; list/get/update → correct data; server-controlled-field injection → `422` |
| Full deactivate/reactivate cycle, run for real against `lrs_dev` with a real minted USER JWT in that department | User could access their department (`200`) → SYSTEM_ADMIN deactivated it → same User blocked (`403`) → SYSTEM_ADMIN reactivated it → same User restored (`200`), all against the live server, not `TestClient` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.1

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A (`lrs_dev` for manual checks, `lrs_test` for the suite —
never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **138 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged from Phase 3A) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.1 required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A authentication tests re-run as part of the full suite | All still pass — no regression |
| Full role/department authorization matrix, run for real against `lrs_dev` (SYSTEM_ADMIN/ADMIN/USER × own/other department, via `curl` with real minted JWTs) | Every case matched the documented rule exactly — including the two explicit attack attempts (ADMIN and USER each tried another department's real UUID) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3A

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2 (`lrs_dev` for manual checks, `lrs_test` for the suite — never
a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **96 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — see Known Limitations) |
| `alembic check` | "No new upgrade operations detected" — Phase 3A required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Bootstrap CLI, run for real against `lrs_dev` | Created a SYSTEM_ADMIN with no department, ACTIVE status, hashed password; a second run was correctly refused |
| `POST /auth/login` for the bootstrapped admin | Returned a valid JWT; `GET /auth/me` with it returned the correct profile |
| Full signup flow via real HTTP against `lrs_dev` | Authorized email → `201`, `PENDING_APPROVAL`; unauthorized email → `403`; role-injection attempt → `422`; login while pending → `403` with the correct message; authorization row confirmed `USED` afterward |
| Tampered JWT / missing token via `curl` | Both `401` |
| Frontend build (`npm run build`) | Succeeds — untouched this phase, verified as still working |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 2 (for reference)

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

Nothing — Phase 4D is complete (architecture review and implementation
both) and the project is paused pending explicit instruction to begin
the next phase, per the standing project rule that phases are reviewed
before the next begins.

## Pending (Phase 5 and later)

* **Document deletion for `LetterDocument`** — deliberately not built in
  Phase 4D (physical or soft), matching the review's own recommendation.
  `LetterDocument` still has no lifecycle/status field to soft-delete
  into if that's ever wanted; no requirement has confirmed deletion is
  needed. See `docs/architecture/document-management.md` §14.
* **An optional `checksum_sha256` column on `LetterDocument`** — the one
  schema change Phase 4D's review recommended (nullable, no uniqueness
  constraint); the implementation brief explicitly deferred it
  ("Do not add checksum yet"). See
  `docs/architecture/document-management.md` §12/§28.
* **Department/year/month grouping in the document storage path** —
  Phase 4D's own architecture review recommended layering this on top
  of the per-letter UUID structure for long-term browsability at high
  volume; the implementation brief's literal example
  (`<letter_uuid>/<document_uuid>.<ext>`, no such grouping) was followed
  instead. Revisit if the flat per-letter directory layout becomes
  unwieldy. See `docs/architecture/document-management.md` §33 and
  `storage/README.md`.
* **The text-attachment workflow** (typed `Letter.text_content` vs. an
  uploaded `.txt` file vs. either, at the User's discretion) — the data
  model already supports all three readings without change; only the
  expected workflow is unconfirmed. See
  `docs/architecture/document-management.md` §10.
* **A document-replacement "supersede" workflow distinct from "just
  upload another document"** — the current, implemented behavior
  (uploading again simply adds another `LetterDocument`; nothing is ever
  marked as superseded or hidden) is the safe default Phase 4D's review
  recommended; a first-class "this replaces that" concept would need a
  new field and isn't built. See
  `docs/architecture/document-management.md` §13.
* **The exact classification value list** — no `Classification` rows are
  seeded; a System Admin can create them through the management API once
  the organization confirms the final list (Important/Classified/Budget/
  etc. were always examples, never a closed enumeration the way
  Category's three now are). See `docs/architecture/letter-registry.md`
  §2.5/§12.
* **The exact classified-letter visibility matrix beyond "not every
  department user by default"** — `app/services/authorization.py:assert_letter_access`/
  `letter_visibility_filter` currently allow `ADMIN`/`SYSTEM_ADMIN`/the
  letter's own recorder; this is an explicit, documented, provisional
  default, not a confirmed final policy. See
  `docs/architecture/letter-registry.md` §8/§12 and
  `docs/architecture/registry-search.md` §11.
* **Exact reference-number search semantics beyond "contains"** (Phase
  4C) — prefix matching was considered and not chosen; contains was
  implemented as the more forgiving default. A product/UX question, not
  a blocking one. See `docs/architecture/registry-search.md` §11.
* **Whether a single free-text `search=` box (spanning multiple fields)
  is wanted** alongside the per-field parameters implemented in Phase
  4C. See `docs/architecture/registry-search.md` §11.
* **A revoke endpoint for ADMIN-purpose `UserAuthorization` rows** — Phase
  3B.4 added revocation only for the USER-purpose path
  (`DELETE /api/v1/users/authorizations/{id}`); a System Admin still
  cannot revoke a still-`ACTIVE`, non-expired ADMIN-purpose authorization.
  The repository layer is already purpose-agnostic
  (`find_by_id`/`list_by_department`/`revoke`), so this needs only a new
  endpoint plus a creator/department check mirroring
  `docs/architecture/user-management.md` §9 — see that section's "Known
  limitations".
* **System Admin handover workflow** — see
  `docs/architecture/authentication.md` §9.
* **Automatic audit logging** of authorization-sensitive actions,
  including the four department events (Phase 3B.2), five Admin events
  (Phase 3B.3), five User events (Phase 3B.4,
  `USER_AUTHORIZATION_CREATED`/`REVOKED`/`APPROVED`/`DEACTIVATED`/
  `REACTIVATED`), and Letter lifecycle events (Phase 4B — the service
  remains `AuditLog`-compatible per Phase 4A §19, but no row is written
  yet) — see `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13,
  `docs/architecture/user-management.md` §12, and
  `docs/architecture/letter-registry.md` §13 for the full list.
* **Automatic notification generation** — "a letter was registered" is
  the one confirmed V1 trigger; `Notification.letter_id` is already
  architecturally ready (Phase 4A §20), but no row is written by Phase 4B.
* **Department/Admin/User/Letter/Category/Classification list
  pagination** — deliberately not implemented in any phase so far, but
  every response envelope (`{"items": [...], "total": N}`) was shaped so
  adding it later needs no redesign; see
  `docs/architecture/department-management.md` §3.
* **Clearing an already-set department `code` back to `null`** — not
  possible through `PATCH /api/v1/departments/{id}` today; see
  `docs/architecture/department-management.md` §3, "Known limitation".
* **The same `unique=True` constraint-naming issue fixed for Department
  in Phase 3B.2** still exists on `categories.name` and
  `classifications.name`. Not fixed, since nothing currently depends on
  either constraint's name — the same technique applies if a future
  Category/Classification management phase ever needs it.
* **An email can be authorized as an Admin (or User) candidate while it
  already belongs to an active User (or Admin)** — a narrow, accepted edge
  case in both directions, not a security issue (the existing
  duplicate-email check at signup already prevents any real
  inconsistency); see `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **Frontend authentication/authorization/department/Admin/User-
  management UI** — login/signup pages, protected routing, token storage,
  role-based show/hide. See `docs/architecture/authentication.md` §15 for
  why this remains deliberately deferred.

## Pending Confirmation (from S&IT)

None of the following are implemented as final requirements — each is a
documented, minimal, reversible assumption. See `docs/database/schema.md`
§7 and `docs/architecture/letter-registry.md` §12 for the full reasoning
behind each.

* **Official letter/reference number's existence/format: RESOLVED (Phase
  4B)** — required, manually entered, no format imposed. **Uniqueness
  scope: STILL PENDING** — a global constraint was implemented, then
  removed during a same-phase hardening pass once it became clear the
  business only said "must be unique", never confirming global vs.
  per-department vs. per-source vs. per-year. Duplicates are currently
  accepted anywhere. See `docs/architecture/letter-registry.md` §2.3/§14.
* **Sender identification: RESOLVED (Phase 4B)** — split into
  `source_name`/`source_department_id` (source/origin) and
  `sender_name`/`sender_designation`/`sender_department`/`sender_address`
  (the specific person/office details), superseding the old free-text
  `received_from`. See `docs/architecture/letter-registry.md` §2.1/§2.2.
* **Final category list: RESOLVED (Phase 4B)** — exactly three, closed
  for V1 (General Letter, Notification, Office Order); "Budget" confirmed
  *not* to be one. See `docs/architecture/letter-registry.md` §2.4.
* **Final classification/priority terminology — still open.**
  "Important"/"Classified"/"Budget"/etc. remain examples only; no
  `Classification` row is seeded. What *is* resolved: classification can
  carry access-control significance (§2.5). See
  `docs/architecture/letter-registry.md` §12.
* **Departmental code format** (`departments.code`) — left nullable,
  unformatted. Unrelated to Phase 4B, still open.
* **`letters.subject` requirement-ness: RESOLVED (Phase 4B)** — now
  required via `LetterCreate` (the underlying database column remains
  nullable — see `docs/architecture/letter-registry.md` §3 for why that's
  not a contradiction). `letters.reason` remains nullable and optional,
  unrequested by the finalized decisions, not removed either.
* **Source location / sender address nullability: RESOLVED (Phase 4B)**
  — `source_location` nullable (not required), `sender_address`
  explicitly, deliberately nullable ("do not make Sender Address
  artificially mandatory").
* **Document retention requirements** — not addressed; no retention/expiry
  field exists on `letter_documents`. Unrelated to Phase 4B, still open.

## Known Limitations

* **RESOLVED (Phase 4C)** — the classified-record count/pagination
  leakage risk identified in this phase's own architecture review
  (a non-recording `USER`'s `total` could have included letters they
  couldn't see, once pagination existed) was fixed *before* pagination
  was built, not after: `letter_visibility_filter` makes the
  classified-access rule a SQL `WHERE` clause, and `total`/`items` are
  derived from the identical filtered query. Verified by two dedicated
  regression tests and a live `lrs_dev` check — see
  `docs/architecture/registry-search.md` §1/§9.
* **`letters.reference_number` currently has no uniqueness enforcement
  at all** (Phase 4B hardening pass finding, unchanged by Phase 4C) — a
  global constraint was implemented then removed once it became clear
  the business never actually confirmed the scope ("must be unique"
  alone doesn't say global vs. per-department vs. per-source vs.
  per-year). Duplicates are currently accepted anywhere in the system,
  and a reference-number search can return more than one result. It is,
  however, indexed again (`ix_letters_reference_number`, migration
  `9fa970ffa560`, Phase 4C) — a plain, non-unique index, added because
  reference-number search is a real requirement. See
  `docs/architecture/letter-registry.md` §2.3/§14 and
  `docs/architecture/registry-search.md` §8.
* **RESOLVED (Phase 4B)** — `Letter` now has `recipient_department_id`
  (the department-isolation boundary) and `source_department_id`/
  `source_name` (the letter's origin) as distinct fields; the single-
  field ambiguity Phase 4A flagged (one `department_id` trying to mean
  both at once) no longer exists. See
  `docs/architecture/letter-registry.md` §5 for the migration that
  resolved it.
* **The classified-access visibility policy is a documented, provisional
  default, not a confirmed final one** (Phase 4B) — `ADMIN`/`SYSTEM_ADMIN`/
  the letter's own recorder can view a restricted letter; a `USER` who is
  none of those cannot, even within their own department. See
  `docs/architecture/letter-registry.md` §8/§12.
* **RESOLVED (Phase 4D implementation)** — `LetterDocument` upload,
  listing, and download are implemented
  (`/api/v1/letters/{letter_id}/documents*`). `storage/README.md` now
  documents the actual, implemented path convention (no longer the
  Phase 1 illustrative one, which had no document-identifier segment and
  conflicted with the schema's multi-document capability).
* **`LetterDocument` has no lifecycle/status field** (Phase 4D
  finding, still true) — unlike `Letter`/`User`/`Department`/`Category`/
  `Classification`, there is currently nothing to soft-delete a document
  into. Phase 4D's implementation deliberately built **no document
  deletion endpoint of any kind** (physical or soft), matching the
  review's own recommendation rather than adding one prematurely. See
  `docs/architecture/document-management.md` §14.
* **The document storage path has no department/year/month grouping**
  (Phase 4D implementation, a deliberate deviation from the review's own
  §7 recommendation) — the flat `<letter_uuid>/<document_uuid>.<ext>`
  structure the implementation brief specified literally was built
  instead; revisit if the per-letter directory layout becomes unwieldy
  at high volume. See `docs/architecture/document-management.md` §33.
* **A bare `pytest` invocation from `backend/` produces one unrelated
  collection error** — `app/api/v1/endpoints/dev_authz_test.py`'s
  filename incidentally matches pytest's default `*_test.py` discovery
  pattern, so pytest also tries (and fails) to collect its route-handler
  functions as test functions. Discovered while validating Phase 4D;
  confirmed pre-existing, not a regression, by reproducing the identical
  error against the unmodified pre-Phase-4D tree. `pytest tests/`
  (scoped explicitly, now documented in `backend/README.md`) avoids it;
  not fixed, since renaming or reconfiguring collection for an unrelated
  Phase 3B.1 file is outside this phase's scope.
* **The local `backend/.env` file was inadvertently overwritten during
  Phase 4D's validation** (copied fresh from `.env.example` while
  setting up an `alembic check` run) — `.env` is git-ignored and was
  never committed, so this is local-environment-only, not a repository
  or data issue. No actual data was lost: the real `lrs_dev` database
  and its schema/rows were confirmed completely intact afterward
  (`lrs_dev:lrs_dev` credentials — matching this project's existing
  `lrs_test:lrs_test` convention — still connect, and its 3 seeded
  `categories` rows were reconfirmed unchanged both before and after
  Phase 4D's live verification). `.env` was restored with a freshly
  generated `SECRET_KEY` and `DATABASE_URL` pointed back at `lrs_dev`; a
  freshly generated `SECRET_KEY` invalidates any JWT signed with the
  previous one (an accepted, already-documented consequence of rotating
  this value — see "Configuration" in `backend/README.md`), not a data
  loss. Flagged here for transparency, not because it blocks anything.
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
* **No refresh tokens or token revocation** (Phase 3A) — a token is valid
  until it expires; deactivating the account it belongs to stops it being
  *useful* immediately (re-checked on every request) but doesn't revoke the
  token itself. See `docs/architecture/authentication.md` §16.
* **`UserAuthorization` records no longer require direct database access
  to create** (resolved: ADMIN-purpose via Phase 3B.3, USER-purpose via
  Phase 3B.4) — both now go through `/api/v1/admins/authorizations` and
  `/api/v1/users/authorizations` respectively. Kept here for history: this
  entry described a real gap during Phase 3A, when manual verification of
  the signup flow had to create an authorization directly via the ORM.
* **Bootstrap has no race-condition hardening beyond a single transaction**
  (Phase 3A) — an accepted, documented simplification since it's a rare,
  CLI-only, operator-run action, unlike signup which is fully race-safe.
  See `docs/architecture/authentication.md` §8.
* **`getpass.getpass()` does not accept piped/redirected stdin on Windows**
  — confirmed during Phase 3A's manual verification (it reads directly
  from the console). Not a bug: arguably a desirable property, since it
  stops a password from being accidentally scripted into a piped command.
  The automated test suite calls `create_system_admin` directly rather than
  the interactive CLI wrapper for this reason.
* **No real departmental *business* resource exists yet** — Phase 3B.2
  gave `require_system_admin` its first real resource (departments
  themselves), and Phase 3B.4 finally exercised
  `assert_department_access` as a genuine cross-department, resource-level
  check (User accounts) rather than only the Phase 3B.1 verification-only
  endpoints. Departments/Admins/Users are all still *management*
  resources, though — no Letter or other departmental *business* resource
  exists yet. Not a defect — see `docs/architecture/authorization.md` §7,
  `docs/architecture/user-management.md` §5-6, and Phase 4 in "Pending"
  above.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for both Phase 3B.1 and 3B.2 (brief §15/§21);
  see `docs/architecture/authorization.md` §12 and
  `docs/architecture/department-management.md` §10 for the full list
  scoped for when the relevant actions exist.
* **`Department.name`/`code` needed a constraint-naming fix this phase**
  (Phase 3B.2) — see "Known Limitations" entry below and
  `docs/database/schema.md` §2.1 for the full explanation. No migration
  was required; this was a Python-model-only fix.
* **The same constraint-naming issue is still latent on
  `categories.name`/`classifications.name`** (Phase 3B.2 finding, not
  fixed) — see "Pending" above.
* **A department's `code` cannot be cleared back to `null` via `PATCH`**
  (Phase 3B.2) — only overwritten with a different value. Deliberate
  simplicity tradeoff; see `docs/architecture/department-management.md`
  §3.
* **No pagination on `GET /api/v1/departments`** (Phase 3B.2) — not needed
  at current data volumes; the response envelope was shaped so adding it
  later needs no redesign. See `docs/architecture/department-management.md`
  §3.
* **No way to revoke a still-`ACTIVE`, non-expired ADMIN-purpose
  `UserAuthorization`** (Phase 3B.3 gap, still open after Phase 3B.4) — no
  endpoint sets one to `REVOKED`. The equivalent USER-purpose gap was
  closed in Phase 3B.4 (`DELETE /api/v1/users/authorizations/{id}`); the
  repository layer behind it is already purpose-agnostic, so an
  Admin-management equivalent needs only a new endpoint. See
  `docs/architecture/user-management.md` §12, "Known limitations".
* **An email can be authorized as an Admin candidate while already
  belonging to an active User, and vice versa** (Phase 3B.3/3B.4) —
  narrow, accepted edge case in both directions; see
  `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for Phase 3B.1/3B.2/3B.3/3B.4 (brief
  §15/§21/§25, and this phase's own scope boundary); see
  `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13, and
  `docs/architecture/user-management.md` §12 for the full list scoped for
  when the relevant actions exist.
* **RESOLVED (Phase 3B.4 hardening pass) — `test_me_with_tampered_token_is_rejected`
  (Phase 3A) was occasionally flaky on a full-suite run.** Root cause
  confirmed empirically (5,000-trial script): the old technique flipped
  the *last base64 character* of a 32-byte HMAC-SHA256 signature to a
  fixed value ('A', or 'B' if already 'A'). That character's low 2 bits
  are base64 padding, discarded on decode; 'A' (`000000`) and 'B'
  (`000001`) differ only in that discarded bit. Whenever the signature's
  real trailing 4 bits already happened to be `0000` (the last char
  already 'A', ~1/16 of random signatures — measured 6.10% empirically),
  the "fall back to B" branch silently produced a byte-identical
  signature, so the server correctly accepted it and the test's `401`
  assertion failed. This was a **test-construction bug, not a JWT
  verification weakness** — `app/core/security.py:decode_access_token`
  was never modified. The test now decodes the signature to raw bytes,
  XORs one real byte, and re-encodes (`_tamper_signature`,
  `tests/integration/test_auth_current_user.py`) — verified deterministic
  across 5,000 trials and 20 consecutive isolated test runs.

## Next Recommended Phase

**Phase 5 — Dashboards, notifications, reporting**, or resolving the
outstanding business clarifications first. The registry is now a
complete, tested, paginated/sortable/searchable, department- and
classification-isolated system with working document attachment
upload/list/download — every V1 requirement confirmed so far (finding,
managing, and now attaching files to letters) is built. Recommended
before or alongside Phase 5: resolve the exact classification value list
and the exact classified-visibility matrix with the product owner
(`docs/architecture/letter-registry.md` §12,
`docs/architecture/registry-search.md` §11) — document access on a
classified letter is exactly the kind of surface where the current
provisional policy's limits become more visible than plain CRUD already
made them, and Phase 4D's document authorization now depends on that
same policy too; the text-attachment workflow question
(`docs/architecture/document-management.md` §10, typed content vs.
uploaded `.txt`); and whether document deletion or a `checksum_sha256`
column is ever actually needed (`docs/architecture/document-management.md`
§12/§14) before either is built speculatively.
