# Operational Activity, Notifications & Audit — Architecture Review & Implementation (Phase 4E)

**Status: IMPLEMENTED (audit generation foundation, notification
generation foundation, and the confirmed "letter registered" trigger).**
§1-30 below are the original architecture review — kept unchanged as the
design rationale. **See §31, "Implementation record"** for what was
actually built on top of it, including the one place a security-relevant
design choice (a database `SAVEPOINT`) was proven against this exact
codebase's own test infrastructure before being written.

This document originally reviewed what already existed for `AuditLog`
and `Notification` (verified fresh against the current repository — not
assumed from any prior phase's report), and designed the
event-generation, transactional, access-control, and retention
architecture a future phase would need to actually populate either
table. That design is now implemented for the events listed in §31;
audit *access* (§9 — a future read API) and several notification
triggers beyond "letter registered" (§12) remain unimplemented exactly as
the review recommended deferring them.

## 0. How to read this document

* **CONFIRMED** — verified directly against current code, migrations,
  or an actual quoted line from an original phase brief (`docs/database/schema.md`,
  `docs/architecture/authorization.md`, etc.), this session.
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts and this project's established conventions. Not implemented.
* **OPTIONAL** — a defensible addition, but not necessary for a working
  V1; adopt only if a real need appears.
* **PENDING** — genuinely open; not guessed into a schema or a policy.

## 1. Current AuditLog architecture (verified fresh)

Read directly this session: `app/models/audit_log.py`, both migrations
touching `audit_logs`, `tests/integration/test_models.py`'s two
`AuditLog` tests, and every prior architecture doc's own audit section
(`authorization.md` §12, `department-management.md` §10,
`admin-management.md` §13, `user-management.md` §12,
`letter-registry.md` §13, `document-management.md` §25) — not assumed
from memory.

**CONFIRMED — schema** (unchanged since the Phase 2 baseline migration;
the Phase 2 hardening migration only confirmed `user_id` was already
indexed, changing nothing):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → `users.id`, **`ON DELETE SET NULL`**, nullable | Nullable for a system-generated action with no human actor — not because a `User` row can be deleted (it can't; see §5) |
| `action` | `varchar(100)`, NOT NULL | Free string — no enum, no fixed vocabulary yet |
| `entity_type` | `varchar(100)`, NOT NULL, indexed | Names which table `entity_id` points into |
| `entity_id` | UUID, nullable, **no FK** | The target table varies per row, so one FK constraint can't cover it |
| `old_values` / `new_values` | JSONB, nullable | Free-form; nothing currently writes to either |
| `created_at` | `timestamptz`, NOT NULL, server-defaulted, indexed | |

**CONFIRMED — indexes**: `user_id`, `entity_type` (single-column, each
supporting "everything by this actor" / "everything of this type"),
`created_at` (time-range queries), plus a composite
`ix_audit_logs_entity_type_entity_id` (supporting "history of this
specific row"). No index on `action` — not yet needed since nothing
queries by it alone.

**CONFIRMED — populated nowhere.** Grepped `app/services/`,
`app/repositories/`, `app/api/`, `app/schemas/`, `app/core/` for
`AuditLog`: zero matches outside `app/models/audit_log.py` itself and
`tests/integration/test_models.py`'s two model-level tests (row
creation, and a nullable-`user_id` system-action row). No service,
endpoint, or repository writes or reads an `AuditLog` row. This matches
the model's own docstring ("No row in this table is ever written by
this phase") and every prior phase's explicit scope boundary.

**CONFIRMED — relationship**: `User.audit_logs` (back-populated,
`passive_deletes="all"`, same pattern as every other `User`-owned
collection in this schema).

## 2. Current Notification architecture (verified fresh)

**CONFIRMED — schema** (unchanged since Phase 2; the hardening migration
added only a database-level `server_default=false()` on `is_read`,
changing no other column):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `recipient_user_id` | UUID, FK → `users.id`, `ON DELETE RESTRICT`, NOT NULL | |
| `letter_id` | UUID, FK → `letters.id`, `ON DELETE CASCADE`, nullable | Nullable "to avoid forcing a schema change the first time a non-letter notification type is needed" (model docstring) |
| `notification_type` | `varchar(100)`, NOT NULL | Free string, same reasoning as `LetterDocument.document_type` |
| `message` | `text`, NOT NULL | |
| `is_read` | `boolean`, NOT NULL, default `false` (both ORM and database-level) | |
| `created_at` | `timestamptz`, NOT NULL, server-defaulted | |
| `read_at` | `timestamptz`, nullable | |

**CONFIRMED — indexes**: composite `ix_notifications_recipient_is_read`
(supporting the one query this table was built for — "this user's
unread notifications"), plus `recipient_user_id` and `letter_id`
individually (FK lookups).

**CONFIRMED — populated nowhere.** Same grep, same result: zero
application code outside `app/models/notification.py` and two
`test_models.py` model-level tests (recipient/letter relationships and
`is_read` default; a CASCADE-on-physical-Letter-delete test exercising a
path the application itself never takes). No notification has ever been
generated by any workflow.

**CONFIRMED (not inferred) — V1's one known trigger.** `docs/database/schema.md`
§2.8, quoting the original Phase 2 brief directly: *"V1's only known
trigger is 'a letter was registered.'"* And: *"No delivery mechanism
(email, push, WebSocket) exists or is assumed. V1 is an in-system
notification center only, per the brief."* These are the only two
notification facts this project has ever actually confirmed with the
business — everything else in this document about notifications is
RECOMMENDED, OPTIONAL, or PENDING, not a re-statement of a settled
requirement.

## 3. AuditLog — additional detail (per the explicit inspection request)

* **Actor relationship**: `AuditLog.user` (back-populated as
  `User.audit_logs`). A single FK, `SET NULL` — see §5 for why.
* **Target representation**: `entity_type` + `entity_id`, no FK — see
  §7.
* **FK behavior on `user_id`**: `SET NULL`, not `RESTRICT`. This is the
  **one FK in this entire schema that behaves differently from every
  other actor-identity FK** (`Letter.recorded_by`, `LetterDocument.uploaded_by`,
  `UserAuthorization.authorized_by` are all `RESTRICT`) — worth
  confirming this is intentional, not an oversight: it is, per the
  model's own docstring, "purely defense in depth, since this schema
  does not otherwise support physically deleting a User" — i.e. `SET NULL`
  never actually fires in normal operation (Users are never physically
  deleted — see §5), so this difference from `RESTRICT` has no observable
  effect today. It matters only if some future, currently-nonexistent
  path ever physically deletes a `User` row; in that hypothetical, `SET NULL`
  would silently anonymize the actor on every audit row they ever
  produced rather than blocking the deletion outright the way `RESTRICT`
  would. See §5 for the recommendation.
* **Is it currently populated anywhere?** No — confirmed by grep, not
  assumption (§1).

## 4. Audit purpose — which actions should eventually be auditable

Evaluated against the existing running lists already scoped across five
prior architecture docs (§1, and see §27 for the consolidation), plus
the categories this task explicitly asked about. **CONFIRMED** here means
the business has actually asked for an accountability trail in general
(the model's own docstring: "Required for a government correspondence
system's accountability trail" — a real, quoted requirement, not
invented); it does **not** mean any specific event below has been
individually confirmed — none has. Every item is RECOMMENDED unless
marked otherwise.

**LETTER** — **no prior doc has ever itemized these**, unlike every
other entity below; `letter-registry.md` §13 only says "automatic audit
logging" generically. This review is the first to actually name them:

| Event | Classification |
|---|---|
| Letter created | RECOMMENDED |
| Letter edited (any field) | RECOMMENDED |
| Letter archived | RECOMMENDED |
| Letter status changed | RECOMMENDED — likely the same event as "archived" in V1, since `ARCHIVED` is currently the only non-`ACTIVE` status; kept distinct here in case a future status value makes them different events |
| Letter classification changed | RECOMMENDED, arguably **higher priority** than a plain edit — this is the one field whose change can alter *who can see the letter at all* (§8's classified-access boundary), making it the single most security-relevant Letter mutation to have a trail for |
| Letter category changed | RECOMMENDED, lower priority — no access-control consequence, purely descriptive |
| Letter recipient department changed | **Does not currently exist as an operation** — no endpoint changes `recipient_department_id` after creation (confirmed: `LetterUpdate` has no such field). Not applicable until/unless that capability is ever added; not a gap in the audit design |

**DOCUMENT** (extends `document-management.md` §25's own list, not a
competing one):

| Event | Classification |
|---|---|
| Document uploaded | RECOMMENDED (`document-management.md` §25 already named this) |
| Document downloaded/viewed | RECOMMENDED — that section already flagged this as arguably higher-value than for most entities, since knowing *who viewed* a classified letter's attachment can matter more than knowing who viewed the letter's metadata |
| Document replaced/added | Already covered by "uploaded" — Phase 4D's implementation made "replace" mean "upload another document" (no distinct replace operation exists), so no separate event is needed unless a future phase adds a real supersede workflow |
| Deletion attempts, since deletion is impossible | OPTIONAL — logging an attempt to call an endpoint that doesn't exist is not meaningful (there is nothing to attempt; a request to a nonexistent route is a `404`/`405` at the framework level, not a business event). If a future phase ever adds a deletion endpoint that then *rejects* a specific attempt (e.g. an authorization failure on a delete call), logging *that* rejection would be reasonable then — not before there's an endpoint to reject anything from |

**USER**:

| Event | Classification |
|---|---|
| Authorized (`UserAuthorization` created) | RECOMMENDED — already named `USER_AUTHORIZATION_CREATED` in `user-management.md` §12 |
| Signup | RECOMMENDED, **not previously named** — every prior list covers *approval*, not the signup event itself. Worth adding: it's the moment a `PENDING_APPROVAL` account is actually created, a distinct fact from the Admin later authorizing the email |
| Approved | RECOMMENDED — `USER_APPROVED` (`user-management.md` §12) |
| Deactivated | RECOMMENDED — `USER_DEACTIVATED` (same) |
| Reactivated | RECOMMENDED — `USER_REACTIVATED` (same) |
| Department changed | **Does not currently exist as an operation** for a `USER`-role account — no endpoint transfers a User between departments (only Admin department-transfer exists, `admin-management.md` §9). Not applicable until/unless added |

**ADMIN** (already fully itemized in `admin-management.md` §13 — this
review does not re-derive it, only confirms it's still accurate):

`ADMIN_AUTHORIZATION_CREATED`, `ADMIN_APPROVED`, `ADMIN_DEACTIVATED`,
`ADMIN_REACTIVATED`, `ADMIN_DEPARTMENT_CHANGED` — all RECOMMENDED,
unchanged.

**DEPARTMENT** (already fully itemized in `department-management.md`
§10 — confirmed still accurate): `DEPARTMENT_CREATED`,
`DEPARTMENT_UPDATED`, `DEPARTMENT_ACTIVATED`, `DEPARTMENT_DEACTIVATED` —
all RECOMMENDED, unchanged.

**AUTHORIZATION** (the `UserAuthorization` table, spanning both
purposes):

| Event | Classification |
|---|---|
| Issued | RECOMMENDED — covered by `USER_AUTHORIZATION_CREATED`/`ADMIN_AUTHORIZATION_CREATED` above; not a separate concept |
| Used (consumed by signup) | RECOMMENDED, **not previously named** — distinct from "issued": the authorization's `status` moves `ACTIVE → USED` at signup, a fact worth its own trail entry, especially since this is also the project's one genuinely race-sensitive write (`SELECT ... FOR UPDATE`) |
| Revoked | RECOMMENDED — `USER_AUTHORIZATION_REVOKED` (`user-management.md` §12); no ADMIN-purpose equivalent exists yet since no ADMIN-purpose revoke endpoint exists (a pre-existing, unrelated gap — see `user-management.md` §12's "Known limitations") |
| Expired | **Not applicable — `expires_at` is a real column, but nothing currently enforces it.** Grepped `app/services/`: no code path checks `UserAuthorization.expires_at` against the current time anywhere. An "expired" audit event would log a state transition that no code currently causes to happen. PENDING BUSINESS CLARIFICATION, not something this review can classify as RECOMMENDED — it depends on whether expiry enforcement is ever actually built, which is itself unconfirmed |

**CATEGORY / CLASSIFICATION** (Phase 4B) — genuinely missing from every
prior list; not mentioned in `letter-registry.md` §13 or anywhere else:
`CATEGORY_CREATED`/`UPDATED`/`ACTIVATED`/`DEACTIVATED` and the
`CLASSIFICATION_*` equivalents (including `restricts_access` toggling,
arguably the single most security-relevant Category/Classification
mutation, analogous to Letter classification changes above) — all
RECOMMENDED, newly identified by this review.

## 5. Audit immutability — CRITICAL

**RECOMMENDED: `AuditLog` should be append-only — insert-only, with no
application-level update or delete capability, ever.** This is not a
guess: it is the same principle this project has applied to every other
entity from Phase 2 onward (Department/User/Category/Classification
deactivate rather than delete; Letter archives rather than deletes;
Phase 4D's own review concluded `LetterDocument` should have **no**
deletion endpoint of any kind). An audit log that could be edited or
removed by any application user would defeat the entire purpose the
model's own docstring states it exists for — "an accountability trail."
No role, including `SYSTEM_ADMIN`, should have an API path that updates
or deletes an `AuditLog` row. (Direct database access for a genuine
data-correction emergency is a separate, already-established category of
action in this project — the same category "clean up a mistakenly
uploaded document" fell into in `document-management.md` §14 — not
something this review is designing an API for.)

**The `user_id` FK question, revisited.** §3 already noted `SET NULL` is
the one actor-identity FK in this schema that isn't `RESTRICT`, and that
the difference is currently inert (Users are never physically deleted).
**RECOMMENDED**: if this schema is ever revisited, change
`audit_logs.user_id` to `ON DELETE RESTRICT`, matching
`Letter.recorded_by`/`LetterDocument.uploaded_by`/`UserAuthorization.authorized_by` —
for the identical reason those three already use `RESTRICT`: historical
actor identity should be protected from vanishing at all, not just
protected by an assumption that the deleting code path never gets built.
`SET NULL` is defensible only for a genuinely actor-less system action
(a future scheduled job, explicitly already anticipated by the model's
own docstring) — which is a real, distinct case from "the user who
performed this action was later removed." **Not urgent** (nothing
currently exercises the difference) and **not a schema change this
review is proposing be made now** — a note for whenever `audit_logs` is
next touched, not a standalone migration.

## 6. Audit actor vs. resource owner

Kept deliberately distinct, per the task's own example:

* **Actor** — the authenticated caller who performed the action.
  `AuditLog.user_id` already represents exactly this and only this.
* **Resource owner** — the user/department the *affected* entity
  belongs to. This is **not** a field on `AuditLog` at all today, and
  doesn't need to be a stored column: it's derivable by joining
  `entity_type`/`entity_id` back to the actual entity's own department
  field (`Letter.recipient_department_id`, `User.department_id`, etc.)
  at query time.

Worked example matching the task's own: **Admin approves User** →
`AuditLog.user_id` = the Admin (actor); `entity_type="User"`,
`entity_id=<the approved User's id>` (the affected resource, whose
"owner" — its own department — is derivable by joining back to that
`User` row, not stored redundantly on the audit row itself). This is the
same actor/resource distinction Phase 3B.4 already established at the
service layer (`UserService.approve_user`'s caller is the Admin; the
User being approved is a different row entirely) — `AuditLog`'s existing
two-field shape (`user_id` for actor, `entity_type`/`entity_id` for
target) already supports this without any change.

## 7. Audit target strategy

**CONFIRMED, already exists, adequate for V1**: `entity_type` (free
string) + `entity_id` (nullable UUID, no FK). Evaluated against the
task's three named alternatives:

* **Separate audit tables per entity** (e.g. `letter_audit_logs`,
  `user_audit_logs`) — rejected: duplicates the same five columns N
  times, makes "everything this actor did, across every entity type" a
  UNION query instead of one table scan, and buys nothing the current
  design doesn't already provide. Clear overengineering for this
  project's scale.
* **Explicit nullable FK per entity type on one wide table** (a
  `letter_id`, `user_id`-as-target, `department_id`, ... column each,
  all nullable) — rejected: a sparse wide table that grows a new nullable
  column every time a new auditable entity type appears, worse than the
  string-keyed design it would replace.
* **`entity_type` + `entity_id`, no FK (current)** — **RECOMMENDED to
  keep as-is.** This is the conventional, minimal shape for an audit log
  specifically (not a general-purpose polymorphic-relationship pattern
  applied indiscriminately) — audit rows are expected to outlive an
  individual referenced row's practical relevance, and the lack of a
  literal FK constraint is the *correct* trade-off here, not a gap:
  nothing in this schema physically deletes rows this table would
  reference anyway (see §5), so the "dangling reference" risk a strict
  FK would guard against essentially doesn't exist in practice.

**Coverage check against all eight named entities** — `Letter`,
`LetterDocument`, `Department`, `Category`, `Classification`,
`UserAuthorization` each map to a real table, so `entity_type` would
literally be that table's model name. **`User` and `Admin` require one
clarification, not a schema change**: an Admin account *is* a `User` row
(`role=ADMIN`) — there is no separate `Admin` table (established since
Phase 3B.3). **RECOMMENDED**: Admin-related audit events should use
`entity_type="User"` (the real table), with the *action* string carrying
the Admin-specific semantic (`ADMIN_APPROVED` vs. `USER_APPROVED`,
already how `admin-management.md` §13 and `user-management.md` §12
independently named their events) — never an invented `entity_type="Admin"`
that doesn't correspond to any real table. This avoids a confusing,
fictitious entity type without needing any design change.

## 8. Change detail strategy

**RECOMMENDED — targeted before/after pairs, not full row snapshots.**
`old_values`/`new_values` (JSONB, already exist) should hold only the
fields that actually changed for that specific event type — the task's
own examples are exactly right: a department change logs
`{"old_department_id": ..., "new_department_id": ...}`, a classification
change logs `{"old_classification_id": ..., "new_classification_id": ...}`.
**Explicitly rejected: a generic "serialize the whole row" JSON blob on
every event.** Three reasons: (1) it would silently capture whatever
columns happen to exist on a model at write time, coupling audit-log
shape to schema evolution in a way nothing forces anyone to notice; (2) a
full snapshot risks capturing something that shouldn't be duplicated
into `old_values`/`new_values` at all (see §10 — a Letter's `text_content`
or a classified subject line, for instance) when the actual auditable
*fact* is almost always a handful of specific fields, not the entire row;
(3) it isn't what any of the events named in §4 actually need — none of
them requires reconstructing an entire historical row, only "what
changed."

**No `reason` field is recommended for V1.** The task lists it as a
candidate; nothing in this project's confirmed requirements asks a caller
to supply a free-text justification for a state change (Letter archival,
User deactivation, etc. all currently require none), and inventing a
mandatory-or-optional reason field would be adding a workflow requirement
the business hasn't asked for. If a future phase confirms a specific
action needs a reason (e.g. "deactivating a User requires a note"), that
becomes a field on *that action's own request schema*, which then
naturally flows into `new_values` — not a standalone `AuditLog.reason`
column added speculatively now.

**Metadata**: `action`, `created_at` (timestamp), `user_id` (actor),
`entity_type`/`entity_id` (target) all already exist and need nothing
added. No separate `metadata` JSONB column is recommended beyond
`old_values`/`new_values` — a second free-form JSON field with no defined
purpose is exactly the kind of "invent a generic blob" this section was
asked to avoid.

## 9. Audit access control — PENDING, safe default recommended

**Who may view audit records is a genuine, unanswered business
question** — this review does not guess it. A real complication worth
surfacing rather than hand-waving: because `AuditLog`'s target is
polymorphic (§7), "does this audit entry belong to my department" isn't
a single column to filter on — it requires resolving the department
*through* whichever entity `entity_type`/`entity_id` points at (a
`Letter`'s via `recipient_department_id`, a `User`'s via its own
`department_id`, a `Department`'s *is* one, and so on) — a genuinely more
involved per-entity-type join than any authorization check this project
has built so far.

**RECOMMENDED safe V1 default, given that complexity**: **`SYSTEM_ADMIN`
only**, for whenever an audit-viewing API is actually built. Not
"`ADMIN` scoped to their own department" — that requires the
per-entity-type department-resolution logic above to be built correctly
*before* it can be trusted not to leak cross-department entries, and
getting that wrong is a real data-leakage risk (§10), not a cosmetic one.
Starting at the narrowest, structurally-safe option (mirroring how every
other System-Admin-only management surface in this project already
works — Departments, Admins, Categories, Classifications) and widening it
later, once the per-entity department-resolution logic is deliberately
designed and tested, is the safer direction to iterate in than the
reverse. **A plain `USER` should never see any audit record in V1** —
nothing about "their own actions" has been requested, and an audit trail
is inherently about oversight *of* users, not a feature *for* them.

## 10. Audit data leakage

**CRITICAL, and directly connects to §8's "no full snapshot" rule.**
Audit entries can absolutely leak exactly the categories the task names,
if `old_values`/`new_values` are populated carelessly:

* **Classified Letter information** — if a classification-change event's
  `old_values`/`new_values` ever included the Letter's `subject` or
  `text_content` (rather than only the classification id, per §8), a
  `SYSTEM_ADMIN`-only audit view would still be seeing content a
  classified letter's own visibility rule (`assert_letter_access`) exists
  to restrict from other roles — not a leak *from* `SYSTEM_ADMIN` (which
  already bypasses that rule for the Letter itself), but a reason the
  §8 "targeted fields only" discipline matters even for entities that
  themselves carry access restrictions.
* **Document filenames** — `original_filename` is exactly the kind of
  field a `DOCUMENT_UPLOADED` audit event's `new_values` would naturally
  want to include; that's fine for an audit record (it's already
  server-side metadata, not secret), but the *audit viewer* must still be
  authorized to know the Letter exists at all first (see below) — the
  filename alone reveals that some letter received an attachment.
* **User emails / department information** — similarly fine to log (they
  aren't secrets, they're already visible to the relevant Admin), but
  again gated by who may view the audit trail at all (§9).

**The correct relationship, stated explicitly per the task's own
framing:**

```
Audit visibility
    ↓
resource authorization
```

**RECOMMENDED**: an audit-viewing capability must never become a second,
independent way to learn about a resource a caller couldn't otherwise
access through that resource's own endpoint. Concretely: if a future
`SYSTEM_ADMIN`-only audit API is built (§9's recommended default),
`SYSTEM_ADMIN` already bypasses every resource-level authorization check
in this system (`assert_letter_access`, `assert_department_access`), so
this constraint is automatically satisfied *for that specific role* by
construction — there is no case where `SYSTEM_ADMIN` could see an audit
entry about a Letter it couldn't otherwise open. **The constraint becomes
load-bearing the moment audit access is ever widened past `SYSTEM_ADMIN`**
(e.g. a future "`ADMIN` sees their department's audit entries" feature) —
at that point, every audit row touching a classified Letter must be
filtered by the *same* `assert_letter_access`/`letter_visibility_filter`
rule the Letter itself uses, not a separately-invented "can this Admin
see this audit row" rule that could drift out of sync with actual Letter
visibility. This mirrors exactly the discipline `document-management.md`
§17 established for document authorization (delegate to
`assert_letter_access`, never duplicate it) — the same seam, reused for
a third consumer.

## 11. Audit retention

**No retention period has been confirmed — correctly left PENDING, not
guessed.** `docs/PROJECT_STATUS.md`'s "Pending Confirmation from S&IT"
list already tracks a related open item (document retention); audit
retention is a distinct, equally unconfirmed question.

**RECOMMENDED technical strategy, independent of what period is
eventually chosen**: `created_at` is already indexed, so a future
time-bounded retention policy (delete/archive rows older than N) is
straightforward to implement later *as a scheduled operational task*, not
something the schema needs to anticipate now. **RECOMMENDED**: whatever
the eventual period, prefer **archiving audit rows to cold storage over
physically deleting them outright** — deleting rows from an
accountability trail is in tension with the very reason it exists (§5),
so if space/performance ever forces a retention decision, moving old
rows out of the hot table (e.g. to a yearly export, or a partitioned
older table) preserves the record while bounding the live table's size,
rather than destroying history. **Not recommended now**: table
partitioning, a dedicated archival job, or any other retention
infrastructure — none of this is justified before the retention *period*
itself is even known, and building it speculatively would be exactly the
kind of premature infrastructure this project's conventions warn
against.

## 12. Notification purpose

Evaluated against the task's candidate list. **CONFIRMED** is reserved
for the one trigger the original brief actually named (§2); every other
candidate is RECOMMENDED/OPTIONAL/PENDING, not a re-statement of settled
scope.

| Candidate | Classification |
|---|---|
| Letter assigned/received (registered) | **CONFIRMED** — the brief's own stated V1 trigger (§2) |
| New letter registered | Same event as above — "assigned/received" and "registered" describe the identical fact for V1, where a Letter is always created directly into its recipient department with no separate assignment step |
| Letter updated | RECOMMENDED, lower priority — informational, no access-control weight |
| Document added | RECOMMENDED — a natural extension once Phase 4D's upload endpoint exists (it now does); mirrors "letter registered" |
| User approved | RECOMMENDED — the approved User themselves is a natural, obvious recipient ("your account is now active") |
| User rejected | **Does not currently exist as a distinct outcome.** There is no "reject" action anywhere in this system — a `UserAuthorization` is either approved, left `PENDING_APPROVAL` indefinitely, or revoked (`user-management.md` §9); revocation is the closest existing concept, and it happens *before* signup, when there is no `User` row yet to notify at all (the authorization record has an email, not an account). PENDING — not applicable until/unless a real rejection concept is added |
| Account deactivated/reactivated | RECOMMENDED — same reasoning as "approved," directly informs the affected account holder |
| Department deactivated | OPTIONAL — informs that department's Users their access is currently blocked; useful, but the effect (a `403` on their next department-scoped action) is already self-evident without a notification |
| Authorization issued | OPTIONAL — the *authorized email* has no `User` account yet to notify in-system (no account = nowhere in this system to receive an in-system notification); this would require out-of-band delivery (email), which §2 already confirms is explicitly **not** part of V1's scope ("in-system notification center only") |
| Authorization revoked | Same limitation as above — OPTIONAL at best, and only meaningfully deliverable to whoever *created* the authorization (the authorizing Admin), not the candidate email, which still has no account |

## 13. Notification recipients — PENDING BUSINESS CLARIFICATION

**The department-ownership trap, addressed directly per the task's own
warning**: recipient selection must **never** derive from any
user-attached `department_id` snapshotted at some other time — not
`uploaded_by.department_id` (a `LetterDocument` concept, not even
relevant to Letter notifications), and not a recipient's own
`department_id` cached anywhere. The only correct source of "which
department does this Letter belong to" remains
`Letter.recipient_department_id` — the exact same field
`assert_letter_access`/`assert_department_access` already treat as
authoritative. Recipient selection is a *query at generation time*
("who is currently in `recipient_department_id`"), never a value copied
onto the `Notification` row itself.

**Candidate recipient groups, none confirmed**:

* All Users in the recipient department
* The recipient department's Admins only
* One specific assigned User (implies an "assignment" concept that
  doesn't exist yet — no field on `Letter` designates a specific
  responsible User beyond `recorded_by`)
* `SYSTEM_ADMIN`
* The acting user only (a receipt-style "you did this" notification,
  distinct from notifying *others*)

**What genuinely needs business confirmation**: whether "a letter was
registered" should notify the *whole* recipient department, just its
Admins, or nobody but the recorder (a receipt). **RECOMMENDED interim
default, explicitly flagged as a guess, not a confirmed answer**: the
recipient department's `ADMIN`s — this mirrors the one clear precedent
already established elsewhere in this system (an Admin manages/oversees
their own department's Users and, as of Phase 4B, has the same Letter
access as any User in that department), so "the department's Admins learn
when new correspondence arrives for their department" is at least
consistent with an existing role responsibility, not an arbitrary guess
from nothing. **Still PENDING** until confirmed.

## 14. Notification security

**CRITICAL — the most important finding in this half of the review.**
`Notification.message` is a free `text` field, populated whenever a
notification is generated, with no defined content constraint today
(nothing populates it yet — see §2). This creates a real risk **if** a
future implementation embeds Letter content directly into that text
(e.g. `f"New letter '{letter.subject}' registered"`):

* **Should a notification be generated for a user who cannot access the
  Letter?** **RECOMMENDED: no** — generation should apply the same
  visibility rule the Letter itself uses (`assert_letter_access`/
  `letter_visibility_filter`) *before* deciding who receives one, not
  generate broadly and rely on read-time filtering. This matters
  specifically for a classified Letter: if §13's "notify the department's
  Admins" default is adopted, that's already consistent (Admins are never
  narrowed by the classified-access boundary — `letter-registry.md` §8),
  but if recipient selection is ever widened to "all Users in the
  department," a classified Letter's notification must **not** go to a
  User who wouldn't be allowed to open that Letter — otherwise the
  notification itself becomes the leak, regardless of what its `message`
  text says.
* **Should notification visibility re-check Letter authorization at read
  time, or is generation-time filtering enough?** **RECOMMENDED: both,
  for different reasons.** Generation-time filtering (above) decides *who
  gets one at all* — necessary but not sufficient, because of the next
  point.
* **What happens if classification changes *after* notification
  creation?** This is the scenario that makes read-time re-checking
  necessary even with correct generation-time filtering: a Letter
  notified to the whole department while unclassified, then later marked
  `restricts_access=True`, leaves existing `Notification` rows already
  sitting in front of Users who should no longer be able to see that
  Letter. **RECOMMENDED**: whenever a notification is *displayed* in a
  way that exposes more than its already-stored `message` text (e.g. a
  future UI that lets a user click through to the Letter, or an API that
  joins to live Letter fields for richer display), that access must
  re-check `assert_letter_access` fresh at read time — never trust that
  passing generation-time filtering once is still true later. This is the
  same "authorization must be re-evaluated fresh, never cached or
  snapshotted" principle Phase 4D already established for documents
  (`document-management.md` §17), applied here for the first time to
  notifications. **The one thing re-checking at read time *cannot* undo**:
  if `message` itself already contains sensitive content baked in at
  generation time (the subject-line-embedding scenario above), a later
  classification change cannot retroactively scrub already-stored text.
  **RECOMMENDED, to close this specific gap**: keep `message` generic and
  non-sensitive by construction (e.g. "A new letter has been registered in
  your department" — the exact example already used in this project's
  own model-level test, `test_notification_user_and_letter`) rather than
  interpolating `subject`/`sender_name`/any Letter field into the stored
  text. Any richer, letter-specific display should be composed at *read
  time* by joining to the live Letter through the same authorization
  check — never persisted into `message` up front.
* **What happens if the recipient is deactivated?** No special handling
  is needed, and none should be invented: `Notification.recipient_user_id`
  is `RESTRICT` (the row is never orphaned), and a deactivated recipient
  simply cannot authenticate at all (`get_current_user`, Phase 3A) —
  their notifications sit unreachable until/unless they're reactivated,
  exactly the same shape as every other user-owned row in this system.
  **OPTIONAL**: skipping generation for an already-deactivated recipient
  is a defensible micro-optimization, not a correctness requirement — a
  notification for a deactivated user is inert, not harmful.

## 15. Notification lifecycle

**CONFIRMED — the state machine already exists**: `created` (row
inserted, `is_read=false`) → `read` (`is_read=true`, `read_at` set). No
other state exists on the model today (no "archived," no "dismissed").

**RECOMMENDED**: keep the lifecycle exactly this simple for V1 — two
states, one boolean, one timestamp — since nothing in the confirmed
scope (§2) asks for more, and the schema already supports exactly this
much and no more.

**Retention** — PENDING, same reasoning as audit retention (§11): no
business-confirmed period exists for how long a read (or unread)
notification should be kept. **RECOMMENDED technical note**: unlike
`AuditLog` (§5, must never be deleted), a `Notification` is explicitly
**not** an accountability record — it's informational, disposable, and
this project's own model docstring already frames it as such. There is
therefore no principled objection to eventually deleting old, read
notifications (unlike audit rows) — but no specific period is
recommended here, since none is confirmed, and building a cleanup job
before a period is known would be speculative.

## 16. Notification API — evaluated, not implemented

The task's four candidate routes fit the existing architecture cleanly,
with no new pattern required:

```
GET   /api/v1/notifications                    (own notifications, paginated — same envelope shape as every list endpoint since Phase 3B.2)
GET   /api/v1/notifications/unread-count        (a lightweight, high-frequency-pollable count — see §18)
PATCH /api/v1/notifications/{id}/read           (mark one's own notification read)
PATCH /api/v1/notifications/read-all            (mark all of the caller's own notifications read)
```

**RECOMMENDED shape, matching existing conventions exactly**:
`GET /api/v1/notifications` is *always* implicitly scoped to
`current_user` — there is no `recipient_user_id` query parameter for any
role, not even `SYSTEM_ADMIN` (unlike `GET /api/v1/letters`'s
`department_id` parameter, which is meaningful for `SYSTEM_ADMIN`
specifically) — because a notification's entire purpose is "what this
specific caller needs to know," not a resource any role has a legitimate
reason to browse on someone else's behalf (see §18). No endpoint here
would need a new dependency, a new router pattern, or a new response
envelope shape — `NotificationRepository`/`NotificationService`/
`notifications.py` would follow the exact four-layer structure every
resource since Phase 3A has used.

## 17. Notification access

**RECOMMENDED, matching the task's explicit constraints**:

* A User must never read another user's notifications —
  `WHERE recipient_user_id = current_user.id` unconditionally, on every
  notification query, for every role including `SYSTEM_ADMIN`. This is
  **not** a department-isolation rule (`assert_department_access` doesn't
  apply here at all) — it's a strictly per-account boundary, closer in
  shape to "an Admin cannot revoke another Admin's `UserAuthorization`"
  (`user-management.md` §9) than to any Letter-style department check.
* A User must never mark another user's notification read — same
  `recipient_user_id = current_user.id` scoping on the
  `PATCH .../{id}/read` endpoint; a mismatched id should 404 (not 403),
  the same enumeration-resistant shape `LetterNotFoundError`/
  `DocumentNotFoundError` already established — a nonexistent
  notification id and someone else's real one must be indistinguishable.
* A User must never infer an inaccessible Letter's existence through a
  notification — covered by §14's generation-time-filtering and
  read-time-re-check recommendations; not a new rule, the same one
  restated in access-control terms.

**No new authorization primitive is needed** — a straight equality
filter on the row already owned by the caller is simpler than even
`assert_department_access`, let alone `assert_letter_access`; this is the
one place in the whole review where "reuse the existing chain" doesn't
apply, because there's a simpler, correct rule available (ownership, not
department/classification).

## 18. Real-time vs. polled

**CONFIRMED, not a green-field decision**: §2's quoted brief language —
"V1 is an in-system notification center only... no delivery mechanism
(email, push, WebSocket) exists or is assumed" — already rules out
WebSockets/Server-Sent Events as anything other than a future
possibility, not a V1 requirement. **RECOMMENDED**: **polling** (the
client calls `GET /api/v1/notifications/unread-count` on an interval, or
simply on page load/navigation — a frontend decision, not a backend one)
or **manual refresh** — either is trivially served by the plain REST
endpoints in §16, with zero new infrastructure. **Not recommended for
V1**: WebSockets, SSE, or any persistent-connection mechanism — no
requirement has ever asked for sub-second delivery, and introducing one
would be new infrastructure (connection management, a pub/sub layer to
actually push events) this project has never needed before, for a
feature whose only confirmed trigger (§2) is "a letter was registered,"
not a high-frequency event stream.

## 19. Event generation architecture

Evaluated against the existing, unbroken layering
(`endpoint → service → repository`) every resource since Phase 3A has
used:

* **A. Endpoint-level** — rejected. Endpoints in this project are
  deliberately thin (`app/api/v1/endpoints/*.py` translate service
  exceptions to HTTP and nothing else — stated explicitly in
  `backend/README.md`'s layering rules: "Endpoints call services.
  Endpoints do not build queries," and by extension, don't contain
  business logic). Adding audit/notification writes at this layer would
  both violate that discipline and risk being silently skipped by any
  future second caller of the same service method that doesn't go
  through this specific endpoint.
* **B. Service-level — RECOMMENDED.** This is where every transaction
  boundary in this codebase already lives (`session.commit()` is called
  from services, never repositories or endpoints, throughout
  `letter_service.py`/`user_service.py`/`admin_service.py`/etc.).
  Recording an audit event and queuing a notification write are, at
  bottom, more writes in the *same* transaction as the operation that
  triggered them — a service method is exactly where "this operation
  succeeded, now do the side effects that go with it" already belongs by
  this project's own established shape. No new architectural layer is
  needed.
* **C. SQLAlchemy event listeners (`after_insert`/`after_update` hooks)**
  — rejected. This project has consistently kept database-level
  invariants (CHECK constraints, FKs) separate from business logic
  (services) rather than blurring the two — see `app/models/user.py`'s
  own docstring distinguishing what a CHECK constraint can and can't
  express. ORM event listeners would fire for *any* write through that
  model, including test-factory setup (`tests/factories.py` creates rows
  directly via the ORM, not through services) — meaning listener-based
  audit/notification generation would either fire during test setup
  (polluting every test with synthetic audit/notification rows) or need
  its own mechanism to distinguish "real" application writes from
  internal ones, which is exactly the kind of fragile, hidden-side-effect
  design this project's conventions have avoided everywhere else.
* **D. Domain events (an event bus/dispatcher pattern)** — rejected for
  V1 as premature. This project's stated philosophy (root `README.md`
  §6: "prefer the simplest architecture that satisfies confirmed
  requirements") argues directly against introducing a publish/subscribe
  layer before the actual number and shape of audit/notification events
  is even confirmed — at V1's scale (a low double-digit count of event
  types across the whole system, per §4/§12), direct service-level calls
  are simpler, more traceable (a reader of `LetterService.create_letter`
  can see exactly what happens, not follow an indirection to find
  subscribed handlers), and don't foreclose introducing a real event
  bus later if the number of side effects ever grows large enough to
  justify one.
* **E. Background task** — this is a *timing* question, not a
  *generation-location* question; see §21/§22 for where it actually
  applies (notification delivery timing, never audit, which must stay
  synchronous and transactional per §21).

**RECOMMENDED**: audit and notification writes both originate from
explicit, readable service-layer calls, in the same session as the
operation they record — e.g. `LetterService.create_letter` would call
something like `self._record_audit_event(...)` and (subject to §21's
savepoint design) a notification-write helper, inside its own existing
`session.commit()` boundary — not a new pattern layered on top of the
one this project already has.

## 20. Transactional consistency — CRITICAL

The task's three failure scenarios, addressed directly, plus the
underlying design decision they all depend on:

**Should audit failure fail the entire operation? RECOMMENDED: yes.**
`AuditLog`'s own docstring states its purpose as an accountability trail
for a government correspondence system's official records. Silently
allowing a real operation (a Letter created, a User approved) to succeed
*without* a corresponding audit row — because the audit write happened to
fail for some unrelated reason — directly undermines that stated purpose;
an accountability trail with silent gaps is not one. **RECOMMENDED
implementation**: the audit `INSERT` happens in the **same transaction**
as the business operation, using the **same session**, with **no**
independent exception-swallowing around it — if it fails, the whole
`session.commit()` fails, and the caller sees the operation itself fail.
This is the conservative, safe-default answer consistent with this
project's pattern of choosing the stricter interpretation whenever a
requirement is ambiguous (archiving not deleting; no
reference-number-uniqueness guess; Phase 4D's "no deletion endpoint"
default).

**Should notification failure fail the operation? RECOMMENDED: no.**
Notifications are informational, not a legal record — nothing in this
system treats "the department Admin was told about this letter" as part
of the letter's official existence. **RECOMMENDED**: notifications are
best-effort; a notification-write failure must never roll back the
underlying business operation (or its audit row).

**The genuine technical subtlety this creates, worked through
precisely**: if the notification write happens in the *same* session as
the (mandatory, must-not-fail-silently) audit write and business
operation, a naive "just wrap it in try/except and swallow" is **not
sufficient** — PostgreSQL aborts an entire transaction at the database
level the moment any statement inside it fails ("current transaction is
aborted, commands ignored until end of transaction block"), so catching
the Python exception from a failed notification `INSERT` does **not**
leave the session usable for the subsequent `commit()` of the audit row
and business operation; the whole transaction would already be dead.
**RECOMMENDED**: wrap the notification write in its own `SAVEPOINT`
(SQLAlchemy's `session.begin_nested()`) — if it fails, roll back to that
savepoint only, leaving the outer transaction (business operation + audit
row) fully intact for a normal commit. **This is not a novel pattern
introduced for this decision** — this exact mechanism is already proven,
working code in this repository: `tests/conftest.py`'s `db_session`
fixture uses `join_transaction_mode="create_savepoint"` for precisely the
same reason (letting an inner `session.commit()` — there, from
`AuthService.signup`; here, a failed notification write — not destroy an
outer transaction's ability to roll back or continue cleanly). A future
implementation could point directly at that fixture as a working
reference for the mechanism, not invent it from scratch.

**Resolving the three named scenarios under this design**:

* *Letter operation succeeds, notification fails* — the intended,
  correctly-handled outcome: the savepoint absorbs the notification
  failure; the Letter and its audit row commit normally.
* *Letter operation succeeds, audit creation fails* — **should not be
  observable as a stable end state**: if the audit write fails, the whole
  transaction (Letter included) rolls back, so the caller sees the
  operation itself fail, not a "succeeded but unaudited" outcome.
* *Notification succeeds, main transaction fails* — **structurally
  impossible** under a same-session design: nothing commits independently
  before the single, outer `commit()` — either everything in that
  transaction (Letter, audit, and any successfully-savepointed
  notification) commits together, or none of it does.

## 21. Background / async processing

**No queue infrastructure exists** — confirmed by grep across
`requirements.txt` and `app/`: no Celery, no Redis, no task queue of any
kind, and no `BackgroundTasks` usage anywhere yet.

**RECOMMENDED for V1: fully synchronous**, for both audit and
notification writes, inside the same request/response cycle that
triggers them — the simplest option, requiring zero new infrastructure,
and the only option compatible with §20's "audit must be part of the same
transaction, and its failure must be visible to the caller" requirement
(a background/async audit write could not satisfy that).
`FastAPI BackgroundTasks` is a legitimate **OPTIONAL** future
refinement for the *notification* half specifically (never audit) if
synchronous notification writes are ever shown to add measurable request
latency — but adopting it preemptively, without evidence of an actual
performance problem, would be exactly the unjustified complexity this
task's own instructions warn against. **Celery/Redis/an external
worker**: explicitly not recommended — no existing infrastructure, no
confirmed scale requirement, and this project's `README.md` "Development
philosophy" already states a preference for simple, readable solutions
over premature complexity.

## 22. Audit vs. notification

Stated explicitly, as requested, because §7/§14/§20 above depend on
keeping the two conceptually and mechanically separate:

| | Audit | Notification |
|---|---|---|
| Answers | "What happened, and who did it?" | "What does this specific recipient need to know?" |
| Audience | Oversight — a `SYSTEM_ADMIN` (§9), reviewing after the fact | The recipient themselves, in the moment (or next login) |
| Immutability | Append-only, never edited or deleted (§5) | Mutable — `is_read`/`read_at` change; may eventually be deletable (§15) |
| Failure handling | Mandatory — a failure fails the operation (§20) | Best-effort — a failure must not fail the operation (§20) |
| Content | Structured old/new field pairs (§8), no free interpolation | Free `message` text, deliberately kept generic (§14) |
| Retention | Preserved/archived, not deleted, by default (§11) | Disposable — no accountability requirement (§15) |

**They must not become the same table or system** — a `Notification` row
happening to reference a `letter_id` might look superficially similar to
an `AuditLog` row with `entity_type="Letter"`, but they answer different
questions for different audiences under different consistency guarantees
(§20), and collapsing them would force notifications into audit's
stricter, transaction-blocking failure mode, or force audit into
notifications' disposable, best-effort one — neither is acceptable for
the entity it would compromise.

## 23. Dashboard implications

**Not implementing a dashboard — evaluating only where its data should
eventually come from.** **RECOMMENDED**: a future dashboard's
*current-state* metrics ("letters received this month," "pending
approvals right now") should read directly from the operational tables
(`Letter`, `User`, `Department`, etc.) via ordinary aggregate queries —
PostgreSQL handles this at this project's expected scale without any
special reporting layer. Its *historical/change* metrics ("actions per
day," "who approved the most Users last quarter") are exactly what
`AuditLog` would exist to answer, once populated (§4/§19-21) — this is a
natural, secondary consumer of the audit trail, not a reason to build it
differently than §1-22 already describe. **`Notification` is not a good
dashboard data source** — it's recipient-scoped and, per §15, deliberately
disposable; it was never designed to be a system of record for anything.
**Not recommended now**: a dedicated "derived reporting table" (a
materialized view, a separate warehouse-style schema, an ETL job) — no
reporting requirement has been confirmed yet, and building one
speculatively, before the actual dashboard's real query patterns are
known, risks designing the wrong aggregation shape.

## 24. Letter timeline

**RECOMMENDED: derive from `AuditLog` once it's populated, rather than
building a separate timeline table.** The task's own example (Created →
Edited → Document Added → Classification Changed → Archived) maps
directly onto §4's Letter/Document event list — a per-Letter timeline is,
structurally, just `SELECT * FROM audit_logs WHERE entity_type='Letter'
AND entity_id=:letter_id ORDER BY created_at`, no new storage needed.

**One genuine design wrinkle worth surfacing, not glossed over**: a
Letter's *documents* are audited under `entity_type="LetterDocument"`,
`entity_id=<document.id>` — not `entity_id=<letter.id>` — since each
document is its own real row with its own identity (§7's design is
correct for that). A **complete** Letter timeline that includes "Document
Added" events therefore can't be a single `entity_id=:letter_id` filter
alone; it needs a second clause reaching into the document event's own
recorded detail. **RECOMMENDED**: whenever a future phase implements
`DOCUMENT_UPLOADED` audit-event generation (§4), its `new_values` should
include the parent `letter_id` explicitly (e.g.
`{"letter_id": "...", "original_filename": "..."}`), so a full timeline
query becomes `WHERE (entity_type='Letter' AND entity_id=:id) OR
(entity_type='LetterDocument' AND new_values->>'letter_id' = :id)` — a
JSONB text-match on an indexed-adjacent table, not elegant, but requiring
**zero schema change**, only a convention for what a specific event type's
`new_values` should contain. This is preferable to adding a redundant
`letter_id` *column* to `AuditLog` itself (which would need to be
nullable for every non-Letter-related event, reintroducing exactly the
sparse-wide-table problem §7 already rejected).

## 25. Search / audit

**Not adding audit search — documenting only, per the task's
instruction.** A future audit search would plausibly need to filter by:
actor (`user_id`, already indexed), action (`action`, currently
unindexed — see §27), date range (`created_at`, already indexed),
target (`entity_type`/`entity_id`, already composite-indexed), and
department (not a column on `AuditLog` at all — would require the same
per-entity-type resolution join §9 already identified as a real
complexity, not a simple `WHERE` clause). This list is offered for a
future phase's reference; nothing here is being built now.

## 26. Database review

**CONFIRMED — no schema change is required to begin populating either
table as designed above.** Both `AuditLog` and `Notification` have been
unchanged since the Phase 2 baseline + hardening migrations (verified via
`alembic check` reporting zero drift throughout every phase since, most
recently re-confirmed at the end of Phase 4D) and remain structurally
sufficient for every event named in §4/§12, using the target/detail
strategy already in place (§7/§8).

**One optional, non-blocking improvement identified, not required**: an
index on `AuditLog.action` (currently unindexed) would help a future
"all `LETTER_ARCHIVED` events" query — **OPTIONAL**, not recommended to
add speculatively before an actual audit-search feature (§25) creates a
real, measured need for it. **No other schema change is identified.**
This review creates **no migration** — read-only, per explicit
instruction.

## 27. Test plan (design only, not implemented)

**Audit**:
1. An audit row's `user_id` matches the actual authenticated actor, not
   the affected resource's owner (proves §6's actor/resource distinction
   holds in a real write, not just in a worked example).
2. An audit row's `entity_type`/`entity_id` correctly identify the
   affected resource (e.g. a `Letter` update produces `entity_type="Letter"`,
   `entity_id=<that letter's id>`, not the acting user's id).
3. A historical actor survives account deactivation — the `AuditLog` row
   and its `user_id` remain intact and resolvable after the actor is
   deactivated (mirrors the Letter/`recorded_by` and Document/`uploaded_by`
   historical-identity tests already in this project).
4. No API path exists that updates or deletes an existing `AuditLog` row,
   for any role including `SYSTEM_ADMIN` (proves §5's append-only design
   holds, not just is documented).
5. A classified resource's audit visibility respects the same
   authorization a direct request for that resource would (§10) — an
   Admin who couldn't open a classified Letter directly also can't learn
   its details through an audit entry, once audit access is ever widened
   past `SYSTEM_ADMIN`-only.
6. Cross-department audit access is blocked once/if audit access is ever
   scoped below `SYSTEM_ADMIN` (§9) — an Admin in Department A cannot see
   an audit entry whose resolved resource-owner is Department B.
7. Audit creation is transactionally consistent with its business
   operation — a simulated audit-write failure rolls back the entire
   operation (letter/user/etc. not created either), proving §20's
   "mandatory, same-transaction" design, not just asserting it.

**Notifications**:
8. Recipient isolation — a User's `GET /notifications` never returns
   another user's rows, regardless of role (including `SYSTEM_ADMIN` —
   §17 explicitly recommends no role-based bypass of this specific rule).
9. Unread/read state transitions correctly (`is_read`/`read_at` both
   update together, never independently).
10. A User cannot mark another user's notification read — a mismatched
    id 404s (not 403), matching §17's enumeration-resistant design.
11. An inaccessible classified Letter's notification is never generated
    for a User who couldn't access it (§14's generation-time filtering),
    and — separately — a notification already generated before a
    classification change doesn't expose more than its already-generic
    `message` text after that change (§14's read-time re-check, and the
    limit of what re-checking can and can't undo).
12. A deactivated recipient's existing notifications remain intact and
    simply unreachable until reactivation (no special-case code needed —
    proving the "no special handling required" claim in §14, not just
    asserting it).
13. Transactional consistency — a simulated notification-write failure
    does **not** roll back the business operation or its audit row
    (§20's savepoint design, the inverse of test 7's audit assertion).
14. Duplicate notification prevention, **if ever needed** — not clearly
    needed for V1's one confirmed trigger (a Letter is registered exactly
    once, so "letter registered" naturally fires exactly once); flagged
    here only because the task asked it be considered, not because a
    concrete duplication scenario currently exists to test.

## 28. Pending business clarifications (consolidated)

1. **Audit access control beyond `SYSTEM_ADMIN`** (§9) — whether/how
   `ADMIN` should ever see department-scoped audit entries, and the
   per-entity-type department-resolution logic that would require.
2. **Notification recipients for "letter registered"** (§13) — whole
   department, Admins only, or a recorder-only receipt; §13's "department
   Admins" default is an explicit guess, not a confirmed answer.
3. **`UserAuthorization.expires_at` enforcement** (§4) — nothing currently
   checks it; an "expired" audit event depends on that first being built,
   which is itself unconfirmed.
4. **Audit and notification retention periods** (§11/§15) — no business
   period exists for either; a technical strategy (archive, don't delete,
   for audit; disposable for notifications) is recommended independent of
   whatever period is eventually set.
5. **Whether "letter updated," "document added," and department/account
   lifecycle events should generate notifications at all** (§12) — only
   "letter registered" is confirmed; every other candidate is
   RECOMMENDED/OPTIONAL, not settled.

## 29. Recommended Phase 4E (implementation) plan — not started

Sequenced so the highest-risk architectural decision is settled first,
before any code depends on it:

1. Confirm §20's audit-mandatory/notification-best-effort transactional
   design with whoever owns this decision — it is the one choice every
   other implementation step depends on getting right first.
2. Implement a single, reusable service-layer helper for writing an
   `AuditLog` row (action/entity_type/entity_id/old_values/new_values),
   called explicitly from each service method per §4's event list —
   starting with the highest-value, already-itemized events
   (Letter classification changes, Document uploads/downloads) rather
   than all of them at once.
3. Implement the notification-write helper with the `SAVEPOINT` pattern
   from §20, starting with the one CONFIRMED trigger (§2: letter
   registered) once §13's recipient question is answered — not before,
   since generating notifications with an unconfirmed recipient rule
   would need to be redone.
4. Build the read-side API (§16) — `GET /notifications`,
   `GET /notifications/unread-count`, the two `PATCH` endpoints —
   `recipient_user_id = current_user.id` scoped unconditionally (§17).
5. Resolve §9's audit-access-control question before building any
   audit-reading endpoint at all — do not default to building one with an
   unconfirmed access rule.
6. Tests per §27, prioritizing the transactional-consistency and
   data-leakage scenarios first (7, 11, 13), the same priority order
   Phase 4C/4D's own hardening passes used for their highest-risk
   findings.
7. Once audit is genuinely populated, revisit §24's Letter timeline as a
   read-only query feature — no new storage, no new migration.

## 30. Explicitly NOT in this phase (review pass — superseded by §31)

At the time of the review, nothing below had been built: audit
generation, notification generation, notification endpoints, audit
endpoints, dashboards, WebSockets, background queues, email
notifications, push notifications, frontend notification UI, an
automatic audit framework. **§31 records what changed** — audit
generation (for the events listed there) and notification generation/
retrieval/read-state are now implemented; audit *endpoints* (a read API),
dashboards, WebSockets, background queues, email/push notifications,
frontend UI, and an automatic (event-listener-based) audit framework
remain explicitly out of scope, unchanged.

## 31. Implementation record (Phase 4E implementation)

Built directly on top of §1-30's recommendations. Every item below is
IMPLEMENTED unless marked otherwise.

### Audit foundation

* **`app/services/audit_service.py:AuditService.record`** — the single,
  reusable service-level mechanism §16/§19 called for: no event bus, no
  SQLAlchemy event listeners, no domain-event framework. Callers pass
  `actor_id`/`action`/`entity_type`/`entity_id`/`old_values`/`new_values`
  directly; the method only `flush()`es (never `commit()`s or
  `rollback()`s) — the caller's own existing `session.commit()` is what
  actually makes the write mandatory (§20), exactly as designed.
* **`app/repositories/audit_log_repository.py`** — insert-only by
  construction: no `update`/`delete` method exists, and none should ever
  be added (§5). **No audit-viewing or audit-mutation endpoint of any
  kind was built** — confirmed by a dedicated test
  (`test_no_audit_mutation_endpoint_exists`) hitting a plausible audit
  URL and getting `404`/`405`, and by the fact that no
  `app/api/v1/endpoints/audit*.py` file exists at all.
* **Actor vs. target, enforced structurally, not by convention alone**
  (§6) — `record`'s `actor_id` parameter is always the authenticated
  caller threaded explicitly through every call site (e.g.
  `AdminService.approve_admin(user_id, *, actor_id)`,
  `admins.py`'s `current_user.id`) — never inferred from the target
  User/Letter/Department being acted on. Verified directly:
  `test_actor_is_the_caller_not_the_target` asserts an Admin-approves-User
  event's `user_id` equals the Admin's id and is never equal to the
  target User's id.
* **Targeted old/new values only, no full-row snapshots** (§8) — e.g.
  `LETTER_CLASSIFICATION_CHANGED`'s `old_values`/`new_values` contain
  only `classification_id`, nothing else; a general `LETTER_UPDATED`
  event records `{"changed_fields": [...]}"` — field *names*, never
  values, so a subject/sender-detail edit never duplicates that content
  into the audit table. Verified: `test_targeted_old_new_values_are_correct_not_full_snapshot`
  asserts the exact key set, and `test_sensitive_values_are_never_stored_in_audit`
  confirms a Letter's `text_content` and a User's `password_hash` never
  appear in any audit row's values.

### Notification foundation

* **`app/services/notification_service.py`** — the one CONFIRMED V1
  trigger, `notify_letter_registered`, wired into `LetterService.create_letter`.
  Recipient strategy is the recipient department's **ACTIVE Admins**
  (`UserRepository.list_admins`) — the PROVISIONAL default §13
  recommended, explicitly not a confirmed business answer; documented as
  such below, not silently promoted to CONFIRMED by having been built.
* **Best-effort via a real `SAVEPOINT`, not a hopeful try/except** (§20/
  §21) — `notify_letter_registered` wraps its body in
  `self.session.begin_nested()`; any exception inside is caught by the
  method's own outer `try/except Exception`, logged at `WARNING`
  (`app/core/logging.py:get_logger`, this project's one existing logging
  convention — no new one introduced), and never re-raised. Proven
  against a real failure inside the savepoint (not a stand-in that
  bypasses it): `test_notification_savepoint_failure_is_logged_and_does_not_block_letter`
  makes `NotificationRepository.create` itself raise, and asserts (a) the
  Letter still commits successfully, (b) the expected warning appears in
  the logs, (c) no notification row exists for that letter.
* **`message` stays generic** (§14/§15) — `"A new letter (reference:
  {reference_number}) has been registered in your department."` — no
  `subject`, `sender_name`, or any other Letter field is interpolated.
  Verified: `test_notification_message_contains_no_letter_content` creates
  a Letter with a deliberately sensitive `subject` and asserts it never
  appears in the generated notification's `message`.
* **Recipient isolation, enforced in the repository, not re-implemented
  per endpoint** (§17/§18) — every read/write method on
  `NotificationRepository` except `create` is scoped by
  `recipient_user_id`; `mark_read`'s lookup
  (`find_by_id_and_recipient`) means a notification belonging to a
  different recipient 404s identically to a nonexistent id, the same
  enumeration-resistant shape `DocumentNotFoundError`/`LetterNotFoundError`
  already established. No endpoint accepts a client-supplied
  `recipient_user_id` anywhere — confirmed by `NotificationResponse`
  having no such field and by dedicated cross-user tests.

### API

* **`GET /api/v1/notifications`** (paginated, newest first, deterministic
  secondary sort by id — the same convention `LetterRepository.list_letters`
  established), **`GET /api/v1/notifications/unread-count`**,
  **`PATCH /api/v1/notifications/{notification_id}/read`** (idempotent),
  **`PATCH /api/v1/notifications/read-all`** — all four routes use
  `get_current_user` only (no role restriction; ownership, not
  role/department, is the entire access rule), and are unconditionally
  scoped to `current_user` for every role including `SYSTEM_ADMIN` — a
  `SYSTEM_ADMIN` calling `GET /notifications` sees only notifications
  addressed to that `SYSTEM_ADMIN` account itself (none currently, since
  the only trigger notifies Admins), never another user's, confirmed
  live against `lrs_dev`.

### Wired into existing services — exactly the events named in the brief, no more

* **Letter** (`app/services/letter_service.py`): `LETTER_CREATED`,
  `LETTER_UPDATED` (general, `changed_fields` only),
  `LETTER_CLASSIFICATION_CHANGED`, `LETTER_CATEGORY_CHANGED` (both with
  targeted old/new id pairs, only emitted when that specific field
  actually changed value — not on every update call), `LETTER_ARCHIVED`
  (only on a genuine `ACTIVE → ARCHIVED` transition — re-archiving an
  already-archived letter, an existing idempotent no-op, does not
  produce a redundant entry).
* **Document** (`app/services/document_service.py`): `DOCUMENT_UPLOADED`
  — recorded *inside* the same try block that already handles Phase 4D's
  write-then-commit compensation logic, so an audit failure here triggers
  the identical file-cleanup path a database failure would (§10 of the
  implementation brief); metadata only (`letter_id`, `original_filename`,
  `mime_type`, `file_size`) — never document bytes.
* **User** (`app/services/user_service.py`): `USER_APPROVED`,
  `USER_DEACTIVATED`, `USER_REACTIVATED` (each only on a genuine status
  transition), `USER_AUTHORIZATION_CREATED`, `USER_AUTHORIZATION_REVOKED`.
  **"User department changed" was not implemented** — confirmed, again,
  that no such operation exists in this codebase for a plain `USER`
  account (only Admin department-transfer exists); inventing an event for
  an operation that doesn't exist was explicitly out of scope.
* **Admin** (`app/services/admin_service.py`): `ADMIN_AUTHORIZATION_CREATED`,
  `ADMIN_APPROVED`, `ADMIN_DEACTIVATED`, `ADMIN_REACTIVATED` (each only on
  a genuine transition), `ADMIN_DEPARTMENT_CHANGED` (targeted old/new
  `department_id` pair). Required adding an `actor_id` parameter to four
  service methods that previously received no caller identity at all
  (`approve_admin`, `deactivate_admin`, `reactivate_admin`,
  `change_admin_department`) and updating `admins.py` to thread
  `current_user.id` through — the previously-unused `_current_user`
  dependency parameter is now used.
* **Department** (`app/services/department_service.py`):
  `DEPARTMENT_CREATED`, `DEPARTMENT_ACTIVATED`, `DEPARTMENT_DEACTIVATED`
  (each only on a genuine transition). **`DEPARTMENT_UPDATED` (name/code
  changes) was deliberately not implemented** — the implementation
  brief's own §7 lists only created/activated/deactivated for Department,
  unlike Category/Classification (below), which explicitly include
  "updated"; honored as a deliberate, brief-specified asymmetry, not an
  oversight.
* **Category** (`app/services/category_service.py`) /
  **Classification** (`app/services/classification_service.py`):
  `CATEGORY_CREATED`/`UPDATED`/`ACTIVATED`/`DEACTIVATED` and the
  `CLASSIFICATION_*` equivalents. `restricts_access` changes are folded
  into `CLASSIFICATION_UPDATED`'s `changed_fields` list (a field name,
  never the before/after boolean value) rather than a separate named
  event — the brief's own event list did not name one, so none was
  invented.
* **Not implemented, confirmed deliberately**: "Letter recipient
  department changed" and "expired" (authorization) — both remain
  operations that do not exist anywhere in this codebase (§4 of the
  original review already established this; re-confirmed, not
  re-guessed, during implementation).

### Transaction behavior

Exactly the design in §20, proven, not just asserted:
`test_audit_failure_rolls_back_letter_creation` forces `AuditService.record`
to raise and confirms the Letter row does not survive a rollback of the
still-open transaction; `test_notification_savepoint_failure_is_logged_and_does_not_block_letter`
forces a failure *inside* the notification `SAVEPOINT` and confirms the
Letter (and its mandatory audit row) commit successfully regardless.

### Database / migration result

**Zero schema changes.** Both `AuditLog` and `Notification` are used
exactly as they already existed since the Phase 2 baseline migration —
`alembic check` against `lrs_dev` reports "No new upgrade operations
detected," both before and after this phase.

### Test results

33 new tests — `tests/integration/test_audit.py` (21) and
`tests/integration/test_notifications.py` (12) — covering all 30
audit/notification scenarios named in the implementation brief's §24 (one
test per scenario in most cases; a few scenarios share a test where
testing them together was more direct, e.g. recipient isolation and
"belongs to exactly one recipient" are proven by the same
two-Admin-notification-list assertion), plus a couple of additional
idempotency/negative cases found necessary while writing them (re-archiving
doesn't duplicate an audit entry; an inactive Admin is never a
notification recipient). One test written during development
(`test_notification_failure_does_not_rollback_letter_creation`) was
removed as redundant and unrealistic — it monkeypatched the entire
`notify_letter_registered` method, bypassing the very internal
try/except-around-`begin_nested()` safety net the *other* transactional
test (`test_notification_savepoint_failure_is_logged_and_does_not_block_letter`)
correctly exercises; keeping both would have tested the same guarantee
twice, once realistically and once not. Regression scenarios 31-35
(existing authorization, classified-Letter access, department isolation,
document access, Letter search/pagination) are covered by the
pre-existing 425-test suite, which stays green — re-running it after
every wiring change was the actual regression check, not a duplicated
set of new test functions asserting facts the existing suite already
established. **Full suite: 458 passed** (425 baseline + 33 new), re-run
3 consecutive times, identical results.

### Live verification against `lrs_dev`

A running `uvicorn` instance, real minted JWTs, real HTTP: Letter
registration produced both a `LETTER_CREATED` audit row (correct actor,
entity_type, targeted `new_values`) and a `LETTER_REGISTERED` notification
for each of the recipient department's two Admins; each Admin's own
`GET /notifications` returned only their own row; one Admin marking their
notification read left the other Admin's unread count untouched; an
Admin attempting to mark the *other* Admin's notification read got `404`;
`read-all` only affected the calling Admin's own rows; the `SYSTEM_ADMIN`'s
own notification list was empty (never a recipient under the current
strategy); an unauthenticated request got `401`. All test data (the
department, its users, the letter, its audit row, its notifications) was
deleted afterward; `lrs_dev` confirmed back to its pre-verification state
(3 seeded `categories` rows, nothing else).

### Known limitations (post-implementation)

* **Audit access control remains unimplemented** (§9) — no read API
  exists for `AuditLog` at all; the SYSTEM_ADMIN-only recommendation is
  still a recommendation for whenever one is built, not something this
  phase needed to act on.
* **Notification recipient strategy ("department Admins") is still
  PROVISIONAL**, not confirmed by the business — implemented as the
  interim default the review named, with the guess clearly labeled in
  both code comments and this document, not quietly treated as settled.
* **No notification triggers beyond "letter registered" exist** — every
  other candidate in §12 (document upload, classification/category
  change, user/admin/department lifecycle) remains unimplemented,
  exactly as instructed. **Superseded in one narrow respect by Phase
  6A** (`docs/architecture/correspondence.md` §11): two new triggers,
  `notify_letter_dispatched`/`notify_correspondence_recorded`, were
  added for the new outgoing-correspondence workflow, reusing this
  exact SAVEPOINT-wrapped, best-effort, "department's ACTIVE Admins"
  pattern — still the same PROVISIONAL recipient strategy noted above,
  not a new one.
* **`UserAuthorization.expires_at` is still not enforced anywhere** — an
  "expired" audit event continues to depend on that being built first,
  which it wasn't (out of scope, unchanged from the review).
