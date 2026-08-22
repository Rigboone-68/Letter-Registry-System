# Document Storage

Scanned letters are stored on the application server's filesystem, deliberately
outside PostgreSQL. The database holds only metadata plus a relative path into
this directory, which keeps backups, disk sizing, and retention policy for
documents independent of the database.

## Layout convention (implemented, Phase 4D)

```
storage/letters/<letter-uuid>/<document-uuid>.<ext>
```

Both identifiers are server-generated UUIDs — never derived from a
client-supplied filename or path. `<ext>` is one of `pdf`/`jpg`/`png`/`txt`,
chosen from a fixed map keyed by the document's magic-byte-validated
content type, never taken from the client's filename. See
`app/services/document_storage.py` and
`docs/architecture/document-management.md` §5-7.

This supersedes the department/year/month-grouped convention this file
originally sketched in Phase 1 (`<department-code>/<year>/<month>/<letter-uuid>.<ext>`),
which was never implemented and — the Phase 4D architecture review found —
had no document-identifier segment at all, implicitly assuming one file
per letter. The Phase 4D *implementation* brief specified the simpler,
flat-per-letter structure above directly, which is what was actually
built; the review's own §7 had recommended keeping a department/year/
month grouping layer on top of it for long-term browsability at large
volumes. That grouping was **not** implemented in V1 — a deliberate
simplification, not an oversight — and remains a reasonable future
enhancement if the flat per-letter directory layout becomes unwieldy.

## Rules

* The runtime root is configured via `STORAGE_PATH`, resolved to an
  absolute path (and created if missing) on first use — see
  `app/services/document_storage.py:get_storage_root`.
* Stored filenames are system-generated identifiers, not user-supplied
  names. The original filename is metadata in the database only
  (`letter_documents.original_filename`) — never part of a filesystem
  path, and never returned in an API response's `storage_path`-shaped
  field (there is no such field on `DocumentResponse`).
* Directory contents are ignored by Git; only `.gitkeep` is tracked.
* Upload handling and layered file-type/size validation are implemented
  — see `app/services/document_validation.py` and
  `app/api/v1/endpoints/documents.py`. Malware/antivirus scanning is
  explicitly **not** implemented; validation proves a file's bytes
  structurally match an accepted type, not that the file is safe.
* No document is ever physically or soft deleted by this system (V1 has
  no deletion endpoint of any kind) — see
  `docs/architecture/document-management.md` §14.
