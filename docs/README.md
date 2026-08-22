# LRS Documentation

| Directory | Contents |
|---|---|
| [`architecture/`](architecture/) | Role hierarchy, department isolation, layering rules, [authentication design](architecture/authentication.md) (Phase 3A), [authorization/RBAC design](architecture/authorization.md) (Phase 3B.1), [department management](architecture/department-management.md) (Phase 3B.2), [Admin management](architecture/admin-management.md) (Phase 3B.3), [User management](architecture/user-management.md) (Phase 3B.4), the [Letter Registry Core](architecture/letter-registry.md) (Phase 4A review + Phase 4B implementation), [Registry Operations & Search](architecture/registry-search.md) (Phase 4C — pagination, sorting, and search on `GET /api/v1/letters`), and [Document Management](architecture/document-management.md) (Phase 4D — `LetterDocument` upload/list/download implemented on top of this phase's own architecture review; no deletion endpoint, a deliberate scope decision) — all complete, deployment topology (planned), decision records (planned) |
| `api/` | REST API reference for `/api/v1` — placeholder; endpoints are documented in `architecture/authentication.md` §11 (auth), `architecture/authorization.md` §7 (verification-only), `architecture/department-management.md` §7 (departments), `architecture/admin-management.md` §10-11 (admins), `architecture/user-management.md` §4/§8/§9/§10 (users), and `architecture/letter-registry.md` §7-9 (letters, categories, classifications) ahead of a dedicated API reference in a later phase |
| [`database/`](database/) | Schema design, entity relationships, migration guide (Phase 2 — complete) |
| `user-guides/` | End-user and administrator guides per role — placeholder until roles have a UI |

Documentation is written alongside each module as it is implemented.
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) is the current, supervisor-facing
summary of what's done, in progress, and pending S&IT confirmation.

Technical documentation and UI/UX support: **Faiza**.
