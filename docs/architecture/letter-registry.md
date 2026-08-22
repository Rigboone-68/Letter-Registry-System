# Letter Registry Core — Architecture (Phase 4A review + Phase 4B finalized decisions)

**Status: Phase 4A (review) complete. Phase 4B (implementation) in
progress/complete — see `docs/PROJECT_STATUS.md` for the exact current
state.** This document first records the six business decisions the
product owner finalized after Phase 4A's review, then the resulting
schema/authorization design, then what remains genuinely open. Sections
carried over unchanged from Phase 4A are marked as such; nothing here
should be read as inventing an answer the product owner didn't give.

## 0. How to read this document

Every claim is tagged as one of:

* **CONFIRMED REQUIREMENT** — stated directly by the organization/product
  owner.
* **FINALIZED DECISION (Phase 4B)** — one of the six business decisions
  explicitly resolved before this phase began. Treated as authoritative,
  not reinterpreted.
* **IMPLEMENTATION DECISION** — a concrete design choice this phase had to
  make to turn a finalized decision into working code, where the decision
  itself left a narrower detail unspecified (e.g., exact role scope for
  Letter update). Documented explicitly so it can be revisited, not
  silently assumed.
* **PENDING BUSINESS CLARIFICATION** — still genuinely open; not guessed
  into a constraint or a policy.

## 1. Confirmed business requirements (unchanged from Phase 4A)

A representative letter contains: reference number, source/sending
department, source location, subject, letter content, recipient
department, sender details, and date received/recorded. Confirmed V1
categories: **General Letter**, **Notification**, **Office Order**
(spelling finalized as singular "Order" in Phase 4B, superseding Phase
4A's "Office Orders"). The actor/ownership hierarchy
(`SYSTEM_ADMIN → Department → ADMIN → USER`) is unchanged; a User records/
edits letters within their own department; historical records must
survive account deactivation and department transfer.

## 2. The six finalized decisions

### 2.1 Source department / source identification

**FINALIZED DECISION**: a letter's source is recorded as **one required
free-text field plus one optional structured reference**:

* `source_name` (required) — the source's name as it appears on the
  physical letter, or manually entered. This is the baseline
  representation every letter has.
* `source_department_id` (optional FK → `departments.id`) — populated
  only when the source happens to be a department already registered in
  LRS. Never required, since "the system must NOT force every source
  into a department FK" (product owner's own wording) — many incoming
  letters originate from organizations LRS has no record of.

This is a rename-plus-addition to the existing `Letter.received_from`
column (Phase 2), not a new concept: `received_from` already served
exactly `source_name`'s role (free-text sender identity, "not assumed to
be a government department"). The migration (§7) renames it rather than
adding a parallel column, preserving every existing value with no data
loss.

**Recipient Department remains the department-isolation boundary** —
unchanged from the Phase 4A recommendation, now implemented as
`recipient_department_id` (renamed from the ambiguous `department_id`;
§7). Source and recipient are never the same column, never derived from
each other, and `source_department_id` is deliberately **not** an
authorization boundary — an external sender has no LRS account and isn't
part of the role/department hierarchy at all (unchanged from Phase 4A
§13's reasoning).

### 2.2 Sender details

**FINALIZED DECISION**: sender details are **required for every letter**,
as four discrete fields, not one free-text block:

* `sender_name` (required)
* `sender_designation` (required)
* `sender_department` (required, free text)
* `sender_address` (optional — "may be NULL because the physical letter
  may not provide one")

**A deliberate, acknowledged overlap, preserved as specified — not
collapsed.** `sender_department` (this section) and `source_department_id`/
`source_name` (§2.1) can describe the same real-world department (e.g.
both might read "Planning & Development Department" for a letter from
that department's Director). The finalized decisions list both as
distinct, independently required/optional fields rather than merging
them, so both are implemented as separate columns. This document flags
the overlap rather than silently resolving it: `sender_department` is the
sender's own stated department (part of *who signed the letter*,
essentially free text describing the signer's affiliation), while
`source_department_id`/`source_name` describe *the originating
organization the letter is from* — in practice usually the same value,
occasionally not (e.g. a sender might write on behalf of a different
office than their home department). No validation ties the two together;
neither is derived from the other.

### 2.3 Reference number

**FINALIZED DECISION**: `reference_number` — required, manually entered
by the User (never auto-generated), a plain string (letters, numbers,
special characters all permitted, no format imposed).

**Uniqueness scope: PENDING BUSINESS CLARIFICATION — revised during a
Phase 4B hardening pass.** The finalized decision says "Must be UNIQUE"
with no scope qualifier. The initial implementation read this as
*globally* unique and added `uq_letters_reference_number` — on review,
that scope was never actually confirmed, and picking the broadest
possible interpretation is itself an assumption, not a neutral default:
this is a real multi-department registry, and two different sending
departments could easily each issue their own overlapping numbering
(e.g. both using "001/2026" internally). A global constraint would
reject the second such letter with a `409` for a scope the business
never asked for. The constraint was **removed** (migration
`c887ab35e4a3`) rather than kept on a guess or replaced with a
*different* guessed scope (e.g. per-department) — per instruction, no
replacement rule was invented. `reference_number` remains required
(`NOT NULL`, non-blank) — only the uniqueness *scope* is unresolved.
Duplicate reference numbers are currently accepted anywhere in the
system; see §12.

### 2.4 Letter categories

**FINALIZED DECISION**: exactly three, closed for V1 — **General Letter**,
**Notification**, **Office Order**. "Budget" is explicitly confirmed to
**not** be a Category (superseding Phase 4A's open question about where
"Budget" belongs — see §2.5 for what this does and does not resolve about
Classification).

The existing `Category` table (`name`, `description`, `status`) needs no
schema change — it was already structurally suitable (Phase 4A §11). What
was missing was the management surface and the seed data; both are added
this phase (§9, §10). The three names are seeded by the migration (§7),
not hard-coded into application logic — `Letter.category_id` continues to
be a plain FK validated against a real, `ACTIVE` `Category` row, so a
client cannot inject an arbitrary category name through Letter creation
(there is no `category_name` field on the create schema — only
`category_id`, a UUID referencing an existing row). The management CRUD
itself is **not** artificially capped at three rows in code — "System
Admin controls categories" has been this project's standing principle
since Phase 2, and nothing in this decision asks for a hard system-level
lock preventing a System Admin from ever adding a fourth. "Do not
introduce additional categories" is honored here as an instruction about
this implementation (seed exactly three, invent no more), not as new code
that permanently forbids a System Admin's own tool from doing its job.

### 2.5 Classification

**FINALIZED DECISION, two parts — one resolved, one deliberately left
open:**

**Resolved**: Classification is not purely descriptive. A classification
can carry **access-control significance** — specifically, a letter whose
classification is marked as restricting access "must not automatically
become visible to every user who can otherwise access the recipient
department" (product owner's own wording). This is a real behavioral
requirement, not just a data-modeling one, and Phase 4B implements a
working, tested restriction — see §11 for the mechanism.

**Explicitly not resolved, not guessed**: the *exact* classification
value list (Important/Classified/Budget/etc. were always Phase 4A
examples, "such as ... etc.", never a closed enumeration the way Category
now is) and the *exact* visibility matrix (precisely which roles/users can
see a restricted letter beyond "not automatically every department user")
remain open. Per explicit instruction not to invent either: **no
Classification rows are seeded** this phase (unlike Category's three,
which were given as a closed, finalized list — Classification's were
never given that way), and the visibility mechanism implemented (§11) is
documented as a conservative, provisional default, not a confirmed final
policy. See §12 for the full reasoning and what remains open.

### 2.6 Source location / nullability

**FINALIZED DECISION**: `source_location` — free text, captured for every
letter where known. Not marked required in the decision (only sender
fields other than address were explicitly called "required"), so it
follows the same nullable-pending-further-confirmation pattern as
`subject`/`reason` since Phase 2. `sender_address` is explicitly,
deliberately nullable — "do not make Sender Address artificially
mandatory" is an explicit constraint on this implementation, not a
default this document chose on its own.

## 3. Final `Letter` column list (as implemented)

| Column | Type | Nullable | Source of the decision |
|---|---|---|---|
| `id` | UUID PK | no | Unchanged |
| `reference_number` | varchar(255) | **no** (required); no uniqueness constraint — removed by `c887ab35e4a3`, see §2.3 | §2.3 |
| `recipient_department_id` | UUID FK → `departments.id`, `RESTRICT` | no | §2.1, renamed from `department_id` |
| `source_name` | varchar(500) | no | §2.1, renamed from `received_from` |
| `source_department_id` | UUID FK → `departments.id`, `RESTRICT` | yes | §2.1, new |
| `source_location` | varchar(255) | yes | §2.6, new |
| `sender_name` | varchar(255) | no | §2.2, new |
| `sender_designation` | varchar(255) | no | §2.2, new |
| `sender_department` | varchar(255) | no | §2.2, new (distinct from `source_department_id` — see §2.2) |
| `sender_address` | text | yes | §2.2/§2.6, new |
| `subject` | varchar(500), indexed | yes | Unchanged (Phase 2, nullability still not explicitly confirmed) |
| `reason` | text | yes | Unchanged (Phase 2, kept — not requested by this phase's field list, not conflicting either) |
| `category_id` | UUID FK → `categories.id`, `RESTRICT` | yes | Unchanged — see §2.4/§9 for why nullability wasn't flipped |
| `classification_id` | UUID FK → `classifications.id`, `RESTRICT` | yes | Unchanged |
| `received_at` | timestamptz, indexed | no | Unchanged — business date, see Phase 4A §9 |
| `recorded_by` | UUID FK → `users.id`, `RESTRICT` | no | Unchanged — always the authenticated caller, never client-supplied |
| `text_content` | text | yes | Unchanged — maps to "Letter Content" |
| `status` | `letter_status` enum | no | Unchanged — `ACTIVE`/`ARCHIVED` |
| `created_at` / `updated_at` | timestamptz | no | Unchanged — `created_at` is the "date recorded" fact, see Phase 4A §9 |

**Category/Classification nullability was deliberately not changed.**
Neither the Phase 4A brief nor the Phase 4B finalized decisions state
that every letter must have a category or classification assigned at
creation time — §2.4 confirms *which* categories are valid, §2.5 confirms
classification's *behavior*, neither confirms that assignment is
mandatory. Leaving both nullable is the conservative reading; flipping to
`NOT NULL` later is a safe, additive migration if the organization
confirms it should be mandatory, matching this project's established
"don't over-constrain what isn't confirmed" convention (Phase 2's
`subject`/`reason`, unchanged here).

## 4. Migration strategy (implemented — see `docs/database/schema.md` for the applied migrations' exact identity)

**Two** Alembic revisions, each built against the actual current head at
implementation time (not assumed): `48ec742d9e8f` (the Phase 4B
implementation) and `c887ab35e4a3` (a same-phase hardening-pass
correction — see step 5 below and §2.3). Applied changes from
`48ec742d9e8f`, in dependency order:

1. **Rename `letters.department_id` → `recipient_department_id`.** A
   plain `ALTER TABLE ... RENAME COLUMN` — PostgreSQL preserves the
   column's data, `NOT NULL`, and foreign key constraint across a rename;
   no `UPDATE` statement is needed and no row is rewritten. The FK
   constraint and both indexes referencing the column
   (`ix_letters_department_id`, the composite
   `ix_letters_department_received_at`) are explicitly renamed to match
   (`ix_letters_recipient_department_id`,
   `ix_letters_recipient_department_received_at`), so DDL introspection
   and `alembic check` stay unambiguous — matching the constraint-naming
   discipline this project adopted after the Phase 3B.2 `Department.name`/
   `code` incident.
2. **Rename `letters.received_from` → `source_name`.** Same
   rename-preserves-data reasoning; `NOT NULL` is preserved unchanged.
3. **Add nullable columns**: `source_department_id` (FK → `departments.id`,
   `RESTRICT`, indexed), `source_location`, `sender_address`.
4. **Add required columns with a safe backfill**, since existing rows (if
   any) have no value for a brand-new `NOT NULL` column — the same
   add-nullable → backfill → tighten pattern this project used for
   `user_authorizations.purpose` in Phase 3B.3: `sender_name`,
   `sender_designation`, `sender_department`, `reference_number`. Any
   pre-existing row is backfilled to a clearly-marked placeholder value
   (not a guess at real content) before the column is tightened to `NOT
   NULL` — see the migration file's own docstring for the exact
   placeholder text and why a placeholder, not a blank string, was
   chosen (a blank string would silently pass future `NOT NULL`
   validation while looking like real data; a placeholder is visibly a
   migration artifact requiring follow-up).
5. **Added, then removed, `reference_number`'s unique constraint.**
   `48ec742d9e8f` originally added `uq_letters_reference_number`
   (explicitly named), reading the finalized "must be unique" decision as
   globally scoped. A same-phase hardening pass found that scope was
   never actually confirmed — "unique" alone doesn't say global vs.
   per-department vs. per-source vs. per-year, and a real multi-
   department registry can easily have two departments each issue their
   own overlapping numbering. Rather than keep a guessed constraint,
   migration `c887ab35e4a3` **drops it**, without substituting a
   different guessed scope. `reference_number` remains required
   (`NOT NULL`); only its uniqueness scope is now PENDING BUSINESS
   CLARIFICATION — see §2.3/§12.
6. **Add `classifications.restricts_access`** (boolean, `NOT NULL`,
   `server_default=false`) — see §11.
7. **Seed exactly three `Category` rows** — General Letter, Notification,
   Office Order, all `ACTIVE` — a data migration, not a schema change; see
   §2.4. No `Classification` rows are seeded (§2.5).

**Historical data preservation**: every existing `Letter` row's
`recipient_department_id` (post-rename) holds exactly the value its
`department_id` held before the migration — a rename cannot lose or alter
data, unlike a drop-and-recreate. This was verified directly against a
pre-existing row inserted before the migration ran, not only asserted
from reading the migration script — see
`tests/integration/test_letter_registry.py` for the test that proves it.

**Reversible**: each migration's `downgrade()` reverses every step in
opposite order (`c887ab35e4a3` re-adds `uq_letters_reference_number`;
`48ec742d9e8f` drops the seeded categories, drops `restricts_access`,
drops the new/backfilled columns, renames `source_name`/
`recipient_department_id` back) — verified with a full
`upgrade → downgrade → upgrade` cycle against a real PostgreSQL instance
for both, same validation standard as every migration since Phase 2. One
accepted asymmetry: downgrading `c887ab35e4a3` after real duplicate
`reference_number` values have been inserted (now possible, since
nothing prevents them) will fail to re-add the unique constraint —
inherent to reverting a constraint after data has diverged from it, not
specific to this migration.

## 5. Department isolation — recipient department, now concrete

`app/services/authorization.py:assert_department_access` (unchanged since
Phase 3B.1) is called with `letter.recipient_department_id` — exactly the
resource-level pattern Phase 3B.4 established for User management, reused
without modification. `source_department_id` is never passed to this
function; it carries no authorization meaning (§2.1).

## 6. Historical identity and historical department (unchanged principles, now applied to the renamed field)

Both guarantees Phase 4A confirmed already held are unchanged in kind,
only in the renamed column they apply to:

* `Letter.recorded_by` remains `ForeignKey("users.id", ondelete="RESTRICT")`
  — never touched by this phase's migration.
* `Letter.recipient_department_id` remains an **independently stored
  column**, set once at creation from the recording User's department at
  that moment, never re-derived from `recorded_by_user.department_id` at
  query time. The rename does not change this property — a column rename
  cannot introduce a derived/joined value where a stored one existed
  before. `tests/integration/test_letter_registry.py` proves this
  directly (not just re-asserts it) for the renamed field, the same way
  Phase 3B.3/3B.4 proved it for `User.department_id` after an Admin/User
  transfer.

## 7. Category management

`app/services/category_service.py` — System-Admin-only CRUD
(create/list/get/update/activate/deactivate), directly mirroring
`docs/architecture/department-management.md`'s established pattern:
race-safe duplicate-name detection via a caught `IntegrityError` (not a
pre-check), never-physically-deleted (`status` moves to `INACTIVE`,
already true of `Category` since Phase 2), `require_system_admin`
(Phase 3B.1, reused unchanged). No new authorization primitive was
needed. Seeded rows (§2.4) are ordinary `Category` rows indistinguishable
from any a System Admin creates later through this same API — nothing
about them is hard-coded as special-cased or immutable.

## 8. Classification management and the classified-access boundary

`app/services/classification_service.py` — same CRUD pattern as Category
(§7), with one addition: `restricts_access` (boolean, default `false`),
settable only by `SYSTEM_ADMIN` through this management API, never by an
Admin/User and never implicitly derived from a classification's `name`
(no string-matching on "Classified" or similar — the flag is the single
source of truth, exactly the same "don't derive security-relevant state
from a label" reasoning this project already applies to role/status
enums).

**The classified-access boundary** — `app/services/authorization.py:assert_letter_access`
(new function, added alongside `assert_department_access`, not a
competing mechanism):

```python
def assert_letter_access(user: User, letter: Letter) -> None:
    assert_department_access(user, letter.recipient_department_id)
    if user.role == UserRole.SYSTEM_ADMIN:
        return
    if letter.classification is not None and letter.classification.restricts_access:
        if user.role == UserRole.USER and letter.recorded_by != user.id:
            raise ClassifiedAccessDeniedError()
```

Order matters: department isolation is always checked first (an
out-of-department caller learns nothing more by also being told a letter
is classified), then `SYSTEM_ADMIN` retains complete access (explicit
instruction — "System Administrator must retain complete administrative
control"), then a restricted classification narrows further for a plain
`USER` who is not the letter's own recorder. `ADMIN` (within the correct
department, already passed the first check) is never narrowed by this
clause — an Admin can always see every letter in their own department,
classified or not.

**This is a provisional, conservative default, not a confirmed final
policy** — the exact visibility matrix was explicitly left open by the
product owner (§2.5). What's implemented today: a `USER` who didn't
record a classified letter cannot view/update/archive it, even within
their own department; an `ADMIN` or `SYSTEM_ADMIN` always can. This
satisfies the one concrete requirement given ("not automatically visible
to every user who can otherwise access the recipient department") without
inventing details the product owner didn't specify (e.g. whether specific
named Users should be individually grantable access, whether the
restriction should also apply to Admins, whether there should be a
time-limited declassification). **`assert_letter_access` is the single
seam every future refinement of this policy needs to change** — no Letter
CRUD code calls any narrower or duplicate check, so tightening or
loosening the exact rule later is a one-function change, not a Letter-
table redesign, per the explicit instruction to leave that door open
without redesigning the table.

## 9. Letter service / repository / API

`app/repositories/letter_repository.py`, `app/services/letter_service.py`,
`app/schemas/letter.py`, `app/api/v1/endpoints/letters.py` — the same
four-layer vertical slice every phase since 3A has used, no new
architectural pattern. `recorded_by` and `recipient_department_id` are
always derived from `current_user` server-side; `LetterCreate`/
`LetterUpdate` have no field for either, `extra="forbid"`, same
established convention. See `docs/PROJECT_STATUS.md`'s Phase 4B entry for
the exact endpoint list and status codes.

**IMPLEMENTATION DECISION — role scope for create/read/update/delete**,
since the finalized decisions confirm department scoping but not
finer-grained per-record ownership: `USER` and `ADMIN` share identical
CRUD access within their own department (create, read, update, archive/
"delete") — narrowed only by §8's classified-access boundary for `USER`.
`SYSTEM_ADMIN` has global read access (via `assert_department_access`'s
existing bypass) but does not create letters (a `SYSTEM_ADMIN` has no
`department_id` to record one against — the same structural fact that
already keeps System Admin out of every other department-scoped
operation in this project). "Only the recording User can edit their own
letter" was considered and **not** implemented — nothing in the finalized
decisions supports that narrower rule, and inventing it would be exactly
the kind of unrequested restriction this project has consistently avoided
adding. If the organization wants per-record ownership restrictions
later, `assert_letter_access` (§8) is again the one seam to extend.

**"Delete" is archive, not physical deletion** — consistent with, not a
change to, the existing Phase 2 `LetterStatus` design (`ACTIVE`/
`ARCHIVED`, "V1 archival is a status change", unchanged and explicitly
preserved by the Phase 4B decisions' instruction to reuse existing
architecture). `DELETE /api/v1/letters/{id}` sets `status = ARCHIVED`; no
SQL `DELETE` statement is ever issued against a `Letter` row by this
service. This avoids re-litigating a decision Phase 2 already made and
this phase's brief didn't ask to reopen.

**Re-verified during a Phase 4B hardening pass, code-level, not just by
re-reading this doc**: `grep`-ing `app/` for `session.delete` targeting
`Letter` returns nothing — `archive_letter`
(`app/services/letter_service.py`) calls only
`LetterRepository.update_status`, a plain `letter.status = status`
attribute set. `letter_documents.letter_id`/`notifications.letter_id`'s
`ON DELETE CASCADE` (Phase 2) stays dormant — it only matters if a
`Letter` row is ever physically removed, which no code path in this
project does. Archiving a letter destroys nothing: its documents,
notifications, and all other data remain exactly as they were, only
`status` changes, and it remains fully retrievable via `GET` afterward
(`test_archive_letter_sets_status_archived_not_physical_delete`).

## 10. Reference number uniqueness — REMOVED (Phase 4B hardening pass)

**No longer enforced at the database level.** `48ec742d9e8f` originally
added `UniqueConstraint("reference_number", name="uq_letters_reference_number")`
in `__table_args__`, reading the finalized "must be unique" decision as
globally scoped — that scope was never actually confirmed (see §2.3), so
migration `c887ab35e4a3` drops the constraint rather than keep it on a
guess. `LetterService.create_letter`/`update_letter` no longer attempt/
catch an `IntegrityError` for this — there is nothing left for that flush
to realistically violate (see each method's own comment). Duplicate
reference numbers are currently accepted, anywhere in the system,
without conflict.

**For the record, the now-removed original design**: `create_letter`/
`update_letter` did not pre-check for a duplicate; they attempted the
insert/update and caught the resulting `IntegrityError`, inspecting
`orig.diag.constraint_name` to confirm it was this specific constraint
before translating it into a clean `409` — the same race-safe pattern
`DepartmentService` has used since Phase 3B.2. That pattern is exactly
right *if and when* a real uniqueness constraint returns (whatever scope
the business confirms) — nothing about the pattern itself was wrong,
only the guessed scope of the constraint it was protecting.

## 11. Searchability (unchanged principle, one addition)

All indexes recommended in Phase 4A §17 are implemented, retargeted at
the renamed/new columns: `recipient_department_id` (+ composite with
`received_at`, replacing the old `department_id` composite),
`source_department_id`. `reference_number` has **no index** — it lost
the one it implicitly had (PostgreSQL auto-backs a `UNIQUE` constraint
with an index) when `uq_letters_reference_number` was removed (§2.3/§10);
a plain `CREATE INDEX` for lookup-by-number without a uniqueness
guarantee would be a reasonable, low-risk addition once real usage shows
it's needed, but wasn't added speculatively. `source_name`,
`source_location`, `sender_name`/`sender_designation`/`sender_department`/
`sender_address` remain unindexed — no confirmed filter/search
requirement exists for them yet, and an unused index only adds write
overhead (same reasoning Phase 4A §17 already applied). **Full-text
search is still not implemented** — unchanged from Phase 4A §17; nothing
in the finalized decisions asks for it, and the explicit Phase 4B
instruction repeats "do not over-engineer V1 search."

## 12. What remains genuinely open (not guessed)

0. **`reference_number`'s uniqueness scope** (global? per receiving
   department? per source? per year?) — PENDING BUSINESS CLARIFICATION,
   identified and corrected during a Phase 4B hardening pass; see §2.3.
   No constraint is currently enforced; duplicates are accepted anywhere.
1. **The exact classification value list.** No `Classification` rows are
   seeded this phase (§2.5). A System Admin can create them through the
   management API once the organization confirms the final list.
2. **The exact classified-letter visibility matrix beyond "not every
   department user by default."** §8's `ADMIN`/`SYSTEM_ADMIN`/recorder
   default is explicitly provisional.
3. **Whether `sender_department` and `source_department_id`/`source_name`
   should ever be validated against each other** (§2.2) — currently
   independent, no cross-field validation exists.
4. **Whether `category_id`/`classification_id` should become mandatory**
   at letter creation — currently both remain nullable (§3).
5. **Whether a letter's `recipient_department_id` can ever change after
   creation** (a transfer/reassignment between departments) — not asked
   for by this phase's decisions, not implemented; a letter's recipient
   department is fixed at creation, matching §6's historical-preservation
   requirement by construction (there is no endpoint that would let it
   change).

## 13. Explicitly NOT in this phase

File upload/download (`LetterDocument` relationship is unchanged and
compatible, per Phase 4A §16 — not implemented), dashboards, automatic
notification generation, automatic audit logging (the Letter service
remains `AuditLog`-compatible per Phase 4A §19 — no row is written by
this phase), full-text search, frontend, System Admin handover, any
change to unrelated RBAC/authentication functionality.

## 14. Phase 4B hardening pass — findings

A pre-commit correctness/security review of the Phase 4B implementation
above, before anything was committed. One real defect found and fixed
(reference-number uniqueness scope, §2.3/§10/§12); everything else
re-verified, code-level, against the claims already in this document.
Findings tagged with this document's own taxonomy (§0):

**DELETE / archival — CONFIRMED safe, re-verified.** `DELETE
/api/v1/letters/{id}` never issues a SQL `DELETE` — see §9's "Delete is
archive" paragraph, now with the exact `grep` evidence appended. No
change made; already the safest available interpretation of "Delete
Letter, subject to authorization" given this project's standing "letters
are never physically deleted" principle (Phase 2, unchanged).

**Reference number uniqueness — ARCHITECTURAL DECISION reversed; now
PENDING BUSINESS CLARIFICATION.** See §2.3. The only substantive change
this hardening pass made.

**Sender field migration placeholders — CONFIRMED safe, no change
needed.** `sender_name`/`sender_designation`/`sender_department` were
backfilled to the literal string `'MIGRATION-PLACEHOLDER'`
(`reference_number` to `'MIGRATED-' || id`) — see migration
`48ec742d9e8f`'s own docstring. Neither string could plausibly be
mistaken for real business data (no fabricated name, title, or
department was invented) regardless of whether the row being backfilled
was real or test data. Separately, no real production data could exist
at all: this project has never been deployed (Phase 1 was "Initial
project foundation"; `lrs_dev`/`lrs_test` are explicitly documented
throughout this project as disposable local instances, never a real
departmental database). Both facts hold independently — the placeholder
choice would have been safe even if the second weren't true.

**Source vs. sender semantics — ARCHITECTURAL DECISION, documented,
not a verbatim business statement.** §2.1/§2.2 already establish: `source_name`/
`source_department_id` describe the *organization* a letter originated
from; `sender_name`/`sender_designation`/`sender_department` describe
the *individual who signed it* (a name, a title, and their stated
affiliation). The finalized decisions support this reading structurally
(a "Source" field pair and a separate "Sender Name/Designation" field
group) but never state the organization-vs-person framing in those exact
words — this document's own architectural inference, not a quoted
requirement. Not redefined by this hardening pass; flagged here as
exactly that kind of inference, for transparency, per instruction.

**`source_department_id` vs. `sender_department` — CONFIRMED
intentional, both retained.** Already documented in §2.2 as a deliberate,
acknowledged overlap (both may describe the same real-world department;
neither is derived from the other; the finalized decisions list both as
independently required/optional fields rather than merging them). Not
collapsed by this hardening pass — no evidence supports treating them as
the same field, and the instruction was explicit not to change the model
without evidence.

**Classification security — CONFIRMED/PROVISIONAL split, re-verified
against actual code.**
* CONFIRMED: System Admin exclusively controls `Classification` rows,
  including `restricts_access` (§8) — verified via
  `require_system_admin` on every `/api/v1/classifications*` route and
  `test_classification_management.py`'s authorization tests.
* PROVISIONAL (technical capability, not a final business policy):
  `restricts_access` narrows visibility to `SYSTEM_ADMIN`/`ADMIN`/the
  letter's own recorder — re-read directly from
  `app/services/authorization.py:assert_letter_access` for this pass, not
  assumed from memory; matches exactly what was previously reported. No
  additional role-based rule was added.
* PENDING: the exact business access matrix for a Classified record —
  unchanged, still open (§12 item 2).

**Category seeding — CONFIRMED correct, one wording note.** The
migration seeds `"General Letter"`, `"Notification"`, `"Office Order"`
(singular "Order") — re-verified directly against the migration file and
a live `GET /api/v1/categories` response. This matches the actual
finalized Phase 4B decision text exactly. (Phase 4A's original brief, and
this hardening pass's own review prompt, both used "Office Orders"
(plural) — already noted in §1 as a wording difference this
implementation resolved in favor of the later, more authoritative
finalized-decision text, not an oversight.) No duplicates; `ACTIVE`
status confirmed; application code has zero string-literal category-name
checks (`grep`-verified) — only FK + `ACTIVE`-status validation, so
System Admin remains the sole authority over the category set going
forward.

**Department isolation — CONFIRMED, re-verified against code and real
cross-department test data.** `assert_letter_access` checks
`letter.recipient_department_id` exclusively — `source_department_id` is
never passed to `assert_department_access` anywhere in this codebase
(`grep`-verified). `test_letter_registry.py`'s isolation tests create
real rows in two distinct departments and assert against actual API
responses (404s, list exclusions), not mocked state.

**Historical User identity — CONFIRMED, unchanged.** `Letter.recorded_by`
is `ForeignKey("users.id", ondelete="RESTRICT")` — re-read directly from
the model for this pass. No cascade delete exists or was introduced.

**Historical department — CONFIRMED, re-verified with a real
department-transfer test.** `recipient_department_id` is an independently
stored column, never derived from `recorded_by_user.department_id` at
query time.
`test_letter_recipient_department_survives_recorders_department_transfer`
creates a Letter, transfers its recording Admin to a different
department via the real `/api/v1/admins/{id}/department` endpoint, then
reloads the Letter row directly (`db_session.get`, after
`expire_all()`) and asserts `recipient_department_id` is unchanged —
inspects the actual database row, not just the API response.

**Letter create/update input security — CONFIRMED, re-verified against
the actual schema file.** `LetterCreate`/`LetterUpdate`
(`app/schemas/letter.py`) have `extra="forbid"` and no field for
`recorded_by`, `recipient_department_id`, `status`, `created_at`, or
`updated_at` — re-read directly, not assumed. `recipient_department_id`
is therefore structurally immutable through this API: there is no code
path, in create or update, that could ever change which department a
letter belongs to after it's recorded — confirmed as the correct,
intentional V1 behavior (letter transfer between departments was never
requested — §12 item 4).

**Letter status — CONFIRMED pre-existing, not introduced by Phase 4B.**
`LetterStatus` (`ACTIVE`/`ARCHIVED`) has existed since Phase 2; Phase 4B
did not add a new lifecycle, only wired the pre-existing `ARCHIVED` value
to the new `DELETE` endpoint (§9). No workflow status was invented.

**Content storage — CONFIRMED unchanged.** `text_content` (textual
content) and `LetterDocument` (metadata-only attachment records) are
both unchanged from Phase 4A/4B's original design; no upload/download
code exists or was added by this hardening pass.

**Migration safety — CONFIRMED.** `48ec742d9e8f`'s `down_revision`
correctly points to the real prior head (`a223396c9eac`); the new
`c887ab35e4a3`'s `down_revision` correctly points to `48ec742d9e8f`.
Full `upgrade → downgrade → upgrade` verified for both, against a real
PostgreSQL instance. No historical migration file was modified — the
fix is a new, third revision. `alembic check`: "No new upgrade operations
detected."
