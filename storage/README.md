# Document Storage

Scanned letters are stored on the application server's filesystem, deliberately
outside PostgreSQL. The database holds only metadata plus a relative path into
this directory, which keeps backups, disk sizing, and retention policy for
documents independent of the database.

## Layout convention

Paths are built from logical identifiers rather than a flat dump, so the tree
stays navigable as volume grows and so departments can be archived or moved
independently:

```
storage/letters/<department-code>/<year>/<month>/<letter-uuid>.<ext>
```

Example (illustrative only — no files exist in Phase 1):

```
storage/letters/REV-01/2026/03/6f1c2a9e-....pdf
```

Nothing in the design assumes a single department: the department segment is
always present, including for any future centralized or unassigned bucket.

## Rules

* The runtime root is configured via `STORAGE_PATH` — never hard-coded.
* Stored filenames are system-generated identifiers, not user-supplied names.
  The original filename is metadata in the database.
* Directory contents are ignored by Git; only `.gitkeep` is tracked.
* Upload handling, validation, and virus/type checking are Phase 3 work and
  are not implemented here.
