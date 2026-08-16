"""database hardening: department status index, letter_documents uploaded_by index, notifications is_read server default

Corrective migration from the Phase 2 self-review. Does not modify the
Phase 2 baseline (`3da4b7ee8167`), which is treated as an immutable
snapshot once applied — see that migration's own docstring. Three changes,
all additive and non-destructive:

  1. `ix_departments_status` — Category and Classification already index
     their `status` column; Department (arguably the most frequently
     filtered "active/inactive" table) did not. Inconsistency, not a design
     decision — see docs/database/schema.md, "Indexes".
  2. `ix_letter_documents_uploaded_by` — every other User-referencing
     foreign key in this schema (`notifications.recipient_user_id`,
     `audit_logs.user_id`, `user_authorizations.authorized_by`) is indexed;
     this one wasn't. Same reasoning.
  3. `notifications.is_read` gains a database-level `DEFAULT false`. The
     column was already `NOT NULL` with a Python-side (ORM) default, but a
     row written outside the ORM — raw SQL, a future admin script — had no
     safe fallback and would fail the NOT NULL constraint. `ALTER COLUMN
     ... SET DEFAULT` only changes metadata; it does not rewrite existing
     rows and is safe on any table size.

The `ck_users_role_department_pairing` CHECK constraint's *model-side*
construction changed (built from `UserRole.*.value` instead of typed-out
literals — see app/models/user.py), but the compiled SQL text is byte-
identical to what this migration's baseline already created, so no DDL
change is needed or included here. The several `passive_deletes="all"`
additions across app/models/*.py (Department, Category, Classification,
User, Letter relationships) are pure SQLAlchemy ORM configuration — they
change how the ORM issues DELETE statements, not the schema — so they too
require no migration.

Revision ID: e8a5cea2ccc6
Revises: 3da4b7ee8167
Create Date: 2026-08-17 02:04:21.740310
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8a5cea2ccc6"
down_revision: Union[str, None] = "3da4b7ee8167"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_departments_status", "departments", ["status"])
    op.create_index(
        "ix_letter_documents_uploaded_by", "letter_documents", ["uploaded_by"]
    )
    op.alter_column(
        "notifications",
        "is_read",
        server_default=sa.false(),
    )


def downgrade() -> None:
    op.alter_column(
        "notifications",
        "is_read",
        server_default=None,
    )
    op.drop_index("ix_letter_documents_uploaded_by", table_name="letter_documents")
    op.drop_index("ix_departments_status", table_name="departments")
