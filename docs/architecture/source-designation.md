# Source Department & Designation Master Data — Architecture & Requirements Review (Phase 5H)

**Status: REVIEW ONLY. No backend or frontend code, migration, or test
was written this phase.** Prepared for handover, under real time
pressure — this document is written to be actionable tonight, not
merely thorough. Repository confirmed clean at `91cb72c` (the
`DepartmentSelector` controlled-select fix) before this review began.

## 0. How to read this document

Same taxonomy this project has used since Phase 4A, plus the brief's
own explicit handover split:

* **CONFIRMED** — verified directly against current source, or already
  settled by an explicit prior product decision (cited).
* **RECOMMENDED** — this document's own proposal. Not implemented.
* **PROVISIONAL** — an explicit judgment call, flagged for review.
* **PENDING BUSINESS CLARIFICATION** — genuinely open.
* **PENDING BACKEND API** — needs backend work not yet built.
* **NOT RECOMMENDED** — considered and rejected, with a reason.
* **FUTURE** — plausible eventually, explicitly not tonight.
* **MUST IMPLEMENT BEFORE HANDOVER** vs. **NICE TO HAVE / FUTURE** — the
  brief's own §22 split, applied to every recommendation in §22 below.

## 0.1 Two findings that change the shape of this review

Before the section-by-section analysis, two facts — verified against
current source, not assumed — determine what "implement Source and
Designation" actually requires. Both are stated up front because they
are easy to miss and, if missed, would produce a feature that looks
built but doesn't work for the people who need it.

**Finding 1 — `source_department_id` already exists, end to end, on
the backend.** `LetterCreate`, `LetterUpdate`, `LetterResponse`, and
`LetterListItem` (`backend/app/schemas/letter.py`) all already have an
optional `source_department_id: Optional[uuid.UUID]` field.
`LetterService._validate_source_department` (`backend/app/services/
letter_service.py`) already rejects a nonexistent department
(`SourceDepartmentNotFoundError`, 404) or an `INACTIVE` one
(`SourceDepartmentNotActiveError`, 409) on create and on any explicit
update. **This was built in Phase 4B and simply never given a frontend
control** — `LetterFormPage.jsx`'s own docstring says so directly:
*"omitted from this V1 form because resolving it to a selectable name
requires `GET /api/v1/departments` (SYSTEM_ADMIN-only)... A scope
simplification, not a backend blocker."* Tonight's task is therefore
overwhelmingly a **frontend** task for Source — with one small,
necessary backend exception named in Finding 2.

**Finding 2 — the exact same access gap that already blocks
Category/Classification on the Letter form would silently block Source
Department and Designation too, unless corrected.** `GET /api/v1/
departments` is `require_system_admin`-only today (`app/api/v1/
endpoints/departments.py`). USER/ADMIN — the only roles that can call
`POST /letters` at all (`require_user_or_admin`; SYSTEM_ADMIN has no
department to record a letter against) — **cannot call this endpoint**.
This is the identical, already-documented gap `docs/architecture/
frontend.md` §36 flagged for Category/Classification
("`GET /api/v1/categories`/`/classifications` are `require_system_admin`-
only, but `POST /api/v1/letters` structurally excludes SYSTEM_ADMIN...
no role that can create/edit a Letter can load those reference lists").
**If Designation's own list endpoint is designed the same restrictive
way, the entire feature demoed tonight — USER/ADMIN picking a Source
Department and a Designation while recording a Letter — will be
non-functional for its actual users**, exactly reproducing a mistake
this project has already made once and already documented as a gap.
Both §5 and §11 below treat this as the single most important design
decision in this review.

---

## 1. Current Source architecture (CONFIRMED, re-read fresh)

| Field | Type | Required | Meaning |
|---|---|---|---|
| `source_name` | `String(500)`, not null | Yes, on every `LetterCreate` | "The required baseline representation of who/where a letter came from" (`app/models/letter.py`'s own docstring) — free text today |
| `source_department_id` | nullable FK → `departments.id`, `ondelete=RESTRICT` | No | "An optional structured cross-reference, populated only when the source happens to be an LRS-registered department... The system must never force every source into a department FK" — **an explicit, already-confirmed product decision**, not something this review is free to override |
| `source_location` | nullable `String(255)` | No | Free text, unrelated to department selection |

`source_name` and `source_department_id` are **not** the same thing and
were never intended to be — `source_name` is the field that makes the
Letter readable even when the source is an external organization LRS
has no record of; `source_department_id` is a bonus structured link for
the subset of letters that genuinely originated from another
LRS-registered department. This distinction is load-bearing for §4.

## 2. Current Designation architecture (CONFIRMED — none exists)

`sender_designation` (`app/models/letter.py`) is a plain
`String(255)`, not null, free-text column — no FK, no relationship, no
master-data table of any kind. No `Designation` model, schema,
repository, service, endpoint, or migration exists anywhere in this
codebase. This is a genuinely new resource, not a hidden existing one
(unlike Source, per Finding 1).

## 3. Letter model — full relevant field recap (CONFIRMED)

`recipient_department_id` (not null, FK, indexed, composite-indexed
with `received_at`) is the isolation boundary `assert_letter_access`
enforces. `sender_department` (not null, free text) is a third,
separate concept — "the sender's own department," distinct from both
Source and Recipient, already documented in the form's own hint text.
`recorded_by` (not null, FK → `users.id`) is who entered the Letter.
Nothing about any of these changes in this review.

---

## 4. Source semantics — which option, and why

Evaluating the brief's own four options against Finding 1 and the
model's own documented intent:

* **Option A (use `source_department_id` alone, drop `source_name`)**
  — **NOT RECOMMENDED.** `source_name` is not redundant with
  `source_department_id` — it is the field that keeps a non-
  departmental source (an external organization) representable at all.
  Dropping it would silently reverse the explicit product decision
  quoted in §1, and would require a migration touching every existing
  Letter's required field — an unjustifiable risk hours before
  handover for a supervisor request that never asked for this.
* **Option C (replace `source_name` entirely)** — **NOT RECOMMENDED**,
  same reasoning.
* **Option B (use `source_department_id` for the selection, retain
  `source_name` as a derived/display field)** — **RECOMMENDED, and
  the one this review designs.** Concretely: when the user picks a
  Department from the new Source selector, the frontend sets
  `source_name` to that department's own `name` automatically — the
  user never manually types it. `source_name` remains the field the
  backend actually requires and stores (zero backend schema change for
  this field); `source_department_id` is submitted alongside it,
  carrying the structured link. This is not a new pattern — it is
  **the exact mechanism this review recommends for Designation too**
  (§8), for the same reason, and both mirror how `LetterListItem`
  already carries both a structured id and a required display string
  side by side today.

**One tension this review does not silently resolve**: the supervisor's
literal words ("select from the... Department list," "should not type
an arbitrary Source name") could be read as "every Letter's source must
now be a department" — which would conflict with the already-confirmed
"must never force every source into a department FK" decision (an
external sender genuinely has no department to pick). **RECOMMENDED for
tonight**: build the dropdown as the primary, default control — exactly
what was demoed — without deciding tonight whether an "external source"
escape hatch is still needed; §21 names this explicitly as
`PENDING BUSINESS CLARIFICATION` rather than guessed at either
direction. If the business confirms every source really is always a
department, `source_department_id` can be promoted to required later;
that is not done here.

## 5. Source Department selection — scope, and the access-gap fix it requires

**Which departments appear**: `PROVISIONAL, RECOMMENDED`: every
`ACTIVE` department, system-wide — not scoped to the recorder's own
department. A Letter's origin is logically independent of who is
recording it (a Finance-department User can legitimately record a
Letter that originated from Planning); there is no confirmed reason to
narrow the list, and `_validate_source_department` already rejects an
`INACTIVE` selection regardless of what the dropdown offers, matching
the exact same "UX nicety, not a security boundary" precedent
`DepartmentSelector.jsx`'s own docstring already states for its
`activeOnly` prop.

**The access gap (Finding 2, concrete fix)**: **MUST IMPLEMENT BEFORE
HANDOVER, backend, minimal**: relax `GET /api/v1/departments`'s
dependency from `require_system_admin` to `get_current_user` — a
one-line change to a single `Depends(...)` call in `app/api/v1/
endpoints/departments.py`. **Nothing else about that endpoint changes**:
the existing `status` query filter already lets a caller ask for
`status=ACTIVE` only; `GET /departments/{id}`, `POST /departments`,
`PATCH /departments/{id}`, and both activate/deactivate endpoints all
keep `require_system_admin` untouched — only the list-everything read
path broadens. This is safe because a `DepartmentResponse`
(`id, name, code, status, created_at, updated_at`) carries nothing
confidential — department names are already implicit organizational
knowledge, already visible indirectly through every USER/ADMIN's own
account, and this change touches **read access to department names
only**, never `assert_department_access`/`assert_letter_access`, never
the isolation boundary itself (§6). This is the smallest possible fix
to Finding 2 for Source — reusing an endpoint that already does
everything needed, rather than inventing a new one.

**Explicit verification that this cannot become a security bypass**:
`_validate_source_department` only checks existence + `ACTIVE` status
— it never calls `assert_department_access`, never compares against
`current_user.department_id`, and has no role branch of any kind.
Submitting a `source_department_id` has **zero effect** on which
Letters a caller can see, create, or edit — that is entirely
`recipient_department_id`'s job (§6), unchanged by anything in this
review. A USER/ADMIN gaining read access to the department *name list*
does not grant them read access to any *Letter* they couldn't already
see — the two are unrelated authorization questions.

## 6. Source Department vs. Recipient Department (CRITICAL — restated, not changed)

**Recipient Department** (`recipient_department_id`) is the registry's
ownership/isolation boundary — `assert_letter_access`'s first, always-
run check, unconditionally scoping USER/ADMIN to their own department.
**Source Department** (`source_department_id`) is origin metadata only
— "an external sender has no LRS account and isn't part of the role/
department hierarchy at all" (`assert_letter_access`'s own docstring).
**Nothing in this review touches, weakens, or blurs this distinction.**
A Letter can legitimately have Source = Finance and Recipient =
Planning simultaneously; the dropdown this review adds only ever
writes to `source_department_id`, never to `recipient_department_id`
(which remains entirely server-derived from the recorder's own account,
unchanged since Phase 4B).

---

## 7. Designation master-data design

**A new table is required** — confirmed, nothing existing can be
repurposed (§2). **RECOMMENDED shape**, modeled directly on `Category`/
`Classification` (the closest, already-proven precedent in this exact
codebase) with one deliberate departure explained below:

```
Designation
  id            UUID, primary key
  name          String(255), not null
  status        ActiveStatus enum (reused, not a new lifecycle), default ACTIVE, indexed
  created_at    (TimestampMixin)
  updated_at    (TimestampMixin)
```

No `description` field — the brief's own proposed shape doesn't include
one, and a job-title-style value ("Section Officer") doesn't obviously
need elaboration the way a Category might; not adding one is the
minimal choice, reversible later if ever needed.

* **Uniqueness**: **RECOMMENDED, yes** — an unmanaged, unbounded
  dropdown invites duplicate near-identical entries. **Case-
  insensitive**, a deliberate departure from Category/Classification's
  plain case-sensitive `unique=True`: reusing the exact technique
  `User.email` already uses (`Index("uq_users_email_lower",
  func.lower(email), unique=True)`) — `Index("uq_designations_name_lower",
  func.lower(name), unique=True)`. Reasoning: Category/Classification
  are a short, deliberately curated list set once by a careful
  reviewer; Designation is meant to be added to "over time" by
  SYSTEM_ADMIN under time pressure, where "Section Officer" vs.
  "section officer" is a realistic, UX-degrading duplicate this review
  would rather prevent structurally than rely on manual care.
* **Whitespace/casing normalization on input**: **RECOMMENDED** —
  reuse the exact `_normalize_name` helper (`.strip()`, reject blank)
  `CategoryCreate`/`CategoryUpdate` already use; no new logic.
* **Physical deletion**: **NOT RECOMMENDED, matching every reference-
  data precedent in this system** (Department/Category/Classification)
  and the business decision's own explicit wording — `status` moves to
  `INACTIVE` only.
* **Activate/deactivate idempotency**: **RECOMMENDED**, identical to
  `CategoryService.activate_category`/`deactivate_category` — calling
  activate on an already-`ACTIVE` row succeeds silently (no duplicate
  audit entry), matching the exact `was_active`/`was_inactive` guard
  pattern.
* **Inactive designations remain selectable for historical letters,
  never for a new assignment** — see §9.

## 8. Designation historical integrity — the recommended strategy

The brief's own four options, evaluated against the one strategy this
project has **already built and proven** for the identical problem
(Category/Classification's own FK-plus-never-delete pattern, and
Source's own `source_department_id`/`source_name` coexistence, §4):

* **Option A (keep `sender_designation` as plain text forever, no FK)**
  — **NOT RECOMMENDED.** Satisfies historical integrity trivially (it's
  just a string) but provides no structured way to enforce "only
  ACTIVE designations selectable" or to let SYSTEM_ADMIN manage a real
  list — it doesn't implement the business decision at all, only the
  cosmetic dropdown appearance of it.
* **Option B (replace `sender_designation` with a required
  `designation_id` FK)** — **NOT RECOMMENDED for tonight.** Every
  existing Letter has a free-text `sender_designation` value with no
  guaranteed match to any future master-data row; making this a hard
  replacement would require backfilling a `Designation` row for every
  **distinct existing string** (realistically inconsistent — casing,
  abbreviations, typos) before the column could become non-null. That
  is real data-migration risk on the eve of handover, solving a problem
  the business never asked this review to solve (only new letters need
  a dropdown).
* **Option C (store both) — RECOMMENDED, exactly as named.** Add a new,
  **nullable** `designation_id` FK (`ondelete=RESTRICT`, matching
  `category_id`/`classification_id`'s own `ondelete` behavior) **while
  keeping `sender_designation` exactly as it is today** — required,
  free text, unchanged validation. When the frontend dropdown is used,
  it auto-sets `sender_designation` to the selected Designation's
  `name` (identical mechanism to Source's own `source_name` auto-fill,
  §4) and additionally submits `designation_id`. **Every existing
  Letter needs zero backfill** — its `designation_id` is simply `NULL`
  forever, and its existing `sender_designation` text continues to
  display exactly as it always has. This is not a new idea invented
  for Designation — it is the same coexistence pattern
  `source_department_id`/`source_name` already prove works in this
  exact codebase.

**A deactivated Designation never makes a historical Letter
unreadable**: the Letter's own `sender_designation` text is untouched
by deactivation (it isn't derived at read time, only at write time);
even a Letter that *does* carry a `designation_id` pointing at a now-
`INACTIVE` row still resolves that FK to a real, readable row (never
physically deleted) — exactly how a Letter tagged with a now-inactive
Category still renders its name today, with an "(inactive)" affordance
the existing `LetterFormPage.jsx` already demonstrates the UI pattern
for (`{option.status === 'INACTIVE' ? ' (inactive)' : ''}`).

## 9. Create/Edit behavior — mirrors `_validate_category` exactly

**RECOMMENDED**: add `LetterService._validate_designation`, identical
in shape to the existing `_validate_category`:

```python
def _validate_designation(self, designation_id):
    if designation_id is None:
        return
    designation = self.designations.find_by_id(designation_id)
    if designation is None:
        raise DesignationNotFoundError()
    if designation.status != ActiveStatus.ACTIVE:
        raise DesignationNotActiveError()
```

Called unconditionally (if supplied) on `create_letter`, and only
`if designation_id is not None` on `update_letter` — the exact same
"omitted means unchanged, so an unchanged inactive reference is never
re-validated" behavior `category_id`/`classification_id` already have.
This answers every question §9 posed, by direct, already-shipped
precedent, not a new policy: only `ACTIVE` designations are selectable
for a *new* assignment (create, or an explicit change on update); an
existing Letter whose designation later goes `INACTIVE` remains fully
editable — editing any *other* field never touches or re-validates
`designation_id`; changing `designation_id` to a *different* value
always requires the new value to be `ACTIVE`; a designation being
deactivated after a Letter was created has **no effect** on that
Letter unless someone later tries to explicitly reassign its
designation to something else.

---

## 10. SYSTEM_ADMIN designation management API

Comparing against `/categories` (the closest precedent) rather than
guessing endpoint shapes: **RECOMMENDED**, mirroring it exactly,
including the verb choice — the brief's own illustrative `PATCH .../
activate` is corrected here to match what this codebase actually uses
(`POST`, confirmed from `categories.py`, not `PATCH`):

| Endpoint | Access | Mirrors |
|---|---|---|
| `POST /api/v1/designations` | SYSTEM_ADMIN only | `POST /categories` |
| `GET /api/v1/designations` | **`get_current_user` — all authenticated roles** (§11, the critical departure) | Shape mirrors `GET /categories`; access does not |
| `GET /api/v1/designations/{id}` | SYSTEM_ADMIN only | `GET /categories/{id}` |
| `PATCH /api/v1/designations/{id}` | SYSTEM_ADMIN only | `PATCH /categories/{id}` |
| `POST /api/v1/designations/{id}/activate` | SYSTEM_ADMIN only | `POST /categories/{id}/activate` |
| `POST /api/v1/designations/{id}/deactivate` | SYSTEM_ADMIN only | `POST /categories/{id}/deactivate` |

Every write path stays SYSTEM_ADMIN-only, satisfying the business
decision exactly ("SYSTEM_ADMIN will manage the designation list");
ADMIN/USER have no create/update/activate/deactivate capability of any
kind — there is no endpoint for them to misuse even if they tried.

## 11. Designation dropdown API — the critical access decision

**This is Finding 2's other half, and the reason §10's table marks one
row differently from every other reference-data list endpoint in this
system.** `GET /api/v1/designations` **must** be reachable by
`get_current_user` (any authenticated, `ACTIVE` account) — **not**
`require_system_admin`, unlike `GET /categories`/`/classifications`/
`/departments`'s own list endpoints. If it were SYSTEM_ADMIN-only like
its siblings, USER/ADMIN — the only roles that can ever record a
Letter — could never populate the dropdown, and the entire feature
would silently fail to do the one thing it was built for. The business
decision itself already confirms this is required, not merely
convenient: *"USER and ADMIN will only select from ACTIVE designations
when recording/editing a Letter."* That sentence is not satisfiable
without this endpoint being readable by USER/ADMIN.

**Filters/pagination**: **RECOMMENDED, minimal, matching Category/
Classification's own list endpoint exactly**: an optional `status`
query filter (so any caller, including USER/ADMIN, can request
`?status=ACTIVE`), **no pagination** — every peer reference-data list
endpoint in this codebase already returns its complete result set with
`total = len(items)`; introducing pagination here would be
inconsistent over-engineering for a resource expected to hold, at
most, a few dozen rows, not the "hundreds of unrelated records" concern
the brief itself warns against speculating about. No sort/search
parameter is proposed — Category/Classification have none either, and
nothing here suggests Designation needs different treatment.

---

## 12. Frontend Designation UX

**Where SYSTEM_ADMIN manages designations**: **MUST IMPLEMENT BEFORE
HANDOVER, deliberately minimized**: without *some* management surface,
SYSTEM_ADMIN has no way to create even the first designation (§16 — no
seed data is being invented), which would leave the dropdown
permanently empty and the feature unusable end to end. **RECOMMENDED
for tonight**: **one page**, not Department's fuller three-page
pattern (list/create/detail) — a single `DesignationListPage` combining
an inline create form at the top with a list below showing each row's
name, `StatusBadge`, and an Activate/Deactivate button, mirroring
`AdminListPage`'s own list-plus-inline-action shape rather than
`DepartmentCreatePage`'s separate route. A dedicated detail/edit-name
page is **NICE TO HAVE / FUTURE** — not needed to satisfy tonight's
demo, and the backend's `PATCH` endpoint existing is enough to support
one later without any schema change.

**Where Designation appears in `LetterFormPage`**: replaces the current
free-text "Sender designation" input with a standard, labeled
`<select>` — following the exact same inline pattern the Category/
Classification selects in this same file already use (a plain
`<select>` mapping over a loaded options array), not a new component;
`DepartmentSelector` itself is Department-specific and not reused here.
**Inactive designations are hidden** from the create-time list (loaded
with `?status=ACTIVE`, matching `AdminAuthorizePage`'s own
`departmentService.list({status: 'ACTIVE'})` convention exactly) —
except on **edit**, where the Letter's *already-assigned* designation
must still render correctly even if it has since gone `INACTIVE` (§9);
**RECOMMENDED**: if the currently-assigned designation is not present
in the active-only list the edit form loaded, inject it into the
option list as a distinct, clearly labeled `(inactive)` entry — the
exact same technique `LetterFormPage.jsx` already uses for Category/
Classification.

**Loading/error/empty states**: reuse `LoadingState`/`ErrorState`
exactly as every other reference-data fetch in this codebase already
does. **Zero active designations**: **RECOMMENDED**: render the
`<select>` with only a "Select a designation" placeholder and no real
options (never a fabricated default) — combined with §16's own
recommendation not to make `designation_id` hard-required, this keeps
Letter recording functional even before SYSTEM_ADMIN has added a
single designation, at the cost of the sender-designation field simply
having nothing to select until then.

**Validation**: **RECOMMENDED**: no new validation-message pattern —
reuse `isBlank`-style required-field checking in `formValidation.js`
exactly as every other required select (e.g. Admin Authorize's own
`department_id` check) already does, *if* designation is made
required at all (§16 recommends against this for tonight).

**Existing Letters**: display unchanged — `sender_designation` (the
text field) continues to be exactly what renders on `LetterDetailPage`
and `LetterTable`; no display code needs to change, since the
recommended strategy (§8) never removes or renames that field.

## 13. Frontend Source UX

**Source Department → a new `DepartmentSelector` instance**,
reusing the exact same component already fixed for the controlled-
value bug this session (`activeOnly`, no `includeAllOption` — but see
the note below about the placeholder now always rendering, which this
selector benefits from directly). **Source Location remains free
text**, unrelated to this change. **Sender fields remain fully
separate and untouched** — `sender_name`/`sender_designation` (now a
dropdown, §12)/`sender_department`/`sender_address` are conceptually
and structurally independent of Source, exactly as today.

**Label clarity — RECOMMENDED, a small but real change**: the existing
form fieldset is already titled "Source" with a field labeled "Source
name *"; **change the field's own label to "Source Department"**
when the new selector replaces the free-text input, and keep the
existing `sender_department` field's hint text exactly as it is today
("distinct from 'Source,' which may or may not be the same
organization") — updating only the word "Source" in that sentence to
"Source Department" for consistency. This directly answers §20:
`docs/architecture/letter-registry.md`'s own three-department
terminology (Source, Recipient, Sender) already risks ambiguity between
"Source" and "Sender"; making the label explicitly "Source Department"
the moment it becomes a department picker (rather than free text)
removes that ambiguity at the exact point a user would otherwise be
confused by three similar-sounding department-shaped fields on one
screen.

---

## 14. API contract impact — exact recommended contract

**`LetterCreate`**: `source_department_id` — **no change, already
exists**, remains optional. `designation_id: Optional[uuid.UUID] = None`
— **new field**, optional (§16). `sender_designation` — **no change**,
remains required text, now populated by the frontend from the selected
Designation's name rather than manual typing.

**`LetterUpdate`**: `designation_id: Optional[uuid.UUID] = None` — new
field, `None` means "leave unchanged," identical convention to every
other optional field on this schema.

**`LetterResponse`/`LetterListItem`**: both gain `designation_id:
Optional[uuid.UUID]`, alongside the existing `sender_designation`
string — **both are returned, never one replacing the other**,
matching exactly how `source_department_id` and `source_name` already
coexist in these same two schemas today.

**No field is removed. No field is renamed. Full backward
compatibility for every existing consumer of these four schemas.**

## 15. Database / migration assessment

**RECOMMENDED, one migration, two changes, no backfill**:

1. **New `designations` table** — `id`, `name` (not null), a
   case-insensitive unique functional index (§7), `status`
   (`active_status_enum`, reused, indexed, default `ACTIVE`),
   `created_at`/`updated_at` (the existing `TimestampMixin`).
2. **New nullable column** `letters.designation_id` — FK →
   `designations.id`, `ondelete=RESTRICT` (matching `category_id`/
   `classification_id`'s own `ondelete` behavior), indexed (matching
   every other Letter FK column, all of which are individually
   indexed today).

**Why no Letter-table migration touches existing data**: `designation_id`
is nullable and every existing row simply gets `NULL` — its own
`sender_designation` text is completely untouched by this migration.
**Historical production data is not at risk** because nothing about
this migration modifies, reads, or depends on any existing row's
current values; it is purely additive. **DO NOT CREATE THIS MIGRATION
during this review** — this is the exact shape a future implementation
step should write, not something produced here.

## 16. Seed data strategy

**CONFIRMED by the business decision itself and this review's own
recommendation: no designations are seeded.** The supervisor
deliberately did not provide a list, and inventing organizational job
titles would be a worse outcome than an empty list SYSTEM_ADMIN fills
in deliberately. **A real, easy-to-miss consequence this review flags
explicitly**: an empty `designations` table at handover time means the
dropdown starts genuinely empty. **RECOMMENDED, directly because of
this**: do **not** make `designation_id` a hard-required field on
`LetterCreate` for tonight — if it were required and the table starts
empty, Letter recording itself would be broken for USER/ADMIN the
moment handover completes, until a SYSTEM_ADMIN manually adds at least
one designation first. Keeping it optional (§14) avoids this landmine
entirely while still fully satisfying the demoed UX the instant at
least one designation exists. Whether it should become mandatory once
the organization has populated a real list is `PENDING BUSINESS
CLARIFICATION`, explicitly not decided here (§21).

---

## 17. Security threat review

| # | Threat | Mitigation | Remaining risk |
|---|---|---|---|
| Unauthorized designation creation | `POST /designations` is `require_system_admin` | None found |
| Unauthorized activate/deactivate | Both endpoints `require_system_admin` | None found |
| Designation ID injection | `_validate_designation` rejects any id that doesn't resolve to a real, `ACTIVE` row — a made-up UUID is rejected identically to a real-but-inactive one | None found, matches `_validate_category`'s own proven behavior |
| Inactive designation injection on a new/changed assignment | Rejected by `_validate_designation`'s `ACTIVE` check | None found |
| Source Department scope escalation | `_validate_source_department` never calls `assert_department_access`; submitting any `source_department_id` has zero effect on Letter visibility (§5/§6) | None found |
| Cross-department Letter access via Source | Not possible — `recipient_department_id` remains the sole isolation boundary, untouched by this review | None found |
| Classified Letter behavior | Untouched — `letter_visibility_filter`/`assert_letter_access` reference `classification_id`/`recipient_department_id` only, never `source_department_id`/`designation_id` | None found |
| Historical designation manipulation | No endpoint lets any role rewrite a Letter's *existing* `sender_designation` text via designation deactivation — deactivation only blocks *future* assignment (§9) | None found |
| IDOR (designation or department ids) | Both are reference-data lookups scoped by existence + `ACTIVE` status only, never by "does this id belong to caller" — there is no ownership concept to violate | None found |
| System Admin protection | Unaffected — no change to any Admin/User endpoint | N/A this phase |
| Admin/User protection | Relaxing `GET /departments`'s read access (§5) does not grant ADMIN/USER any new *write* capability anywhere, and does not change `require_admin`/`require_user_or_admin` gating on any endpoint | None found |

**The frontend is never the security boundary** for either feature:
every rule above is enforced in `_validate_source_department`/
`_validate_designation`/`assert_letter_access`, none in
`LetterFormPage.jsx` or any selector component.

## 18. Test strategy (design only, not implemented)

**Backend**: SYSTEM_ADMIN can create/activate/deactivate a Designation;
ADMIN and USER each get `403` attempting any of the three; duplicate
name (including a casing-only duplicate, proving the case-insensitive
index) is rejected with `409`; a new Letter with an `INACTIVE`
`designation_id` is rejected with `409`; a nonexistent `designation_id`
is rejected with `404`; a Letter created with a valid `designation_id`,
whose Designation is later deactivated, remains fully readable and
editable via `PATCH` on every *other* field with no re-validation
error; `GET /designations` succeeds for all three roles (the critical
regression proving Finding 2 was actually fixed); `GET /departments`
succeeds for USER/ADMIN post-fix, while `POST`/`PATCH`/activate/
deactivate on Departments still correctly `403` for both; a
`source_department_id` never influences which Letters a USER/ADMIN can
list or fetch (a fixture with two departments, asserting the existing
isolation test suite's own conclusions are unaffected); classified-
Letter visibility tests continue to pass unmodified. **Frontend**:
designation dropdown loads and shows only `ACTIVE` options; an
already-assigned-but-now-inactive designation still renders correctly
on the edit form; zero-designations empty state renders a placeholder-
only select, not an error; submitting sends both `designation_id` and
the auto-derived `sender_designation` text; the Source Department
selector reuses `DepartmentSelector` correctly (including the recent
controlled-value fix — the same latent bug class must not resurface
here); Source selection auto-populates `source_name`; existing Letter
detail/list views render unchanged for pre-existing rows with no
`designation_id`/no `source_department_id`.

## 19. Performance

**No new index beyond what §15 already specifies is needed** —
`designation_id`/`source_department_id` are both simple equality
lookups on small reference tables, the same query shape every other
Letter FK column already handles cheaply. **No caching is proposed** —
consistent with this project's own repeated conclusion (Phase 5F/5G)
that no reference-data or dashboard query in this system has
demonstrated a performance problem to solve. Department lookup is
directly reused (§5) — no duplicate lookup mechanism is introduced.

## 20. Terminology

**RECOMMENDED, adopted throughout this document and the eventual UI**:
"Source Department" (was "Source"/"Source name"), "Recipient
Department" (unchanged, already used consistently), "Sender's
Department" (unchanged — already labeled this way in the form), and
"Designation" (unchanged — already the term used everywhere in this
codebase, no ambiguity found). The label change from "Source" to
"Source Department" is the one terminology change this review
recommends, precisely because the field is changing from a description
of an organization to a specific Department selection, and the
existing three-department vocabulary on one screen (Source, Recipient,
Sender) needs the extra precision the moment "Source" stops being free
text.

---

## 21. Business clarifications (genuinely open, not manufactured)

* Should the Source dropdown ever offer a non-departmental "external
  source" path, given the already-confirmed "must never force every
  source into a department FK" decision? Not resolved here (§4).
* Should inactive source departments remain valid when *editing* a
  historical Letter that already references one (mirroring §9's
  designation answer)? `_validate_source_department` currently applies
  the identical "only re-validate on explicit change" rule already —
  this is likely already answered by existing behavior, but not
  explicitly reconfirmed by the business for this new UI context.
* Should SYSTEM_ADMIN be able to deactivate a Designation currently in
  use by Letters? Yes, per direct precedent (Category/Classification
  already allow this) — not itself in question, but worth the business
  hearing this is the existing system-wide policy, not a new one.
* Should designation names be globally unique, case-insensitively? This
  review recommends yes (§7); not independently confirmed by the
  business.
* Should Source Department be mandatory? Not confirmed — this review
  recommends leaving it optional, matching the pre-existing product
  decision (§4).
* Should Designation be mandatory? Not confirmed — this review
  recommends leaving it optional for tonight specifically because of
  the empty-seed-data risk (§16); revisit once real data exists.
* What should happen when no active designations exist — is an empty,
  unusable-until-populated dropdown acceptable at handover, or does
  the business want a manual fallback? Not confirmed; this review's
  own recommendation (§12) is the empty-placeholder behavior, made
  explicit rather than silently assumed.

## 22. MUST IMPLEMENT BEFORE HANDOVER vs. NICE TO HAVE / FUTURE

**MUST IMPLEMENT BEFORE HANDOVER**:
1. Relax `GET /api/v1/departments` to `get_current_user` (§5) —
   without this, Source Department cannot work for USER/ADMIN at all.
2. New `Designation` model/table, migration, repository, service,
   endpoints — `GET` reachable by all roles, every write SYSTEM_ADMIN-
   only (§7/§10/§11) — without the `GET` being broadly readable, the
   feature is equally broken (Finding 2, designation half).
3. New nullable `letters.designation_id` FK column (§8/§15) — no
   backfill, no risk to historical data.
4. `LetterService._validate_designation`, wired into create/update
   exactly like `_validate_category` (§9).
5. `LetterCreate`/`LetterUpdate`/`LetterResponse`/`LetterListItem`
   gain `designation_id`, kept optional (§14/§16).
6. `LetterFormPage.jsx`: Source Department selector (`DepartmentSelector`,
   auto-fills `source_name`) and Designation selector (a plain
   `<select>`, auto-fills nothing extra, sends `designation_id` +
   `sender_designation`) — §12/§13.
7. A minimal, single-page SYSTEM_ADMIN Designation management screen
   (create + list + activate/deactivate) — without this, SYSTEM_ADMIN
   has no way to populate the list at all (§12).
8. Label change "Source" → "Source Department" (§13/§20).

**NICE TO HAVE / FUTURE — explicitly not tonight**:
* A dedicated Designation detail/edit-name page (PATCH already
  supported by the API; just no UI route needed yet).
* An "external, non-departmental source" fallback for Source (§21).
* Making `source_department_id`/`designation_id` mandatory (§16/§21).
* A `source_department_id` search/filter on the Letter registry list.
* Any UI polish, typography, spacing, footer, or Phase 6 work — all
  explicitly out of this phase's scope per the brief's own §24/§25 and
  untouched by anything recommended above.

## 23. Implementation sequence (RECOMMENDED, tightly scoped for tonight)

1. **5H.1 — Designation database/model.** New table + migration, per
   §15.
2. **5H.2 — Designation repository/service/API.** Mirrors
   `CategoryRepository`/`CategoryService`/`categories.py` almost line
   for line; the one deliberate departure is the list endpoint's
   dependency (§11).
3. **5H.3 — `GET /departments` access relaxation.** A one-line
   dependency change (§5) — do this alongside 5H.2, since both are the
   same category of fix (a reference-data list becoming USER/ADMIN-
   readable) and are easiest to verify together.
4. **5H.4 — Letter schema/backend changes.** `designation_id` on the
   four Letter schemas, `_validate_designation`, wired into
   `create_letter`/`update_letter` (§9/§14).
5. **5H.5 — Minimal Designation management UI.** One SYSTEM_ADMIN page
   (§12) — needed before 5H.6 can be demoed end to end, since
   otherwise there is nothing to select.
6. **5H.6 — Letter frontend integration.** `LetterFormPage.jsx`'s
   Source and Designation fields (§12/§13).
7. **5H.7 — Security/regression tests.** Per §18, before calling this
   done.
8. **5H.8 — Manual E2E.** Recreate the supervisor's own demo path:
   SYSTEM_ADMIN adds a Designation, USER/ADMIN records a Letter
   selecting both a Source Department and a Designation, an existing
   pre-migration Letter still displays correctly.
9. **5H.9 — Commit/push checkpoint.**

---

## 24. Documentation (this phase's own footprint)

Created: `docs/architecture/source-designation.md` (this file).
Updated: `README.md`, `docs/README.md`, `docs/PROJECT_STATUS.md`,
`docs/architecture/overview.md` — recording that this review exists,
its two critical findings, and its MUST-IMPLEMENT list, matching the
documentation-only footprint every prior review-only phase has left.
`docs/architecture/letter-registry.md` and `docs/architecture/
frontend.md` are the two documents most directly touched by this
review's findings (Source's own field history, and the Category/
Classification access-gap precedent this review explicitly avoids
repeating) — both are cited above rather than duplicated or
contradicted, per the brief's own instruction to update carefully
rather than fork the narrative.

## 25. Explicit scope confirmation

This phase produced documentation only. It did **not** produce or
modify: any file under `backend/app/` or `backend/alembic/`, any file
under `frontend/src/`, any test file, any migration, any database
change, any dependency. It did not implement the Designation model,
repository, service, or endpoints; the `GET /departments` access
change; any `LetterFormPage.jsx` change; any SYSTEM_ADMIN Designation
management screen; or any UI polish/footer/Phase 6 work. `git status`
before and after this session is identical except for this new
documentation file and the four project documentation updates listed
in §24. Implementation begins only when explicitly instructed.

---

## 26. Implementation record — IMPLEMENTED

Built directly on §1-25's own design — no new architecture decisions,
only the ones already recommended (or, where §22 left something
genuinely open, an explicit choice made and recorded here, not
silently promoted to CONFIRMED).

### Designation backend resource (§7/§10/§11) — IMPLEMENTED

New `app/models/designation.py` — `id`/`name`/`status`/`created_at`/
`updated_at`, mirroring `Category` exactly, plus a case-insensitive
unique functional index (`uq_designations_name_lower`, the same
technique `uq_users_email_lower` already uses) rather than
Category/Classification's plain case-sensitive `unique=True`. New
`DesignationRepository`/`DesignationService` mirror `Category`'s own
modules almost line-for-line: race-safe duplicate handling via a caught
`IntegrityError` (never a pre-check), idempotent activate/deactivate,
never physically deleted. New `app/api/v1/endpoints/designations.py` —
`POST/GET/PATCH /designations`, `POST /designations/{id}/activate`,
`POST /designations/{id}/deactivate` (verb corrected to match this
codebase's real convention, not the brief's own illustrative `PATCH`
guess). **The one deliberate departure from Category/Classification,
verified directly**: `GET /designations` depends on `get_current_user`
— every authenticated role — not `require_system_admin`; every write
endpoint and `GET /{id}` remain SYSTEM_ADMIN-only, confirmed by reading
each endpoint's own `Depends(...)` line after implementation, not
assumed.

### `GET /departments` access relaxation (§5) — IMPLEMENTED, minimal

One dependency changed, in `app/api/v1/endpoints/departments.py`:
`list_departments` now depends on `get_current_user`. Every other
Department endpoint (`create`/`update`/single-`get`/`activate`/
`deactivate`) is unchanged, confirmed by re-reading the file after the
edit. No new query parameter, no new response field, no change to
`DepartmentService`/`DepartmentRepository` at all.

### Letter schema/backend integration (§8/§9/§14) — IMPLEMENTED

`letters.designation_id` — new, nullable FK (`ondelete=RESTRICT`,
indexed), added via migration `323ccfde77f4_designation_master_data`
(down-revision `9fa970ffa560`, the confirmed prior head). `sender_designation`
is completely unchanged — still required text, still the field every
existing Letter and every old API client already depends on.
`LetterCreate`/`LetterUpdate`/`LetterResponse`/`LetterListItem` all
gain `designation_id: Optional[uuid.UUID]`, coexisting with
`sender_designation`, exactly mirroring how `source_department_id`/
`source_name` already coexist. `LetterService` gains
`_resolve_designation` (mirrors `_validate_category`'s shape, but
returns the row so its current `name` can be copied into
`sender_designation` — "the master-data selection is authoritative,
never the client's own text," implemented literally: the service
overrides whatever `sender_designation` string the client sent
whenever a `designation_id` is being newly assigned). Audit trail gains
`LETTER_DESIGNATION_CHANGED`, mirroring `LETTER_CATEGORY_CHANGED`
exactly.

**One deliberate refinement beyond `_validate_category`'s own
behavior, implemented exactly as the brief specified**: on update, a
*resent-but-unchanged* `designation_id` (equal to the Letter's current
value) is never re-validated, even if that designation has since gone
`INACTIVE` — only an actual *change* to a different `designation_id`
requires the new one to be `ACTIVE`. This is what makes "editing an
unrelated field on a Letter whose designation later went inactive"
safe, verified directly by test
(`test_resending_unchanged_now_inactive_designation_does_not_invalidate_edit`).

### Source Department validation (§5/§6/§10) — CONFIRMED unchanged

`_validate_source_department`/`assert_letter_access`/
`assert_department_access`/`letter_visibility_filter` were not
modified in any way — re-read fresh after every other change to
confirm this. `source_department_id` still has no role in
authorization anywhere; `recipient_department_id` remains the sole
isolation boundary, verified directly by a new test
(`test_source_department_id_never_expands_letter_authorization`) that
records a Letter with a *different* department as its Source and
confirms a user in that Source department still cannot see it.

### Migration (§15) — IMPLEMENTED, verified against a real database

`323ccfde77f4_designation_master_data` — one new table, one new
nullable FK column, zero backfill. **Verified for real, not merely
written**: `alembic upgrade head` → `alembic downgrade 9fa970ffa560` →
`alembic upgrade head` → `alembic check` against a real local
PostgreSQL `lrs_dev` instance — clean at every step, `alembic check`
reporting "No new upgrade operations detected" after the full cycle.

### Frontend — Source Department (§13) — IMPLEMENTED

`LetterFormPage.jsx`'s free-text "Source name" input is replaced with
the existing `DepartmentSelector`, bound to `source_department_id`.
Selecting a department auto-fills `source_name`. Labeled "Source
Department" (§20). **Required only on create** — `utils/
formValidation.js`'s `validateLetterForm` gained an `{isEdit}` option
specifically so editing a Letter that predates this phase (and
legitimately has no Source Department) is never blocked over an
unrelated edit; verified by test.

### Frontend — Designation (§12) — IMPLEMENTED

The free-text "Sender designation" input is replaced with a `<select>`
bound to a new `designation_id` field; selecting one auto-fills
`sender_designation` client-side (the backend remains authoritative
and overrides it server-side regardless). **On create**, only `ACTIVE`
designations load (`?status=ACTIVE`); **on edit**, the complete
(active + inactive) list loads instead, so a Letter's already-assigned,
possibly-now-inactive designation still renders and is visibly
labeled `(inactive)` — mirroring the existing Category/Classification
inactive-injection pattern in this same file. **Zero-designations
state**: a clear message renders ("No designations are available
yet..."), never a fake option, and — per an explicit, deliberate
decision this record does not silently soften — submission is
correctly blocked by the same required-on-create validation, matching
the brief's own repeated instruction not to invent a workaround for the
system's intentional empty starting state.

### SYSTEM_ADMIN Designation management UI (§12) — IMPLEMENTED, minimal

One page, `/app/system/designations` (`DesignationListPage.jsx`) —
inline create form, status filter, list, Activate (direct, no
confirmation — a purely restorative action, matching Department's own
confirmation-matrix precedent) and Deactivate (behind a
`ConfirmDialog`, `tone="caution"`, stating explicitly that existing
Letters keep their designation unchanged). No delete action anywhere.
No dedicated detail/edit page — deliberately, per the brief's own "do
not overbuild" instruction; `PATCH /designations/{id}` exists on the
backend with no UI yet (§21, a real, disclosed limitation, not an
oversight).

### Tests (§18) — IMPLEMENTED

**Backend**: 29 new tests — a new `tests/integration/
test_designation_management.py` (16: SYSTEM_ADMIN/ADMIN/USER
list/create/activate/deactivate authorization, case-insensitive
duplicate rejection, idempotent activate/deactivate, no physical
delete endpoint), plus Letter/Source/Designation integration tests
added to `tests/integration/test_letter_registry.py` and
department-list-access tests added to `tests/integration/
test_department_management.py`. Backend total: **487 passed**
(458 baseline + 29), run 3 consecutive times with identical results.
**Frontend**: 22 net new tests — `pages/DesignationListPage.test.jsx`
(new), `pages/LetterFormPage.test.jsx` extended substantially,
`utils/formValidation.test.js`/`navigation/navigationConfig.test.js`
extended. Frontend total: **280 passed** (258 baseline + 22), run 3
consecutive times with identical results.

**One test-infrastructure issue found and fixed, not a logic
defect**: the initial `fillRequiredFields()` test helper in
`LetterFormPage.test.jsx` didn't wait for the new async department/
designation load before interacting with the form — fixed by awaiting
the first field via `findByLabelText` instead of a synchronous
`getByLabelText`, matching this project's own established async-test
convention elsewhere.

### Security review (§17, verified this phase, not merely designed)

Grepped every new/changed file for `jwt`/`decode`/`localStorage`/
hardcoded department ids/hardcoded designation names/`source_department_id`-
as-authorization/client-controlled `role`/`DELETE`-on-designation/
physical-deletion. Every match found is a comment documenting the
pattern's *absence* — zero matches represent actual usage. Additionally
verified, by reading the actual `Depends(...)` line on every single
endpoint in `designations.py` and `departments.py` after
implementation: exactly one `get_current_user` dependency in each file
(the two list endpoints), every other endpoint `require_system_admin`,
matching the design exactly.

### Build / regression — IMPLEMENTED, verified

`npm run build` succeeds (187 modules, no errors). `npm run test` —
**280 passed**, 0 failed, run 3 consecutive times. `pytest tests/` —
**487 passed**, 0 failed, run 3 consecutive times. `alembic upgrade
head` → `downgrade` → `upgrade head` → `check` — clean, zero drift,
against a real local PostgreSQL instance. `git status` confirms no
file outside the explicit implementation scope (§Implementation
Scope of the brief) was touched.

### Manual/live verification — NOT PERFORMED beyond the real database migration cycle

The Alembic upgrade/downgrade/upgrade/check cycle above ran against a
real local PostgreSQL `lrs_dev` instance — that part is genuinely live,
not simulated. **No running backend server or frontend dev server was
started, and no browser-based click-through of the actual demo path
(SYSTEM_ADMIN adds a Designation → USER records a Letter selecting a
Source Department and Designation) was performed.** Reported honestly
per the brief's own instruction, rather than claimed.

### Remaining business clarifications (§21, unchanged, not resolved by implementation)

Whether an external/non-departmental Source fallback is still needed;
whether Source Department/Designation should ever become backend-
mandatory; whether designation names should be considered globally
unique across some other, currently-unconsidered scope. None of these
were decided here — the implementation matches exactly what §22's
MUST-IMPLEMENT list specified, no more.
