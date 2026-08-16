# Database Documentation

PostgreSQL is the system of record for all metadata. Scanned documents live on
the filesystem and are referenced by path.

Phase 1 defines no tables and contains no migrations. This directory will hold:

* `schema.md` — entities, relationships, and indexes
* `conventions.md` — naming, key strategy, soft-delete and audit-column rules
* `migrations.md` — how to generate, review, and apply Alembic revisions
