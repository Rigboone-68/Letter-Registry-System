# Document Management — Architecture Review & Implementation (Phase 4D)

**Status: IMPLEMENTED.** §1-32 below are the original architecture
review (unchanged from the review pass — kept as the design rationale);
see **§33, "Implementation record"** for what was actually built on top
of it, including two places where the implementation brief's own
explicit instructions were simpler than this review's recommendation
(and which one was followed, and why).

This document originally reviewed what already existed for
`LetterDocument` (verified fresh against the current repository, storage
directory, and `.gitignore` — not assumed from any prior phase's report),
and designed the storage, validation, naming, authorization, and
lifecycle architecture document upload/download would need — including
reconciling a real conflict found between two pieces of pre-existing
documentation (§7). That design is now implemented; §33 records the
result.

## 0. How to read this document

* **CONFIRMED** — verified directly against current code, migrations,
  configuration, or the actual filesystem/`.gitignore`.
* **RECOMMENDED** — this document's own proposal (§1-32), grounded in
  confirmed facts and this project's established conventions. Where
  §33 doesn't say otherwise, treat these as implemented as recommended.
* **PENDING** — genuinely open; not guessed into a schema or a policy.
* **IMPLEMENTED** (§33 only) — built, tested, and live-verified this
  phase.

## 1. Existing document architecture (verified fresh)

Read directly this session: `app/models/letter_document.py`,
`app/models/letter.py`, `app/core/config.py`,
`app/services/letter_service.py`, `app/repositories/letter_repository.py`,
`app/schemas/letter.py`, `app/api/v1/endpoints/letters.py`,
`app/services/authorization.py`, `app/main.py`, both migrations touching
`letter_documents`, `storage/README.md`, `.gitignore`, and the actual
`storage/` directory tree.

**CONFIRMED — what exists:**

* `LetterDocument` table (unchanged since the Phase 2 baseline migration,
  except one index added in the Phase 2 hardening migration): `id`,
  `letter_id` (FK → `letters.id`, `ON DELETE CASCADE`), `document_type`
  (free string, nullable), `original_filename` (required),
  `storage_path` (required), `file_size` (nullable), `mime_type`
  (nullable), `uploaded_by` (FK → `users.id`, `ON DELETE RESTRICT`),
  `uploaded_at` (server-defaulted).
* **No application code populates any of this** — grepped
  `app/services/`, `app/repositories/`, `app/schemas/`, `app/api/` for
  `LetterDocument`/`storage_path`/`STORAGE_PATH`/`upload`/`download`:
  zero real matches (only a stale Phase 1 docstring in
  `app/api/v1/endpoints/__init__.py` mentioning "documents" as a future
  module). No upload endpoint, no download endpoint, no storage service,
  no validation code.
* `STORAGE_PATH` (`app/core/config.py`) = `"../storage/letters"` — a
  **relative** path, currently unused by any code path.
* `app/main.py` does **not** mount `StaticFiles` or any public
  static-serving route — confirmed by direct inspection, not assumed.
* The physical `storage/letters/` directory exists (empty except
  `.gitkeep`); `.gitignore` excludes its contents
  (`storage/letters/*` / `!storage/letters/.gitkeep`) — confirms no file
  has ever been committed, consistent with zero upload code existing.
* **`storage/README.md` already exists (Phase 1)** and already states
  two of this review's core principles as settled intent: metadata in
  PostgreSQL / bytes on the filesystem, and "stored filenames are
  system-generated identifiers, not user-supplied names — the original
  filename is metadata in the database." It also sketches an
  **illustrative, never-implemented** path convention — see §7 for why
  it needs revising, not discarding.
* `Letter.documents` uses `cascade="all, delete-orphan"` (not
  `passive_deletes`, since SQLAlchemy forbids combining them) — each
  `LetterDocument` is a true owned child of its `Letter`.
  `letter_documents.letter_id` is `ON DELETE CASCADE` at the database
  level too — both only matter if a `Letter` row is ever physically
  removed, which no code path in this project does (Letters archive, they
  don't delete).
* Existing tests (`tests/integration/test_models.py`): one document per
  letter and multiple documents per letter both work at the ORM level
  (`test_letter_multiple_documents`); the `CASCADE` fires correctly on an
  actual physical `Letter` delete (`test_letter_deletion_cascades_documents_and_notifications`
  — exercising a code path the application itself never takes). No
  upload/validation/storage-path-safety test exists anywhere, correctly,
  since none of that code exists yet.

## 2. Document cardinality

**CONFIRMED**: the schema already supports one `Letter` → **many**
`LetterDocument` rows (`letter_id` has no uniqueness constraint) — a
deliberate Phase 2 decision ("a letter may eventually have multiple
attachments; one `storage_path` column on `Letter` would cap every letter
at exactly one document").

**The office confirmed format (PDF/image/text), not cardinality** — this
review does not read that as confirming multiplicity, and does not
invent a multi-document requirement.

**RECOMMENDED: keep the multi-document capability.** It creates no
practical risk, because it is a strict superset of "exactly one
document": a letter with one attachment is simply the `N=1` case of a
`1→N` model. Removing it would require *adding* a new uniqueness
constraint — itself an unconfirmed assumption, and one that would
actively block a legitimate future need (a scanned PDF *and* a separate
typed transcription for the same letter) without any business reason to
do so. No schema change is implied either way — this is a "do nothing"
recommendation.

## 3. Supported file types — existing fields

**CONFIRMED**, no duplicate metadata needed: `mime_type` (free string,
nullable) is the correct machine-readable type indicator for
PDF/image/text (`application/pdf`, `image/jpeg`, `image/png`,
`text/plain`); `document_type` is a *separate*, looser, already-existing
free string the model's own docstring explains is intentionally
unconstrained ("the set of meaningful document types isn't confirmed
yet... an unrecognized value here is harmless") — available for a future
*business* categorization (e.g. "Scanned Copy" vs. "Transcription") that
is orthogonal to the technical MIME type, not a duplicate of it.
`original_filename`, `file_size`, `uploaded_by`, `uploaded_at` all
already exist and need no change. **Missing, and addressed below**: a
checksum field (§12, recommended addition) and a file-extension field
(not recommended — see §7, an extension is derived server-side from the
validated MIME type, never stored as independent, potentially
inconsistent metadata).

## 4. Database vs. filesystem strategy

**CONFIRMED, remains appropriate — no change recommended.** Metadata
(ownership, relationships, the authorization-relevant `letter_id`,
`uploaded_by`) belongs in PostgreSQL; binary/text content belongs on the
filesystem, referenced by a relative `storage_path`. No compelling
requirement exists to store document bytes in PostgreSQL (`BYTEA`/Large
Objects) — doing so would bloat the database, complicate backup/
replication, and buys nothing this design doesn't already get more
simply from a plain file tree. This is the same conclusion Phase 1
reached and Phase 4A re-confirmed; this review re-verifies it against
actual code (not just prior documentation) and finds nothing has changed.

## 5. Storage path safety

**CONFIRMED**: no path is currently constructed by any code — `storage_path`
is an unpopulated column. This section is therefore entirely about the
architecture a *future* implementation must follow, not a bug in
existing code.

**RECOMMENDED**:

* **Resolve `STORAGE_PATH` to an absolute path at application startup**
  (e.g. `Path(settings.STORAGE_PATH).resolve()`), not a relative one
  used as-is at every file operation. A relative path is
  working-directory-dependent — fragile under a process manager or
  container that starts the app from an unexpected directory. This is a
  small, low-risk correctness fix worth making whenever upload code is
  first written, not a change to make now (nothing depends on it yet).
* **Never use client-supplied input to build a filesystem path** — not
  the original filename, not a client-provided extension, not a
  client-provided directory hint. Every path segment must be a
  server-generated identifier (a UUID) or a server-derived value (a
  MIME-type-to-extension mapping the server controls — §7). This is
  already `storage/README.md`'s stated principle; this review confirms
  it and treats it as a hard requirement for any future implementation,
  not optional guidance.
* **Verify the final resolved path stays within the storage root** before
  any file write/read, as defense in depth beyond "we never used
  untrusted input" — cheap insurance against a resolution bug or an
  unexpected symlink (the storage root itself is entirely server-managed
  and should never contain untrusted symlinks in the first place, but a
  containment check costs nothing and catches classes of mistakes the
  "don't trust input" rule alone might not).
* **Collisions are prevented by construction**, not by checking: a
  UUID-named file (the document's own primary key, generated before the
  row is inserted) cannot practically collide with another document's
  file, so there is no need for a "does this filename already exist"
  check.

## 6. Uniqueness

Covered by §5's UUID-based naming — filenames never collide because
they are never derived from anything a user controls, including the
original filename, which is preserved only as metadata (§11).

## 7. File naming strategy — reconciling a real conflict

**A genuine inconsistency exists between two already-written documents,
surfaced by this review, not invented by it.**

`storage/README.md` (Phase 1, "illustrative only — no files exist")
proposes:

```
storage/letters/<department-code>/<year>/<month>/<letter-uuid>.<ext>
```

This groups by department/year/month (good — avoids one flat directory
with years of files, and lets departments' documents be archived or
migrated independently, per that document's own stated rationale) but
ends in `<letter-uuid>.<ext>` with **no document-identifier segment at
all** — structurally assuming exactly one file per letter. That
assumption is now known to conflict with §2's confirmed multi-document
capability: if two documents are attached to the same letter, this
naming scheme has nowhere for the second one to go without colliding
with or overwriting the first.

**RECOMMENDED reconciliation** — combine both documents' correct ideas
rather than discard either:

```
storage/letters/<department-id>/<year>/<month>/<letter-uuid>/<document-uuid>.<ext>
```

Keeps Phase 1's grouping (browsability, independent department
archival/migration) and adds the per-letter subfolder + per-document
filename this review's own cardinality finding (§2) requires. Two
further refinements over Phase 1's illustrative example:

* **`<department-id>` (the department's UUID), not `<department-code>`.**
  `departments.code` remains nullable with an unconfirmed format (a
  standing gap since Phase 2 — see `docs/database/schema.md` §7) — using
  it as a directory name would mean some departments have no path
  segment at all, or an unpredictable one. The UUID is always present
  and always filesystem-safe; a human-readable department name is
  available from the database when needed for display, never used to
  build a path.
* **`<ext>` is a server-derived canonical extension from the *validated*
  MIME type** (§8) — a fixed mapping (`"application/pdf" → "pdf"`,
  `"image/jpeg" → "jpg"`, `"image/png" → "png"`, `"text/plain" → "txt"`),
  never the client-supplied filename's extension taken verbatim.

`storage/README.md` should be updated to this corrected convention once
a future phase actually builds upload — not changed speculatively in
this review, since it is documentation of an architecture, not code, and
this review's job is to identify the correction, not silently apply it
ahead of the implementation phase that will actually exercise it. [Note
— §33: the implementation that followed used a simpler, flatter
convention than this section recommends; `storage/README.md` was
updated to match what was actually built, not this section's
suggestion.]

## 8. Validation strategy

**RECOMMENDED — layered, none of it implemented yet:**

1. **Extension allowlist** — a fast, cheap first filter (`.pdf`, `.jpg`/
   `.jpeg`, `.png`, `.txt`), rejecting obviously-wrong uploads early. Weak
   on its own (trivially spoofed) but useful as an immediate UX signal.
2. **Client-supplied `Content-Type` is never trusted alone** — explicit
   instruction, and correct: a browser or script can claim any
   `Content-Type` regardless of actual content.
3. **Magic-byte / content-signature validation is the authoritative
   check** — inspect the actual file bytes against known signatures
   (`%PDF-` for PDF; `\xFF\xD8\xFF` for JPEG; `\x89PNG\r\n\x1a\n` for
   PNG). Plain text has no reliable magic-byte signature; the practical
   equivalent is confirming the content decodes as valid UTF-8 text
   without binary/control-character content. A Python library such as
   `python-magic` (libmagic bindings) is a reasonable implementation
   choice for a future phase — noted here as an option, not mandated,
   since this review does not write code. [Note — §33: the
   implementation that followed used hand-rolled byte-prefix checks
   instead, deliberately avoiding a native libmagic dependency.]
4. **Size validation** — see §9.

**Explicitly not malware/antivirus scanning** (per instruction) — noted
as **FUTURE work**, with one point made explicit so it is never mistaken
for something this validation already provides: passing magic-byte
validation proves a file *is* a structurally valid PDF/JPEG/PNG/text
file, not that it is *safe* — a byte-valid PDF can still carry a
malicious embedded object. Type validation and malware scanning are
different concerns; this review only recommends the former for V1.

## 9. Size limit — ARCHITECTURAL RECOMMENDATION, not a confirmed requirement

**CONFIRMED**: no upload size limit exists anywhere in this repository
today (no application limit, no reverse-proxy configuration present) —
and the office has not given a number.

**ARCHITECTURAL RECOMMENDATION (not a business fact)**: 10 MB per file
as a starting technical default — generous enough for a multi-page
scanned PDF at a reasonable DPI or a photographed page, while still
bounding worst-case per-request memory/storage impact. This is a
`Settings` value (`app/core/config.py`), trivially changed later; nothing
about this recommendation is meant to imply the organization has agreed
to this specific number.

## 10. Text handling

**CONFIRMED — the model already cleanly supports both readings of
"text" without any redesign, so this is not blocked on new schema:**

* `Letter.text_content` (existing, nullable `Text`) — content typed or
  transcribed directly into the Letter record itself; no file, no
  `LetterDocument` row.
* `LetterDocument` with `mime_type="text/plain"` — an actual uploaded
  `.txt` file, attached the same way a PDF or image would be.

These are not duplicates and not redundant: `text_content` has no
`storage_path`/`original_filename`/uploader at all (it's a plain column
on `Letter`), while a `LetterDocument` always does. Both can coexist for
the same letter (a typed summary plus an attached original file), and
neither is derived from the other.

**PENDING BUSINESS CLARIFICATION** — not the data model (resolved above)
but the **workflow**: when a User records a letter whose source is
"text", is typing it into `text_content`, uploading a `.txt` file, or
either at the User's discretion, the expected behavior? The confirmed
requirement ("text is one of the formats a letter may be provided in")
does not say which. No schema change is blocked on this answer either
way.

## 11. Original filename

**CONFIRMED, already correct, no change needed**: `original_filename` is
already metadata-only — nothing in the current schema or this review's
recommendations ever uses it to construct a storage path (§5/§7).
**RECOMMENDED**: expose it to authorized callers in the future document
metadata response (§24) — genuinely useful for display ("Scan_2026_01.pdf")
even though the on-disk name is a UUID.

## 12. Checksum / integrity — RECOMMENDED, not required

**Not currently present.** Use cases considered: detecting corruption,
identifying duplicate uploads, verifying integrity generally. None of
these is a confirmed business requirement.

**RECOMMENDED (future addition, not built this phase)**: a
`checksum_sha256` column (nullable), computed automatically from the
bytes already being read to write to disk — negligible extra cost, real
defensive value for a government-records system (detecting silent
corruption, or flagging — not blocking — likely-duplicate uploads).
**Explicitly not a uniqueness constraint** — two different, legitimate
letters can share a byte-identical attachment (a form letter circulated
to multiple departments), and enforcing uniqueness would incorrectly
reject a real, valid upload. SHA-256 is the recommended algorithm —
industry-standard, no security requirement here demands anything
stronger, and this is integrity/duplicate-detection, not
password-grade cryptography.

## 13. Replacement policy — PENDING workflow, safe default identified

**Not confirmed by the business.** Four options were weighed:

* Physical replace (destructive) — **rejected**: conflicts directly with
  this project's historical-integrity principle, applied consistently to
  every other entity (Letters, Users, Departments, Categories,
  Classifications all archive/deactivate, never destroy).
* Prevent replacement entirely — safe but potentially impractical (no
  remedy for a genuine mistake, e.g. the wrong scan attached).
* **Retain the old document, add the new one (RECOMMENDED)** — requires
  **no schema change** at all: this is simply "upload another document
  for the same letter," already supported by §2's confirmed multi-
  document capability. The safest option against historical-record loss,
  because nothing is ever removed.
* Mark the old document formally "superseded" — would need a new field
  (e.g. `superseded_by_id` or `is_current`) to distinguish current from
  prior versions in a UI; a reasonable *future* enhancement if the
  business confirms replacement is a distinct first-class workflow from
  "just add another attachment," not adopted here since nothing confirms
  that distinction is wanted.

**PENDING**: whether the *workflow* (as opposed to the *data model*,
already resolved above) should visually distinguish "the current
version" from historical ones. The data model does not need to wait for
this answer.

## 14. Deletion policy — CRITICAL, none recommended for V1

**The core question**: should `LetterDocument` follow the same
never-physically-deleted principle already established for `Letter`
(and every other core entity in this project)?

**Assessment**: yes in principle, but **`LetterDocument` currently has no
lifecycle/status field at all** — unlike `Letter` (`LetterStatus`),
`User` (`UserStatus`), `Department`/`Category`/`Classification`
(`ActiveStatus`), there is nothing on `LetterDocument` today to soft-
delete *into*. Adding one (a status enum, or a simpler
`archived_at`/`is_active`) would be a genuine future schema change, not
something this review is building now.

Weighing storage growth (documents, unlike lightweight metadata rows,
consume real disk space, so an absolute "never delete, ever, no
exceptions" policy has a real long-run cost) against historical
integrity and accidental-deletion protection (the same reasoning that
makes every other entity in this system soft-delete-only):

**RECOMMENDED**: **no document deletion capability of any kind —
physical or soft — in V1.** Not because physical deletion is safe (it
isn't, for the same reasons it's forbidden everywhere else in this
project) and not because soft-delete is unsafe (it would be the right
long-term answer) but because:

1. No confirmed requirement asks for document deletion at all (only
   upload/download/attachment were confirmed).
2. Soft-delete would need a schema change (a status field) not yet
   justified by a confirmed need.
3. Building a delete endpoint now — before its exact behavior (physical
   vs. soft, who's authorized, whether storage is ever actually
   reclaimed) is confirmed — risks exactly the "invent a policy nobody
   asked for" outcome this review process exists to avoid.

If a genuine need for removing a mistakenly-uploaded document arises
before this is revisited, it can be handled by direct, logged
administrative intervention (the same "rare, deliberate operator action"
category as other uncommon cleanup tasks in this project), not a
self-service endpoint.

## 15. Historical identity — already correct

**CONFIRMED, verified directly against the actual migration DDL, not
just the model file**: `letter_documents.uploaded_by` is `FOREIGN KEY
... REFERENCES users(id) ON DELETE RESTRICT` — not `CASCADE`, not `SET
NULL`. `User.documents_uploaded` uses `passive_deletes="all"`, the same
pattern applied to every other `RESTRICT`-backed relationship in this
schema. **No flag, no correction needed** — this already matches
`Letter.recorded_by`'s established, correct pattern exactly, and (since
`User` rows are never physically deleted either — `status` moves to
`DEACTIVATED` instead) the historical uploader identity survives account
deactivation by construction.

## 16. Department isolation

**CONFIRMED**: `LetterDocument` has **no department field of its own at
all** — its only relationship to a department is transitive, via
`LetterDocument.letter_id → Letter.recipient_department_id`. This
already avoids the exact trap this review's own instructions warn
against (deriving ownership from `uploaded_by.department_id`, which
would break the moment a User transfers departments) — there is no such
field to misuse in the first place.

**RECOMMENDED architecture for the future authorization layer**: a
`assert_document_access(user, document)` function that does nothing more
than load `document.letter` and delegate entirely to the existing
`assert_letter_access(user, document.letter)`
(`app/services/authorization.py`, unchanged since Phase 4B/4C). No new
authorization primitive, no duplicated department/classified logic —
the exact "reuse the centralized check, don't re-implement it per
resource" discipline this project has followed since Phase 3B.1.

## 17. Classified document security — CRITICAL

**Follows directly from §16 with no additional mechanism needed.**
Classification lives entirely on `Letter`
(`Letter.classification_id`/`Classification.restricts_access`) — a
`LetterDocument` has no independent classification, visibility, or
existence outside its Letter's authorization. Because the recommended
`assert_document_access` (§16) is a thin wrapper with no logic of its
own beyond delegating to `assert_letter_access`, a classified letter's
restricted visibility extends to every one of its attached documents
automatically, by construction — not by a second, parallel check that
could drift out of sync with the Letter-level rule.

**The authorization chain must always be**: Document → its Letter →
`assert_letter_access` — **never** "Document ID → direct lookup" without
that chain. A future implementation's single most important discipline:
resolve `document.letter` and check access *before* returning anything
about the document at all — including whether it exists. A guessed or
otherwise-inaccessible document id must produce the identical response
to a nonexistent one, the same enumeration-resistant pattern already
established for Letters, Users, and Admins throughout this project.

## 18. Path traversal / IDOR protection

Summarizing §5/§7/§17 as direct answers to each listed threat:

| Threat | Mitigation |
|---|---|
| `../`, absolute paths, Windows-style traversal | Paths built only from server-generated UUIDs — no client string ever appears in a constructed path |
| Crafted filenames | `original_filename` is metadata only, never a path component |
| Document-ID guessing | `assert_document_access` (§16/§17) gates every lookup; inaccessible and nonexistent produce the same response |
| Direct storage URL access | No static route exists or should ever exist (§20) — all retrieval goes through the authenticated API |
| Symlink escape | Storage root is entirely server-managed; a resolved-path containment check (§5) is recommended as defense in depth regardless |

## 19. Retrieval API design

**RECOMMENDED**: `GET /api/v1/letters/{letter_id}/documents/{document_id}`
(nested under the Letter), plus `GET /api/v1/letters/{letter_id}/documents`
for listing a letter's attachments — not a flat `GET
/api/v1/documents/{document_id}`. Nesting under the Letter isn't just a
URL-style preference: it makes the letter-first authorization chain
(§17) the structurally obvious code path, matching how every other
nested resource in this project is authorized through its parent, rather
than relying on discipline alone to remember the check on a flat lookup.

**RECOMMENDED, not implemented**: `Content-Type` on any future download
response must come from the stored, already-validated `mime_type` —
never re-trusted from a client header at retrieval time either.
`Content-Disposition`'s `filename=` parameter should use
`original_filename`, sanitized against header-injection characters
(stray `CR`/`LF`/quotes) before being placed in an HTTP header — a real,
narrow injection surface worth naming explicitly. Since only PDF/image/
text are confirmed formats, HTML/SVG (active-content-capable types)
should simply never be in the accepted-type allowlist (§8) — the
question of "can uploaded content execute in a browser" is closed by not
accepting content that could, not by a separate runtime guard. A
`X-Content-Type-Options: nosniff` response header is a cheap, standard
addition worth recommending for whenever this is built.

## 20. Static file exposure — confirmed clean, must stay that way

**CONFIRMED**: `app/main.py` does not mount `StaticFiles` or any other
public/unauthenticated route over the storage directory — verified by
direct inspection this session, not assumed. **This must remain a hard
constraint on every future phase**: the storage directory is never
reachable except through the authenticated, authorized API endpoint
design in §19. No document, classified or not, may ever be guessable or
reachable by URL alone.

## 21. Storage backend assessment

**CONFIRMED appropriate for V1, no change recommended.** Filesystem
storage suits this project's own standing principle — "designed to run
entirely inside a private government network... does not depend on the
public internet, cloud identity providers, or third-party SaaS" (root
`README.md` §6) — cloud object storage (S3/Azure/GCS) would directly
work against that principle unless the deployment model itself changes,
which nothing in this review suggests. **Not introduced, per explicit
instruction and independent reasoning.**

If a genuine future need arises (e.g. a multi-server deployment
requiring shared storage), the natural refactor point would be a small
storage-backend interface (`write(path, bytes)` / `read(path)` /
`delete(path)`) that the filesystem implementation satisfies today and a
future backend could satisfy identically — **not built now**, since
introducing an abstraction before a second implementation is ever needed
is exactly the premature generalization this project's own conventions
warn against.

## 22. Backup / recovery

**Documented relationship, no automation implemented (per instruction):**
a PostgreSQL-only backup captures every `LetterDocument` row's metadata
— including `storage_path` — but none of the referenced file bytes;
restoring from it alone would leave every document row pointing at a
file that may not exist. A filesystem-only backup has the opposite
problem: files with no metadata linking them to any Letter. **A complete
Letter Registry backup requires both, coordinated** — the database and
the `STORAGE_PATH` tree must be treated as one backup unit, not two
independently-scheduled ones. Given §14's recommendation that documents
are never deleted once created, a filesystem backup that runs slightly
*after* a database backup is safe (it can only be a superset of what the
database references); the reverse ordering is not. This is an
operational requirement for whoever manages a real deployment, not
something this project's codebase implements.

## 23. Failure / transaction strategy

**The core fact this section starts from, stated in the task itself and
correct**: a database transaction cannot roll back a filesystem write.
Perfect atomicity across the two is not achievable without infrastructure
this project has no other need for (e.g. a two-phase-commit protocol) —
the realistic goal is to bias every failure mode toward the *recoverable*
outcome, not to eliminate failure entirely.

**RECOMMENDED ordering**: write the file to its final, fully-resolved
path **first**; only after that write is confirmed complete, insert and
commit the `LetterDocument` row. This ordering is deliberate:

1. **File write fails** → nothing is committed to the database; the
   caller sees a clean upload failure. No orphan, no dangling reference.
2. **File write succeeds, then the database insert/commit fails** → an
   orphaned file exists on disk with no referencing row. This is the
   **acceptable** failure mode (the reverse ordering's failure mode — a
   DB row referencing a file that was never actually written — is worse:
   every future read of that "document" fails unexpectedly, long after
   the original request succeeded from the caller's point of view).
   **RECOMMENDED**: log the orphan clearly (including its path) so a
   future maintenance task could reconcile it; an "orphan file scan"
   (files on disk with no matching row) is a reasonable future tool, not
   built now.
3. **Upload interrupted mid-transfer** → an incomplete file must be
   detected and removed before it could ever be treated as successfully
   written; no `LetterDocument` row is created for an incomplete write.
4. **Duplicate document uploaded** → not a failure at all — an ordinary
   second `LetterDocument` row and a second file, consistent with §12's
   explicit "no uniqueness constraint on checksum."
5. **Storage directory unavailable** — **RECOMMENDED**: checked at
   application startup (verify `STORAGE_PATH` exists and is writable,
   failing loudly if not — the same lazy-check-at-boot convention
   `SECRET_KEY`/`DATABASE_URL` already use) *and* at upload time
   (filesystem errors caught and translated into a clean `5xx` response,
   never a raw stack trace — the same "no PostgreSQL exception ever
   exposed" discipline already applied everywhere else in this codebase).

## 24. Document metadata response — safe fields only

**RECOMMENDED** (future schema, not built): `id`, `original_filename`,
`mime_type`, `file_size`, `uploaded_at`, `uploaded_by`, and `checksum` if
§12 is adopted. **Never**: `storage_path` (the internal filesystem
location — a real information-disclosure risk if leaked, and this
model's direct equivalent of `password_hash` — structurally absent from
the response schema, not merely unselected), absolute paths, server
directory structure. This is the same "the field doesn't exist on the
response shape at all" guarantee `UserPublic`/every response schema in
this project has relied on since Phase 3A.

## 25. Audit implications

**CONFIRMED**: `AuditLog`'s existing polymorphic design
(`entity_type`/`entity_id`, no FK) already accommodates
`entity_type="LetterDocument"` without any schema change — the same
conclusion already reached for every other entity in this project.
**RECOMMENDED future events** (not implemented), extending the single
running list already tracked across `authorization.md`/
`department-management.md`/`admin-management.md`/`user-management.md`/
`letter-registry.md`, not a competing one: `DOCUMENT_UPLOADED`,
`DOCUMENT_VIEWED`/`DOCUMENT_DOWNLOADED` (arguably higher-value than for
most entities — knowing who viewed a classified letter's attachment
matters), `DOCUMENT_REPLACED` (if §13's workflow is later confirmed).

## 26. Notification implications

**Not implemented.** "A document was attached" is a plausible future
notification trigger, extending the single confirmed V1 trigger ("a
letter was registered") — `Notification.letter_id` (already nullable,
already generic) needs no Document-specific field to support this; the
notification would simply reference the Letter, with message text
mentioning the attachment. Documented as future work only.

## 27. Search implications

**Not implemented, not recommended for now.** Phase 4C's Letter search
deliberately covers only Letter's own columns. Searching by attached
filename/MIME type is a plausible future enhancement (e.g. "find the
letter with a file named X") but is not confirmed and would need either
a join or a denormalized field — real complexity for an unconfirmed
need. Documented as future work only, not pursued here.

## 28. Database / migration assessment

**CONFIRMED**: `letter_documents` is unchanged since the Phase 2 baseline
migration, touched exactly once more (the Phase 2 hardening migration,
which added the `uploaded_by` index) — nothing since. **This review
creates no migration** (explicit instruction, and correctly so — nothing
here needs a schema change to be *recommended*). The only schema change
any recommendation in this document implies is the **optional**
`checksum_sha256` column (§12) — a simple, additive, nullable column with
no backfill complexity (every environment's `letter_documents` table is
currently empty, since no upload code has ever run), deferred to
whichever future phase actually implements upload.

## 29. Test plan (design only, not implemented)

Organized by the scenarios this review was asked to plan for; each names
what a future test would verify, not test code:

**File type validation**
1. A well-formed PDF is accepted.
2. A well-formed JPEG/PNG is accepted.
3. A well-formed plain-text file is accepted.
4. An unsupported file type (e.g. `.docx`, `.exe`) is rejected.
5. A file with a spoofed `Content-Type` header claiming `application/pdf`
   but whose actual bytes don't match the PDF signature is rejected —
   the direct proof that magic-byte validation, not the client header,
   is authoritative.
6. A file exceeding the configured size limit is rejected.

**Path / storage safety**
7. A malicious `original_filename` (e.g. containing `../`, an absolute
   path, or Windows-style traversal sequences) never influences the
   actual on-disk storage location — the stored path is always
   server-generated regardless of what filename was supplied.
8. The constructed storage path always resolves within the configured
   storage root.

**Authorization**
9. A User/Admin outside the letter's recipient department cannot access
   its documents (cross-department rejection, mirroring the existing
   Letter-level tests).
10. A classified letter's document is inaccessible to a USER who isn't
    the letter's recorder, exactly matching the letter's own visibility
    rule (§17) — the direct proof the authorization chain is Document →
    Letter → `assert_letter_access`, not a separate, potentially
    drifting check.
11. Document-id enumeration (IDOR): a nonexistent id and an inaccessible
    id produce the identical response.

**Historical integrity**
12. A document's `uploaded_by` remains intact and resolvable after that
    User is deactivated (mirrors the existing Letter/`recorded_by`
    historical-identity tests).
13. Archiving a Letter (`status -> ARCHIVED`) does not delete, hide, or
    otherwise affect its attached documents.

**Failure handling**
14. A simulated filesystem write failure during upload leaves no
    `LetterDocument` row behind (the "file-then-DB" ordering, §23,
    verified: no dangling DB reference to a file that was never
    written).
15. A simulated database failure *after* a successful file write leaves
    an orphaned file, not a corrupted/partial one, and does not raise an
    unhandled exception to the caller.

**Storage exposure**
16. The storage directory is confirmed not reachable via any
    unauthenticated route (a direct regression test against `app.routes`/
    an HTTP probe of a guessed storage path, proving §20's "no
    `StaticFiles` mount" stays true as the codebase grows).

## 30. Pending business clarifications

1. **Text workflow** (§10) — typed `text_content` vs. an uploaded `.txt`
   file vs. either, at the User's discretion. The data model already
   supports all three readings without change.
2. **Replacement workflow** (§13) — whether "replacing" a document
   should visually distinguish a current version from prior ones (a UI/
   workflow question); the safe underlying data model (retain both) is
   already resolved and needs no schema change either way.
3. **Document deletion, if ever needed** (§14) — deliberately left
   entirely unaddressed for V1, not merely deferred in mechanism.
4. **Upload size limit** (§9) — 10 MB is an architectural
   recommendation, not a confirmed organizational limit.

## 31. Recommended Phase 4D (implementation) plan — superseded by §33

**This section is the original, pre-implementation plan, kept for
history — it is no longer current.** Two of its steps (3 and 10) named
the department/year/month-grouped path convention this review's own §7
recommended; the actual implementation followed the brief's simpler,
literal instruction instead. **§33 is authoritative for what storage
convention was actually built:**

```
<STORAGE_PATH>/<letter_uuid>/<document_uuid>.<ext>
```

No department/year/month segment exists anywhere in the implementation.
See §33 and `storage/README.md` for the current, accurate description —
do not follow steps 3 or 10 below as written.

Sequenced so the safest, most foundational pieces come first:

1. Resolve `STORAGE_PATH` to an absolute path at startup; verify
   writability at boot (fail loudly, matching `SECRET_KEY`/`DATABASE_URL`).
2. Implement the layered validation pipeline (§8): extension allowlist →
   magic-byte signature check → size check. No antivirus.
3. ~~Implement server-side path construction (§5/§7):
   `storage/letters/<department-id>/<year>/<month>/<letter-uuid>/<document-uuid>.<ext>`,
   with a resolved-path containment check.~~ **As built (§33)**:
   `<STORAGE_PATH>/<letter_uuid>/<document_uuid>.<ext>` — no
   department/year/month grouping — with the same resolved-path
   containment check, unaffected by which convention sits above it.
4. Implement the file-then-DB-commit ordering (§23), with orphan-file
   logging on the DB-failure branch.
5. Add `assert_document_access` (§16/§17) — a thin delegate to
   `assert_letter_access`, no new authorization logic.
6. Build `POST /api/v1/letters/{letter_id}/documents` (upload),
   `GET /api/v1/letters/{letter_id}/documents` (list metadata),
   `GET /api/v1/letters/{letter_id}/documents/{document_id}` (download/
   view) — no delete endpoint (§14).
7. Add the metadata response schema (§24) — explicitly no `storage_path`
   field.
8. If adopted, the one-column `checksum_sha256` migration (§12/§28) —
   otherwise, no migration is needed at all for the rest of this plan.
9. Tests per §29, prioritizing authorization/classified-access and
   path-safety scenarios first.
10. ~~Update `storage/README.md`'s illustrative path convention to §7's
    corrected form.~~ **As built (§33)**: `storage/README.md` was
    updated to describe the flat `<letter_uuid>/<document_uuid>.<ext>`
    convention actually implemented — not §7's department/year/month
    reconciliation, which was not adopted.

## 32. Explicitly NOT in this phase (review pass — superseded by §33)

At the time of the review, nothing below had been built: upload
endpoint, download endpoint, document deletion endpoint, file validation
code, storage service, static file serving, frontend upload UI, OCR,
antivirus scanning, cloud storage, backup automation, notifications,
automatic audit logging. **§33 records what changed** — upload/download/
listing/validation/storage are now implemented; document deletion,
frontend, OCR, antivirus, cloud storage, backup automation,
notifications, and automatic audit logging remain explicitly out of
scope, unchanged.

## 33. Implementation record (Phase 4D implementation)

Built directly on top of §1-32's recommendations. Every item below is
IMPLEMENTED unless marked otherwise.

* **Storage foundation** — `app/services/document_storage.py`.
  `get_storage_root()` resolves `STORAGE_PATH` to an absolute path fresh
  on every call (never cached at import time — §5) and creates it if
  missing. `build_storage_path()` builds
  `<STORAGE_PATH>/<letter-uuid>/<document-uuid>.<ext>` entirely from
  server-generated UUIDs and a fixed MIME-type-to-extension map, with a
  resolved-path containment check. `write_document_file()` stages to a
  uniquely-named temp file and `os.replace()`s it into place atomically.
  **One deliberate deviation from §7's own recommendation**: the
  implementation brief's own explicit example
  (`storage/<letter_uuid>/<document_uuid>.<safe_extension>`) was
  followed literally — **no department/year/month grouping layer** was
  added on top, even though §7 recommended one for long-term
  browsability at high volume. Following the brief's explicit, literal
  instruction over this document's own earlier recommendation was a
  deliberate choice, not an oversight — see `storage/README.md`, which
  now documents the same thing and explicitly flags the gap between what
  was recommended and what was built.
* **File validation** — `app/services/document_validation.py`. Layered:
  extension allowlist -> size limit
  (`settings.MAX_DOCUMENT_SIZE_BYTES`, default 10 MB, still labeled an
  architectural recommendation, not a confirmed limit, in both
  `config.py` and `.env.example`) -> magic-byte content-signature sniff
  (hand-rolled byte-prefix checks for PDF/JPEG/PNG, UTF-8/control-
  character heuristic for text — **no `python-magic`/libmagic
  dependency added**, a deliberate simplification given the small, fixed
  type set and the friction a native library adds on Windows) ->
  extension/content-type agreement (a `.pdf` upload whose bytes are
  actually a PNG is rejected as mismatched, not silently accepted).
  Client-supplied `Content-Type` is read by FastAPI but never consulted
  by any validation function. Malware/antivirus scanning remains
  explicitly unimplemented.
* **Document upload workflow** — `app/services/document_service.py:upload_document`,
  `POST /api/v1/letters/{letter_id}/documents`
  (`app/api/v1/endpoints/documents.py`). Write-then-commit ordering
  (§23): the file is written to its final path *before* the database
  row is created; a DB failure after a successful write rolls back the
  transaction and deletes the now-orphaned file as compensation (a
  dedicated test simulates this and asserts zero files remain — see
  `tests/integration/test_document_management.py::test_db_failure_cleans_up_finalized_file`);
  a simulated storage failure leaves no database row at all
  (`test_file_write_failure_creates_no_db_record`).
* **Document authorization** — no new authorization primitive.
  `DocumentService._get_letter_for_access` calls the existing
  `LetterService.get_letter`, which already applies
  `assert_letter_access` and collapses "doesn't exist"/"wrong
  department"/"classified and inaccessible" into one
  `LetterNotFoundError` — reused, not duplicated. `assert_document_access`
  (`app/services/authorization.py`) was also added as a thin delegate to
  `assert_letter_access` for any future caller holding an
  already-loaded `LetterDocument`, per the brief's explicit suggestion,
  though the actual upload/list/download code paths reach the same
  result via `LetterService.get_letter` directly.
* **Who can upload** — every document route (`upload`/`list`/`download`)
  uses `get_current_user` only, not `require_user_or_admin` — deliberately
  different from `POST /letters` (which excludes SYSTEM_ADMIN because it
  structurally has no department to record a letter against). A document
  attaches to an *existing* letter, which SYSTEM_ADMIN can already fully
  read/update; excluding it from document upload would have been a new,
  invented restriction the brief's §13 explicitly said not to add
  ("SYSTEM_ADMIN retains system-wide access"). Verified live: a
  SYSTEM_ADMIN uploaded to a letter in a department it does not belong
  to (§ below, "Live verification").
* **Document retrieval** — `GET /api/v1/letters/{letter_id}/documents`
  (metadata list, no `storage_path` field on the response — §24) and
  `GET /api/v1/letters/{letter_id}/documents/{document_id}` (binary
  download via Starlette's `FileResponse`, streamed from disk rather
  than read fully into memory). The retrieval path is followed exactly
  as specified: authenticate -> resolve+authorize the parent Letter via
  `DocumentService.get_document` -> look the document up scoped to
  *both* `document_id` and `letter_id`
  (`LetterDocumentRepository.find_by_id_and_letter`, so a document that
  exists under a different letter 404s identically to one that doesn't
  exist) -> **reconstruct** the storage path from trusted primitives
  (`build_storage_path(letter_id, document_id, document.mime_type)`)
  rather than trusting the stored `storage_path` column as-is -> confirm
  the file exists -> stream it. `Content-Type` is always the
  server-validated `mime_type`; `Content-Disposition`'s filename is
  sanitized against control characters (`_safe_download_filename`)
  before use; every response carries `X-Content-Type-Options: nosniff`.
* **Failure/cleanup handling** — covered above (upload workflow) and in
  the transaction-ordering design (§23, unchanged from the review).
* **No document deletion endpoint** — confirmed absent by design, not
  omission; `grep` for `@router.delete` in `documents.py` returns
  nothing. Uploading again simply adds another `LetterDocument`; nothing
  in this implementation ever removes a prior one (§13/§14/§18/§19,
  unchanged from the review's recommendation — the one recommendation in
  this document implemented exactly as written, with zero deviation).
* **Schema/migration** — **zero schema changes.** `LetterDocument` is
  untouched; `alembic check` against `lrs_dev` reports "No new upgrade
  operations detected" both before and after this phase. The
  review's §12 `checksum_sha256` recommendation was **not** implemented
  — the brief's own §9 explicitly said "Do not add checksum yet."
* **Tests** — `tests/integration/test_document_management.py`, 38 new
  tests: file acceptance (PDF/JPEG/PNG/TXT), file rejection (bad
  extension, HTML, unsupported extension, MIME spoofing, malformed
  PDF/image, oversized, empty), path security (five malicious-filename
  variants, parametrized, plus a direct containment-check test),
  authorization (USER/ADMIN own vs. other department, SYSTEM_ADMIN
  cross-department, classified-letter recorder vs. non-recorder,
  wrong-letter/document pairing, nonexistent letter/document), historical
  integrity (deactivated uploader still represented, letter archive
  doesn't remove documents, a document stays downloadable after its
  letter is archived), storage (UUID-based server-controlled path, no
  `storage_path` in any response, no static route exposes storage,
  correct download headers), and failure handling (DB-failure cleanup,
  write-failure leaves no DB row, a normal upload leaves exactly one
  file, no orphans). Full suite: **425 passed** (387 baseline + 38 new),
  re-run 3 consecutive times, identical results, against a real local
  PostgreSQL 17 test database (`lrs_test`).
* **Live verification against `lrs_dev`** — a running `uvicorn` instance,
  real minted JWTs, real HTTP: upload as the recording USER (`201`,
  content round-tripped byte-for-byte on download); cross-department
  USER upload and download (`404`, both); SYSTEM_ADMIN upload to a
  letter in a department it doesn't belong to (`201` — confirms §13's
  "SYSTEM_ADMIN retains system-wide access"); non-recording USER in the
  *same* department denied a classified letter's documents (`404`); the
  recording USER allowed (`201`); unsupported extension (`422`); MIME
  spoofing — `.pdf` filename, real PNG bytes — rejected (`422`);
  metadata response confirmed free of `storage_path`; nonexistent
  document id (`404`); unauthenticated request (`401`). All test data
  (departments/users/letters/documents, both DB rows and the files they
  wrote under `storage/letters/`) was deleted afterward; `lrs_dev`
  confirmed back to its pre-verification state (3 seeded `categories`
  rows, nothing else).
* **`python-multipart` added as a new dependency** — required by
  FastAPI/Starlette to parse `multipart/form-data` upload requests; no
  code in this repository imports it directly. Pinned in
  `requirements.txt`, installed into the local `.venv`.
