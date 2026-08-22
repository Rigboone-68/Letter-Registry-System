"""letter registry core: recipient/source department, sender details, reference number, category seed, classification restricts_access

Phase 4B. Implements the six finalized business decisions from
docs/architecture/letter-registry.md §2, on top of the Phase 2 `letters`/
`categories`/`classifications` tables (unchanged in shape until now).

Renames (data preserved, not recreated):
  * `letters.department_id` -> `recipient_department_id` — the ambiguous
    single department field Phase 4A flagged is now unambiguous: this is
    the department-isolation boundary, never the source. Every index and
    the FK constraint referencing this column are renamed to match, so
    DDL introspection stays consistent with the new name (the same naming
    discipline adopted after the Phase 3B.2 Department constraint-naming
    incident — see docs/database/schema.md §2.1).
  * `letters.received_from` -> `source_name` — same column, clarified
    name; it already held exactly this free-text "who/where this letter
    is from" value since Phase 2.

New nullable columns (no backfill needed): `source_department_id` (FK ->
departments.id, RESTRICT, indexed — populated only when the source
happens to be an LRS-registered department), `source_location`,
`sender_address`.

New required columns, added nullable -> backfilled -> tightened (the
standard safe pattern this project used for user_authorizations.purpose
in a223396c9eac — works identically whether `letters` currently has zero
rows or many): `sender_name`, `sender_designation`, `sender_department`,
`reference_number`. Backfilled to a clearly-marked placeholder, never a
blank string, so a pre-existing row is visibly a migration artifact
needing follow-up rather than silently looking like real data.
`reference_number`'s placeholder is `'MIGRATED-' || id` (the row's own
UUID) specifically because it must be globally unique — a single repeated
placeholder would violate the unique constraint added immediately after.

`classifications.restricts_access` (boolean, NOT NULL, default false) —
the classified-access authorization boundary's data-model half; see
docs/architecture/letter-registry.md §8. Not derived from `name` — no
classification is seeded as restricting access by this migration; a
System Admin sets this explicitly per classification once one exists.

Seeds exactly three `categories` rows (General Letter, Notification,
Office Order) — a data migration, not a schema change, and not something
application code seeds on every startup. No `classifications` rows are
seeded (the value list remains open — see docs/architecture/letter-registry.md
§2.5/§12).

Revision ID: 48ec742d9e8f
Revises: a223396c9eac
Create Date: 2026-08-22 18:23:32.443737
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "48ec742d9e8f"
down_revision: Union[str, None] = "a223396c9eac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_categories_table = sa.table(
    "categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("status", sa.String),
)

_SEED_CATEGORIES = ["General Letter", "Notification", "Office Order"]


def upgrade() -> None:
    # --- 1. Recipient department (rename, preserves every existing value) ---
    op.alter_column("letters", "department_id", new_column_name="recipient_department_id")
    op.execute(
        "ALTER TABLE letters RENAME CONSTRAINT letters_department_id_fkey "
        "TO letters_recipient_department_id_fkey"
    )
    op.execute(
        "ALTER INDEX ix_letters_department_id RENAME TO ix_letters_recipient_department_id"
    )
    op.execute(
        "ALTER INDEX ix_letters_department_received_at "
        "RENAME TO ix_letters_recipient_department_received_at"
    )

    # --- 2. Source name (rename, preserves every existing value) -----------
    op.alter_column("letters", "received_from", new_column_name="source_name")

    # --- 3. New nullable columns --------------------------------------------
    op.add_column(
        "letters",
        sa.Column(
            "source_department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_letters_source_department_id", "letters", ["source_department_id"])
    op.add_column("letters", sa.Column("source_location", sa.String(length=255), nullable=True))
    op.add_column("letters", sa.Column("sender_address", sa.Text(), nullable=True))

    # --- 4. New required columns: add nullable, backfill, tighten ----------
    op.add_column("letters", sa.Column("sender_name", sa.String(length=255), nullable=True))
    op.add_column(
        "letters", sa.Column("sender_designation", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "letters", sa.Column("sender_department", sa.String(length=255), nullable=True)
    )
    op.add_column("letters", sa.Column("reference_number", sa.String(length=255), nullable=True))

    op.execute(
        "UPDATE letters SET "
        "sender_name = 'MIGRATION-PLACEHOLDER', "
        "sender_designation = 'MIGRATION-PLACEHOLDER', "
        "sender_department = 'MIGRATION-PLACEHOLDER', "
        "reference_number = 'MIGRATED-' || id::text "
        "WHERE sender_name IS NULL"
    )

    op.alter_column("letters", "sender_name", nullable=False)
    op.alter_column("letters", "sender_designation", nullable=False)
    op.alter_column("letters", "sender_department", nullable=False)
    op.alter_column("letters", "reference_number", nullable=False)

    op.create_unique_constraint(
        "uq_letters_reference_number", "letters", ["reference_number"]
    )

    # --- 5. Classification access-control flag ------------------------------
    op.add_column(
        "classifications",
        sa.Column(
            "restricts_access",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # --- 6. Seed the three finalized Category values ------------------------
    op.bulk_insert(
        _categories_table,
        [
            {"id": uuid.uuid4(), "name": name, "description": None, "status": "ACTIVE"}
            for name in _SEED_CATEGORIES
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM categories WHERE name = ANY(:names)").bindparams(
            names=_SEED_CATEGORIES
        )
    )

    op.drop_column("classifications", "restricts_access")

    op.drop_constraint("uq_letters_reference_number", "letters", type_="unique")
    op.drop_column("letters", "reference_number")
    op.drop_column("letters", "sender_department")
    op.drop_column("letters", "sender_designation")
    op.drop_column("letters", "sender_name")

    op.drop_column("letters", "sender_address")
    op.drop_column("letters", "source_location")
    op.drop_index("ix_letters_source_department_id", table_name="letters")
    op.drop_column("letters", "source_department_id")

    op.alter_column("letters", "source_name", new_column_name="received_from")

    op.execute(
        "ALTER INDEX ix_letters_recipient_department_received_at "
        "RENAME TO ix_letters_department_received_at"
    )
    op.execute(
        "ALTER INDEX ix_letters_recipient_department_id RENAME TO ix_letters_department_id"
    )
    op.execute(
        "ALTER TABLE letters RENAME CONSTRAINT letters_recipient_department_id_fkey "
        "TO letters_department_id_fkey"
    )
    op.alter_column("letters", "recipient_department_id", new_column_name="department_id")
