# Correspondence Direction, Diary Number & Letter Continuation

**Phase 6A.** Status markers used throughout this document:

- **IMPLEMENTED** — built and tested this phase.
- **CONFIRMED** — verified directly against the actual codebase (not assumed).
- **PENDING BUSINESS CLARIFICATION** — a genuine open question; the safest, backward-compatible default was chosen and is documented as a default, not silently promoted to a requirement.
- **FUTURE** — deliberately out of scope, not forgotten.

## 1. Context

Before this phase, every `Letter` implicitly represented one thing: correspondence that arrived at the recording department and was entered into that department's own registry. `recipient_department_id` — the field `assert_letter_access` checks — is always the *recorder's own* department (`app/services/letter_service.py:create_letter` derives it from `recorder.department_id`, never a client-suppliable destination). There was no way for one department to record correspondence addressed to *another* department, and no relationship between two departments' otherwise-identical records of the same real-world letter.

The supervisor's request: Finance sends a letter to S&IT. Finance records it as **Outgoing/Dispatch**; S&IT is notified, records the same correspondence as **Incoming/Diary** with one click (no re-entry), Finance is notified again once S&IT has recorded it, and if S&IT responds, the reply is traceably linked back to the original — all without inventing a separate correspondence subsystem, and without touching any existing security boundary.

## 2. Correspondence direction — IMPLEMENTED

`Letter.direction` (`LetterDirection`: `INCOMING` | `OUTGOING`), `NOT NULL`, `server_default 'INCOMING'`.

Every letter recorded before this phase already *was* `INCOMING` in the sense above — the migration's default applies that true, unchanged fact to every historical row; it is not a guessed backfill (§8).

**`recipient_department_id`'s meaning is deliberately unchanged for both directions** — it remains "the department that owns/can see this row," exactly as before:

- `INCOMING`: the receiving department (as always).
- `OUTGOING`: the *dispatching* department — Finance owns and sees its own outgoing record in its own registry, exactly the way it already owned every letter it ever recorded.

This is the single design decision that let every existing authorization function (`assert_letter_access`, `letter_visibility_filter`, `assert_department_access`) go completely untouched (§7). The actual destination for an `OUTGOING` letter is a new, separate field:

`Letter.dispatch_department_id` — nullable FK to `departments`, `RESTRICT`. Required (service-validated) exactly when `direction == OUTGOING`; forbidden when `INCOMING`. Distinct from `source_department_id` (optional, no authorization meaning, describes an external sender who may not even be an LRS department) and from `recipient_department_id` (ownership).

Self-dispatch (`dispatch_department_id == recorder.department_id`) is rejected — a conservative, documented validation choice, not verbatim-requested but reversible; see §6.

## 3. Diary Number — IMPLEMENTED, with defaults documented per the brief's own ten questions

**Q1/Q2 (from actual code, not assumed): is `reference_number` the unique identity of a Letter? No.** `reference_number` has never had a uniqueness constraint (removed by migration `c887ab35e4a3`, a Phase 4B hardening finding) — the business confirmed reference numbers "must be unique" but never confirmed the scope, and this remains **PENDING BUSINESS CLARIFICATION**, untouched by this phase (`docs/architecture/letter-registry.md` §2.3/§12). The supervisor's own statement that "the same letter content may occur more than once" is additional, independent confirmation that `reference_number` was never meant to be a unique key.

**Q3: should Diary Number be the operationally prominent identifier? Yes** — `diary_number` is now shown alongside `reference_number` in the registry table and the Letter detail page (never replacing it).

**Q5 (date vs. generation): the supervisor's statement describes how the number is *generated* (associated with the dispatch/receipt date), not that the date itself *is* the number.** A calendar date is not a safe database identifier on its own — multiple letters share a date. Rather than inventing a new `dispatched_at` column duplicating the existing `received_at` (the brief's own "do not duplicate fields" instruction), `received_at` is reused for both directions: the date this correspondence record pertains to — received, for `INCOMING`; dispatched, for `OUTGOING`. `diary_number` is a separate, purely sequential identifier, generated at creation time.

**Q4: uniqueness scope — department + direction, not global, not date/year-scoped.** Every other resource in this schema (Letters, notifications) is already department-isolated; a real diary register is kept independently per office. `LetterNumberSequence` (`department_id, direction` composite key, one row per pair, created lazily) backs a plain, perpetually incrementing counter — allocated under `SELECT ... FOR UPDATE` (the same row-locking technique `app/repositories/user_authorization_repository.py` already uses), so two concurrent creations in the same department/direction can never collide. No prefix or zero-padding was invented; the stored value is the bare sequence number as text (e.g. `"1"`, `"2"`) — display-layer framing ("Diary #4" / "Dispatch #4") is a presentation choice, not a stored format.

**An annual/monthly reset cadence was never confirmed — PENDING BUSINESS CLARIFICATION / FUTURE.** The counter never resets. If the business later confirms an annual reset, it changes only `LetterNumberSequence`'s own shape (e.g. adding a `year` column) and the one allocation method — no other code depends on the current perpetual behavior.

**Q10: historical letters get `diary_number = NULL`, never backfilled** — there is no true historical diary number to recover, and inventing one would fabricate a business fact (§8).

## 4. The "Record" action — IMPLEMENTED

`POST /api/v1/letters/{outgoing_letter_id}/record` (`require_user_or_admin` — SYSTEM_ADMIN has no department to record into, mirroring `POST /letters` itself).

1. Loads the outgoing letter by id (plain lookup, **not** `assert_letter_access` — see §7 for why that check is the wrong question here).
2. `assert_dispatch_recipient_access` (new, additive function) verifies `letter.direction == OUTGOING` and `letter.dispatch_department_id == caller.department_id` (plus the caller's own department must be `ACTIVE`) — independently re-verified server-side on every call, never inferred from the fact that a notification exists (§7's own explicit instruction).
3. **Q6 (reuse the original's fields): yes, copied verbatim** — `reference_number`, `subject`, `sender_name`, `sender_designation`, `designation_id`, `sender_department`, `sender_address`, `source_name`, `source_department_id`, `source_location`, `reason`, `category_id`, `classification_id`, `received_at`, `text_content` are all copied from the outgoing letter as-is. The recipient never re-enters anything (the brief's own explicit requirement). `source_name`/`source_department_id` are copied unchanged, not overwritten with the dispatching department's identity — whatever the dispatching department recorded as the correspondence's true origin remains true regardless of who now holds a copy of it.
4. **Q8 (one outgoing → one incoming): enforced at the database level**, not just in application logic — `Letter.recorded_from_letter_id` (self-referential FK) carries a **partial unique index** (`WHERE recorded_from_letter_id IS NOT NULL`). Step 6's duplicate-protection requirement is therefore a real constraint, not a convention: a race between two simultaneous "Record" clicks is caught by an `IntegrityError` on the losing request, which then re-queries and returns the winner's row instead of erroring.
5. **Idempotent.** A repeat call for an already-recorded outgoing letter returns the existing incoming letter unchanged — `200 OK`. The first, letter-creating call returns `201 Created`. Never a duplicate row, never a client-visible error for the repeat case.

## 5. Continuation / response — IMPLEMENTED

**Q9: a response is a new, separate Letter, linked to the original — the original is never overwritten.** `Letter.continuation_of_letter_id` (self-referential FK, plain index, **not** unique — a department may send more than one follow-up referencing the same original).

Deliberately a *different* field from `recorded_from_letter_id`, not an overloaded single "parent" column — the two relationships have different cardinality rules (recorded-from is at-most-one; continuation-of is unbounded) and different meanings (an automatic system-derived copy vs. a deliberate human response). Conflating them into one column would have made the unique-index-based duplicate-protection guarantee in §4 ambiguous.

A continuation is created through the *existing* `POST /letters` endpoint with `continuation_of_letter_id` set — not a separate action endpoint (see §10 for why). The referenced letter must be one the caller can already access (`LetterService._get_for_access`, the same check every other single-resource read/write in this service already reuses) — which, combined with `recipient_department_id`'s own unchanged meaning, means a continuation can only ever reference a letter within the caller's own department (or, for SYSTEM_ADMIN, anywhere it can already see).

## 6. Business decisions made from existing evidence (not silently invented)

| Question | Decision | Basis |
|---|---|---|
| Q1/Q2 | `reference_number` is not unique, never was; diary_number is a separate identifier | Existing code + migration `c887ab35e4a3`; supervisor's own statement |
| Q3 | Diary Number shown prominently in UI, `reference_number` unchanged | Supervisor's explicit request |
| Q4 | Unique per `(department_id, direction)`, perpetual counter | Every other resource here is department-scoped; no reset cadence confirmed |
| Q5 | Diary Number's *generation* is date-associated (`received_at`); the number itself is a sequence | Explicit instruction not to use a bare calendar date as an identifier |
| Q6 | Incoming record copies the outgoing letter's fields verbatim | Explicit "no manual re-entry" instruction |
| Q7 | One outgoing letter = one dispatch destination department | No multi-recipient precedent anywhere in this schema; avoids inventing one |
| Q8 | Enforced via a partial unique index on `recorded_from_letter_id` | Explicit "server-side, not just frontend" duplicate-protection instruction |
| Q9 | Continuation is a new Letter with `continuation_of_letter_id`, never an overwrite | Explicit instruction |
| Q10 | Historical letters: `direction = INCOMING` (server default), `diary_number = NULL`, never backfilled | "Do not backfill unless absolutely necessary" |

**PENDING BUSINESS CLARIFICATION / FUTURE, explicitly not decided here:**

- Whether Diary Number generation should reset annually/monthly.
- Whether one outgoing letter should ever be dispatchable to more than one department (today: create one outgoing letter per destination).
- The exact final `reference_number` uniqueness scope (unchanged, still open since Phase 4B).
- Self-dispatch is currently rejected as a conservative validation guard — not verbatim requested, easily reversible if the business wants to allow it.

## 7. Authorization model — CONFIRMED unchanged where it matters, one new additive check

**Nothing about the existing security boundary was touched:**

- `assert_letter_access`, `letter_visibility_filter`, `assert_department_access` — byte-for-byte unchanged. `recipient_department_id` remains the one and only ownership/visibility boundary for every Letter, `OUTGOING` or `INCOMING` alike.
- No `department_id` from the frontend is ever trusted as an authorization decision — `dispatch_department_id` is validated against a real, `ACTIVE` `Department` row server-side; the caller cannot choose an unauthorized *recipient* of their own letter's visibility, only its dispatch *destination*, which is a different, narrower question (§4).
- No classification-based UI authorization was added; no `recipient_user_id` is ever exposed to the frontend (`Notification` schema unchanged); no document storage path or signed/public URL is touched by any of this; no Delete/Replace document action exists; `assert_letter_access` is never bypassed anywhere in this feature.

**One new, additive function**: `assert_dispatch_recipient_access(user, letter)` (`app/services/authorization.py`) — answers a genuinely different question ("may this department record *this* outgoing letter as their own") than `assert_letter_access` does ("can this user see this letter in their own registry"). The "Record" action independently re-verifies this relationship server-side on every call — it never infers authorization from the mere existence of a notification, per the brief's own explicit instruction.

**A real bug found and fixed during this phase's own testing**: the first draft of `notify_correspondence_recorded` linked the receipt-confirmation notification to the newly created *incoming* letter — which the *notification's own recipient* (the dispatching department) cannot open (`assert_letter_access` would 404 it, since they don't own it). Fixed to link to the *outgoing* letter instead, which that department already owns. A notification must never point its own recipient at a letter that recipient can't access — this is now a named regression test (`test_receipt_confirmation_notification_links_to_a_letter_the_recipient_can_open`). The same reasoning is why `LETTER_DISPATCHED`'s own `letter_id` (the outgoing letter, inaccessible to the *dispatch* department until they Record it) is handled specially in the frontend (§9) rather than rendered as a normal navigation link.

## 8. Backward compatibility — CONFIRMED

Migration `7f3b2d9c4a1e` (`correspondence direction, diary number, dispatch/continuation links`), upgrade → downgrade → upgrade verified against the real dev database, `alembic check` reports zero drift. All five new `letters` columns are nullable or server-defaulted; the new `letter_number_sequences` table is created lazily per department, never pre-seeded. No existing column was renamed, narrowed, or backfilled with invented data. `reference_number`, `sender_designation`, `source_name`, `source_department_id`, `designation_id`, classification, documents, and notifications all continue functioning exactly as before — every pre-existing backend test (487) and frontend test (364, pre-Phase-6A count) passes unmodified except one hardcoded table-name list (`test_imports.py`) which necessarily grew to include the one new table.

## 9. Frontend — IMPLEMENTED

- `LetterFormPage.jsx`: a new, **create-only** "Correspondence direction" fieldset (Incoming/Diary vs. Outgoing/Dispatch); selecting Outgoing reveals a "Dispatch to Department" selector (reusing `DepartmentSelector`, the recorder's own department excluded from the option list as a UX nicety — the server independently rejects self-dispatch regardless). `direction`/`dispatch_department_id`/`continuation_of_letter_id` are never sent on edit — there is no field for any of them on `LetterUpdate`.
- `LetterDetailPage.jsx`: a "Correspondence Direction" section — Direction, Diary/Dispatch Number, and, when set, "Received via dispatch from" (plain text, derived from this letter's own already-copied `source_name` — **never** a link to the originating outgoing letter, which this department cannot open) and "Continuation of" (a real, working link — always safe, since a continuation only ever references a letter within the caller's own department). A "Create response" button (shown only for `INCOMING` letters) navigates to the create form with `continuationOfLetterId`/`continuationOfReference` carried via router `state`, never a query string.
- `NotificationItem.jsx`: the one type-specific branch in an otherwise type-agnostic component — `LETTER_DISPATCHED` notifications render a `Record` button instead of a Letter link (that notification's own `letter_id` is the inaccessible outgoing letter — see §7); on success, the row shows a real link to the newly recorded (or already-existing) incoming letter.
- `LetterTable.jsx`/`LetterFilters.jsx`: a Direction badge and Diary/Dispatch Number column (always rendered, `—` for historical letters); a Direction filter, following the same real-`GET`-parameter convention every other filter here already uses.

## 10. API design — resource-oriented, one genuine new action

Router → Service → Repository → Schema, unchanged layering.

- **Extended, not duplicated**: `POST /letters` now accepts `direction`/`dispatch_department_id`/`continuation_of_letter_id`, all optional/defaulted — recording an outgoing letter or a continuation is not a structurally different operation from recording any other letter, so it does not get its own endpoint.
- **One new action endpoint**: `POST /letters/{id}/record` — a genuine, distinct domain operation (cross-department target verification, field auto-derivation, idempotent duplicate protection) that does not fit the plain-CRUD shape at all.
- **Considered and deliberately not built as separate endpoints**: "create continuation" (folds into the existing create endpoint, §5) and "acknowledge receipt" (happens automatically as a side effect of "Record" — §4 — never a manual action a user clicks, since the brief's own Step 4 describes it as automatic).
- No page-shaped route (`/dashboard/...` or similar) was introduced.

## 11. Notifications — IMPLEMENTED, reusing the existing architecture exactly

Two new best-effort triggers on `NotificationService`, both following the exact SAVEPOINT-wrapped, never-raises, "recipient department's ACTIVE Admins" pattern `notify_letter_registered` already established (Phase 4E) — no new authorization mechanism, no new recipient-selection strategy:

- `notify_letter_dispatched(letter)` — fires when an `OUTGOING` letter is created; recipients are the **dispatch** department's Admins (not the recording department's, which still gets the existing, unchanged `notify_letter_registered`).
- `notify_correspondence_recorded(outgoing_letter, incoming_letter)` — fires when "Record" succeeds; recipients are the **originating** (dispatching) department's Admins. Links to `outgoing_letter.id`, not `incoming_letter.id` — see §7's bug note.

Message text remains generic (a reference number and a department name — never subject, sender detail, content, or classification), matching the existing message-security discipline exactly.

## 12. Tests

Backend: `tests/integration/test_correspondence.py` (23 tests) — outgoing/incoming creation, every dispatch-department validation error, the full Record lifecycle (creation, field-copying, idempotency, cross-department rejection, rejection of an already-incoming target), the receipt-confirmation notification (including the §7 bug regression), continuation creation and its own access check, Diary Number independence across departments and across directions within one department, and SYSTEM_ADMIN's exclusion from both `POST /letters` and `POST /letters/{id}/record`. Full suite: 510 passed (487 pre-existing + 23 new), one pre-existing test's hardcoded table list updated for the one new table.

Frontend: new tests in `LetterFormPage.test.jsx` (direction default/selection, dispatch-department requirement and exclusion of the recorder's own department, continuation pre-fill via navigation state, and confirmation that none of the three new fields are ever sent on edit), `LetterDetailPage.test.jsx` (direction/diary display, the plain-text vs. real-link distinction from §7/§9, "Create response" navigation), `NotificationItem.test.jsx` (Record button rendering, loading/success/error states, availability regardless of read status), and `LetterTable.test.jsx` (direction badge and diary number columns). Full suite: 382 passed (364 pre-existing + 18 new), run 3 consecutive times with identical results.

## 13. Manual E2E verification

**Not performed** — no browser-automation tool is available in this environment, consistent with every visual phase since 5I.6. Every claim in this document is backed by the automated test suites in §12, not by observing the running application.

## 14. Update, Phase 6C — `direction`/`dispatch_department_id` reused by the new aggregate API

`GET /api/v1/letters/aggregate` (`docs/architecture/dashboard-analytics-api.md`'s own "Phase 6C" section) reuses `direction` as both a filter and a `group_by` dimension, and `dispatch_department_id` as both a filter and a new `group_by=dispatch_department` dimension — answering "which departments are receiving correspondence via dispatch," a question this phase's own `department` dimension (still `recipient_department_id`, unchanged) cannot answer alone. `diary_number`, `recorded_from_letter_id`, and `continuation_of_letter_id` were deliberately **not** exposed as aggregate dimensions — none is a meaningful grouping value. No field, model, migration, or authorization rule described in §1-§13 above was changed by that phase.
