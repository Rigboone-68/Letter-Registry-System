# Authentication — Phase 3A

**Status: complete.** This document describes the authentication foundation
and account lifecycle implemented in Phase 3A. It does not cover
role/department authorization decisions (Phase 3B — see "Deferred to Phase
3B" below).

**No external OAuth provider is used. Authentication is local to the
deployment.** LRS runs on a private government intranet and authenticates
entirely on its own — there is no dependency on Google, Microsoft, or any
other internet-based identity service, by design (see root `README.md`,
"Development philosophy").

---

## 1. Architecture

```text
FastAPI endpoint (app/api/v1/endpoints/auth.py)
        ↓ translates service exceptions to HTTP responses
Service (app/services/auth_service.py, bootstrap_service.py)
        ↓ owns business rules and transaction boundaries
Repository (app/repositories/user_repository.py, user_authorization_repository.py)
        ↓ the only layer that queries the database
SQLAlchemy models (Phase 2) → PostgreSQL
```

This follows the layering already established in Phase 1/2
(`docs/architecture/overview.md` §5) rather than introducing a second
pattern: endpoints stay thin, services hold policy, repositories hold
queries. Password hashing and JWT handling live in one place,
`app/core/security.py`, matching the placeholder role that module was
given in Phase 1.

## 2. Password hashing

**Argon2id**, via `argon2-cffi`'s `PasswordHasher` used directly (not
through `passlib`, whose argon2 backend has a history of version-pinning
friction with `argon2-cffi` itself — using the library directly avoids that
indirection layer entirely). `argon2-cffi`'s default hasher profile is
Argon2id, the variant the brief requested.

* `app/core/security.py:hash_password` — hashes; the result is safe to
  store, the input never is.
* `app/core/security.py:verify_password` — verifies *through the library*
  (`PasswordHasher.verify`), never a manual string/hash comparison. Catches
  `VerifyMismatchError`/`InvalidHash` and returns `False` rather than
  letting either propagate, so callers have one boolean to check.
* Hashing is salted and non-deterministic by construction — two hashes of
  the same password differ (see
  `tests/unit/test_security.py::test_hash_password_is_salted_and_nondeterministic`).

**Password policy** (brief §6) — minimum 8 characters, maximum 128,
non-empty — is centralized in exactly one function,
`app/core/security.py:validate_password_policy`, called from exactly two
places: `SignupRequest`'s Pydantic validator (`app/schemas/auth.py`) and
the bootstrap service (`app/services/bootstrap_service.py`). Login never
validates password *policy* — an existing password that predates a policy
change should still work for login; policy is only enforced when a
password is being *set*.

## 3. JWT design

**PyJWT**, not the `python-jose` placeholder informally sketched in
`requirements.txt` before this phase — python-jose has had an
algorithm-confusion vulnerability (CVE-2024-33663) and slower maintenance;
PyJWT is actively maintained. Only **HS256** (symmetric, `SECRET_KEY`-based)
is used, and `decode_access_token` always passes `algorithms=[settings.ALGORITHM]`
explicitly — the token's own header is never trusted to select the
algorithm, which is what prevents algorithm-confusion attacks in the first
place (see `tests/unit/test_security.py::test_decode_access_token_rejects_alg_none_token`).

**Payload** (brief §4):

```json
{
  "sub": "<user UUID>",
  "role": "<UserRole value>",
  "department_id": "<department UUID, or null for SYSTEM_ADMIN>",
  "iat": 1699999999,
  "exp": 1700003599
}
```

Nothing else. No password, no password hash, no full name, no email — only
what a future authorization check (Phase 3B) needs to make a decision
without a database round trip, plus the standard timing claims.

**Token lifecycle**: issued by `POST /api/v1/auth/login` on successful
authentication, valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60,
environment-configurable), and carries no server-side state — there is no
token table, no revocation list, and no refresh-token mechanism in this
phase (see "Deferred to Phase 3B"). This means:

* A token cannot be individually revoked before it expires. Deactivating a
  User's *account* still takes effect immediately, because
  `get_current_user` (`app/api/deps.py`) re-checks the user's status
  against the database on every request rather than trusting the token's
  claims — but the token itself remains cryptographically valid until
  `exp`, it simply stops being *useful* the moment the account it names is
  no longer ACTIVE.
* Rotating `SECRET_KEY` invalidates every outstanding token at once
  (documented in `.env.example`).

**`SECRET_KEY` is never read at import time** — `app/core/security.py`
checks it lazily, the first time a token is actually created or decoded
(mirroring the existing lazy-check pattern for `DATABASE_URL` in
`app/database/session.py:get_engine`), and raises a clear `RuntimeError` if
it's unset. This means `/health` and any non-auth code path still work in
an environment where `SECRET_KEY` hasn't been configured yet.

## 4. Account statuses (brief §7)

| Status | Can log in? | Notes |
|---|---|---|
| `PENDING_APPROVAL` | No | Default status for a freshly signed-up user. `POST /auth/login` returns `403` with a message distinguishing this from a wrong password (see §6, "Ordering"). |
| `ACTIVE` | Yes | The only status a JWT is issued for. |
| `DEACTIVATED` | No | Never a physical delete — see Phase 2's schema docs. `POST /auth/login` returns `403`. An *existing* token for a user who is deactivated after the token was issued also stops working, on the very next request — see §3. |

## 5. Signup workflow (brief §10-13)

```text
Admin pre-authorizes an email (UserAuthorization, status=ACTIVE)
        ↓
POST /api/v1/auth/signup  {full_name, email, password, password_confirm}
        ↓
AuthService.signup:
  1. normalize_email(email)
  2. find_and_lock_active(email)   -- SELECT ... FOR UPDATE, see §7
       not found/expired/revoked/used → SignupNotAuthorizedError (403)
  3. mark the locked authorization USED
  4. create User: role=USER, department_id=<from authorization>,
     status=PENDING_APPROVAL, password_hash=hash_password(password)
  5. flush; a unique-email violation → rollback (un-consumes the
     authorization) → DuplicateEmailError (409)
  6. commit
        ↓
201 Created — the new User's public profile (PENDING_APPROVAL)
```

**`role`, `department_id`, and `status` cannot be supplied by the
caller** — not merely ignored if sent. `SignupRequest`
(`app/schemas/auth.py`) has no fields for them, and additionally sets
`model_config = ConfigDict(extra="forbid")`, so a request that tries to
inject any of them (even a field FastAPI doesn't recognize) is rejected
outright with `422` before it ever reaches the service layer — see
`tests/integration/test_auth_signup.py::test_signup_grants_user_role_regardless_of_input`
and its two siblings, which assert both the `422` and that no row was
created.

## 6. Login workflow (brief §14)

Order matters and is deliberate:

1. Normalize email.
2. Look up the user (case-insensitively).
3. Verify the password.
4. **Only then** check account status.

Verifying the password *before* checking status means a wrong password
never reveals whether an account is pending or deactivated — only a
*correct* password does, and someone who already knows the correct
password has already cleared a much higher bar than guessing an email
exists. Unknown-email and wrong-password responses are additionally
**byte-identical** (`tests/integration/test_auth_login.py::test_login_unknown_email_and_wrong_password_return_identical_response`),
including a constant-time-ish mitigation: a lookup miss still runs one
Argon2 verification against a precomputed dummy hash
(`app/services/auth_service.py:_DUMMY_PASSWORD_HASH`) before returning,
so the response doesn't take measurably less time than a real failed
login — otherwise the timing difference is its own account-enumeration
channel. `PENDING_APPROVAL`/`DEACTIVATED` responses, by contrast, *are*
distinguishable from each other and from generic "invalid credentials" —
that tradeoff is deliberate and scoped narrowly to accounts whose password
was already proven correct (see §7 error-handling table).

## 7. UserAuthorization consumption is race-safe (brief §13)

`app/repositories/user_authorization_repository.py:find_and_lock_active`
selects the oldest matching, unexpired, `ACTIVE` authorization with
`SELECT ... FOR UPDATE`, taking a row lock inside the caller's transaction.
A second, concurrent signup attempt for the same email blocks on that lock
until the first transaction commits or rolls back, then re-evaluates the
same `WHERE` clause — finding either nothing (already consumed) or a
*different* row (if, unusually, more than one active authorization exists
for that email). This is why the service does **not** do a plain "check
`status == ACTIVE`, then a separate `UPDATE`" — the check and the lock
happen together, atomically, in one statement, exactly as the brief
requires.

Proven, not just argued: `tests/integration/test_auth_signup.py::test_concurrent_signup_attempts_consume_authorization_exactly_once`
fires two real threads with two independent database connections at the
same authorization simultaneously and asserts exactly one succeeds and
exactly one `User` row is created.

## 8. Bootstrap System Admin (brief §8-9)

```text
python -m app.cli create-system-admin
```

CLI-only — **there is no HTTP endpoint for this operation**, and that's
deliberate (`app/services/bootstrap_service.py` docstring): the first
System Admin can't come through public signup (there's no admin yet to
authorize them via `UserAuthorization`), and an HTTP endpoint for "create a
privileged account" is a meaningfully larger attack surface than a command
that only runs on the server, once, by whoever already has shell access to
it. `app/cli.py` only gathers input (`input()` for name/email, `getpass.getpass()`
for the two password prompts — masked, never echoed, and never accepted as
a command-line argument, so it never appears in shell history or a process
listing) and prints output; `app/services/bootstrap_service.py:create_system_admin`
holds the actual logic and is what the test suite calls directly.

The command refuses to run if an **active** `SYSTEM_ADMIN` already exists
(`SystemAdminAlreadyExistsError`, checked before anything else). No
row-locking beyond a single transaction — unlike signup, this is a rare,
deliberate, operator-run action, not a concurrent-request-prone endpoint;
the brief's race-condition requirement is scoped to signup.

Produces: `role=SYSTEM_ADMIN`, `department_id=NULL`, `status=ACTIVE`,
password hashed the same way as everywhere else in this codebase.

## 9. System Admin handover — deferred

The brief is explicit that the handover workflow (an existing System Admin
transferring authority to another account) is **out of scope for Phase
3A**. `app/cli.py`'s refusal message points at this document as the
authoritative note that it's coming in the RBAC/administration phase, not
implemented here. There is no code path in this phase that lets a System
Admin be created, promoted, or demoted other than the one-time bootstrap
above.

## 10. Security considerations

* **No plaintext password is ever stored, logged, or returned.**
  `UserPublic` (`app/schemas/auth.py`) has no `password_hash` field — not a
  field excluded at serialization time, which a future edit could silently
  un-exclude, but a field that structurally does not exist on the response
  model at all.
* **No account enumeration via login.** See §6.
* **No self-selected role/department/status at signup.** See §5.
* **JWT algorithm confusion is not possible.** See §3.
* **JWT tampering is rejected.** Any change to the signed payload
  invalidates the signature; PyJWT's verification catches this before the
  payload is ever trusted (`tests/unit/test_security.py::test_decode_access_token_rejects_tampered_signature`).
* **Deactivation takes effect immediately**, not at next token expiry. See
  §3, §4.
* **Bootstrap cannot run twice.** See §8.
* **Secrets never appear in source, docs, `.env.example`, or tests.**
  `.env.example` ships placeholder text only; the real `.env` stays local
  and gitignored (unchanged from Phase 1/2). Every test password used in
  this test suite (e.g. `"correct horse battery staple"`) is a throwaway
  value scoped to a disposable local test database, never a real secret.

### Security review performed

Every item in the brief's §29 checklist was checked against the actual
running system (not just the code), most via the test suite, several via
manual HTTP verification against a real local PostgreSQL instance (see
`docs/PROJECT_STATUS.md`, "Validation performed" for the exact commands and
results):

| Check | How verified |
|---|---|
| No plaintext passwords stored | `tests/unit/test_security.py`, manual `psql` inspection of `users.password_hash` |
| No secrets in source/docs/git | Manual review of every new/changed file; `.env` confirmed gitignored |
| Signup cannot self-select role/department/status | `tests/integration/test_auth_signup.py` (3 tests) + manual `curl` attempt |
| System Admin cannot be created via public signup | No code path exists; `SignupRequest` has no `role` field at all |
| Pending/deactivated users cannot log in | `tests/integration/test_auth_login.py`, manual `curl` |
| JWT expiration enforced | `tests/unit/test_security.py`, `tests/integration/test_auth_current_user.py` |
| JWT tampering rejected | `tests/unit/test_security.py`, `tests/integration/test_auth_current_user.py`, manual `curl` |
| Password hashes never in API responses | `tests/integration/test_auth_login.py`, `test_auth_current_user.py` |
| Errors don't leak unnecessary info | §6 (login enumeration); signup's four rejection reasons collapse to one response (§5) |
| Bootstrap blocked once an active System Admin exists | `tests/integration/test_auth_bootstrap.py`, manual CLI run against `lrs_dev` |

No findings required a code change beyond what's already described above —
these were design decisions verified to hold, not defects found and fixed.

## 11. API endpoints

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/auth/signup` | No | Create a `PENDING_APPROVAL` account from a valid authorization |
| `POST` | `/api/v1/auth/login` | No | Exchange email/password for a JWT |
| `GET` | `/api/v1/auth/me` | Yes (Bearer JWT) | Return the caller's own profile — a development/verification endpoint that also stays useful for the future frontend |

## 12. Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs/verifies every JWT | *(none — must be set)* |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `60` |

All three already existed in `app/core/config.py` before this phase (added
as placeholders in Phase 1); no configuration schema change was needed,
only real use of what was already there. See `.env.example` for comments
on each.

## 13. Test strategy

* `tests/unit/test_security.py`, `tests/unit/test_email_utils.py` — pure
  functions, no database, always run.
* `tests/integration/test_auth_bootstrap.py`, `test_auth_signup.py`,
  `test_auth_login.py`, `test_auth_current_user.py` — against a real local
  PostgreSQL test database (`lrs_test`), using the `client`/`db_session`
  fixtures in `tests/conftest.py`. Skipped, not failed, if no test database
  is reachable — unchanged policy from Phase 2.
* `test_concurrent_signup_attempts_consume_authorization_exactly_once`
  deliberately does *not* use those shared fixtures — it needs two
  genuinely independent database connections to model a real race, so it
  opens its own engine/sessions and cleans up its own committed rows
  explicitly (see the test for detail).

Run everything with:

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg2://lrs_test:lrs_test@localhost:5432/lrs_test pytest
```

(Or rely on the same default `TEST_DATABASE_URL` conftest.py already falls
back to — see `docs/database/README.md`.) `SECRET_KEY` must also be set
(via `.env`) for the JWT-dependent tests to run at all — see
`backend/README.md`, "Tests".

## 14. What is implemented vs. deferred

### Implemented (Phase 3A)

* Local email/password authentication — no external identity provider.
* Argon2id password hashing, centralized password policy.
* JWT access tokens (creation, validation, expiration).
* `get_current_user` dependency — the identity-establishment foundation
  Phase 3B's authorization checks will sit on top of.
* Account lifecycle enforcement (`PENDING_APPROVAL`/`ACTIVE`/`DEACTIVATED`)
  at login and on every authenticated request.
* Authorized signup against `UserAuthorization`, race-safe consumption.
* CLI bootstrap of the first System Admin.
* `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`.

### Deferred to Phase 3B

* Role/department authorization decorators — `get_current_user` establishes
  *who*, not *what they're allowed to do*.
* Department management endpoints.
* Admin user-management endpoints (approving `PENDING_APPROVAL` accounts,
  deactivating users, creating `UserAuthorization` records via the API —
  today these can only be done by direct database access).
* System Admin handover workflow (see §9).
* Any letter/document/notification functionality.

### Other explicitly out of scope for this phase (per the brief)

* Social login / external OAuth.
* Password recovery via email.
* Email verification.
* Multi-factor authentication.
* Refresh tokens / token revocation.
* Full frontend authentication UI — see §15.

## 15. Frontend

**Deliberately untouched in this phase.** The brief explicitly permits
this ("If frontend changes are genuinely unnecessary for this phase, leave
the frontend untouched") — the API surface was verified thoroughly via the
automated test suite (`tests/integration/test_auth_*.py`, using FastAPI's
`TestClient`) and via manual `curl`/CLI runs against a real local
PostgreSQL instance (see `docs/PROJECT_STATUS.md`). Building even a minimal
API client stub risked scope creep with no verification value beyond what
those already provide. Full login/signup UI, protected routing, and
token storage are frontend-phase work.

## 16. Known limitations

* No refresh tokens: a token cannot be renewed without logging in again.
* No token revocation: a compromised-but-unexpired token remains valid
  until `exp` (mitigated in that a deactivated account's token stops being
  *useful* immediately — see §3 — but the token itself isn't revoked).
* `UserAuthorization` creation has no API yet — an authorization must be
  inserted directly (as this phase's own manual verification did), since
  Admin user-management endpoints are Phase 3B work.
* Bootstrap has no race-condition hardening beyond a single transaction —
  an accepted, documented simplification (§8) since it's a rare, CLI-only,
  operator-run action.
* `getpass.getpass()` reads directly from the console on Windows and does
  not accept piped/redirected stdin — confirmed during this phase's manual
  verification. This is standard `getpass` behavior (arguably a desirable
  security property — it stops a password from being accidentally
  scripted into a piped command) and not a bug in `app/cli.py`; automated
  tests exercise `create_system_admin` directly rather than the interactive
  wrapper for this reason.
