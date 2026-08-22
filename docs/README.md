# LRS Documentation

| Directory | Contents |
|---|---|
| [`architecture/`](architecture/) | Role hierarchy, department isolation, layering rules, [authentication design](architecture/authentication.md) (Phase 3A), [authorization/RBAC design](architecture/authorization.md) (Phase 3B.1), [department management](architecture/department-management.md) (Phase 3B.2), [Admin management](architecture/admin-management.md) (Phase 3B.3), and [User management](architecture/user-management.md) (Phase 3B.4) — all complete, deployment topology (planned), decision records (planned) |
| `api/` | REST API reference for `/api/v1` — placeholder; endpoints are documented in `architecture/authentication.md` §11 (auth), `architecture/authorization.md` §7 (verification-only), `architecture/department-management.md` §7 (departments), `architecture/admin-management.md` §10-11 (admins), and `architecture/user-management.md` §4/§8/§9/§10 (users) ahead of a dedicated API reference in a later phase |
| [`database/`](database/) | Schema design, entity relationships, migration guide (Phase 2 — complete) |
| `user-guides/` | End-user and administrator guides per role — placeholder until roles have a UI |

Documentation is written alongside each module as it is implemented.
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) is the current, supervisor-facing
summary of what's done, in progress, and pending S&IT confirmation.

Technical documentation and UI/UX support: **Faiza**.
