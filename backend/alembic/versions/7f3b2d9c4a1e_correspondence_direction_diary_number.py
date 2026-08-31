"""correspondence direction, diary number, dispatch/continuation links

Phase 6A (docs/architecture/correspondence.md). Four additive changes to
`letters`, plus one new counter table — nothing existing is renamed,
narrowed, or backfilled with invented data:

1. `letters.direction` (new `letter_direction` enum: `INCOMING`/
   `OUTGOING`), `NOT NULL`, `server_default 'INCOMING'` — every letter
   recorded before this migration already represented "something that
   arrived here and we recorded it," i.e. `INCOMING`; the server default
   applies that true, unchanged fact to every existing row automatically,
   which is not the same thing as backfilling a guessed value.

2. `letters.dispatch_department_id` — nullable FK to `departments`,
   `ondelete=RESTRICT` (same behavior as `source_department_id`/
   `category_id`/`classification_id`). The destination department for an
   `OUTGOING` letter; required at the service layer, not here, exactly
   when `direction == OUTGOING`.

3. `letters.diary_number` — nullable `varchar(50)`. `NULL` for every
   existing row and deliberately never backfilled (there is no true
   historical diary number to recover); auto-generated going forward by
   the service layer via the new `letter_number_sequences` table.

4. `letters.recorded_from_letter_id` / `letters.continuation_of_letter_id`
   — nullable, self-referential FKs to `letters.id`, `ondelete=RESTRICT`
   (letters are never physically deleted, so this can never actually
   fire in normal operation — same reasoning as every other Letter FK).
   `recorded_from_letter_id` also gets a **partial unique index** — the
   database-enforced half of "an outgoing letter can be recorded at most
   once" (the other half is the service-layer idempotent check-then-
   insert in `app/services/letter_service.py:record_incoming_correspondence`).

5. `letter_number_sequences` — a new, minimal counter table (composite
   primary key `department_id, direction`), the backing store for
   `diary_number` generation. Created lazily per department by the
   service layer, not pre-seeded here.

Revision ID: 7f3b2d9c4a1e
Revises: 323ccfde77f4
Create Date: 2026-08-31 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7f3b2d9c4a1e"
down_revision: Union[str, None] = "323ccfde77f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# `create_type=False` on the shared object — the type is created exactly
# once, explicitly, at the top of `upgrade()` below; without this, each
# subsequent `sa.Column(..., letter_direction_enum)` usage (on `letters`
# and again on the new `letter_number_sequences` table) would each try
# to `CREATE TYPE` it a second/third time and fail with "already exists".
letter_direction_enum = postgresql.ENUM(
    "INCOMING", "OUTGOING", name="letter_direction", create_type=False
)

_DISPATCH_DEPARTMENT_FK = "letters_dispatch_department_id_fkey"
_RECORDED_FROM_FK = "letters_recorded_from_letter_id_fkey"
_CONTINUATION_OF_FK = "letters_continuation_of_letter_id_fkey"
_SEQUENCE_DEPARTMENT_FK = "letter_number_sequences_department_id_fkey"


def upgrade() -> None:
    letter_direction_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "letters",
        sa.Column(
            "direction",
            letter_direction_enum,
            nullable=False,
            server_default="INCOMING",
        ),
    )
    op.create_index("ix_letters_direction", "letters", ["direction"])

    op.add_column(
        "letters",
        sa.Column("dispatch_department_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_letters_dispatch_department_id", "letters", ["dispatch_department_id"]
    )
    op.create_foreign_key(
        _DISPATCH_DEPARTMENT_FK,
        "letters",
        "departments",
        ["dispatch_department_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column("letters", sa.Column("diary_number", sa.String(length=50), nullable=True))

    op.add_column(
        "letters",
        sa.Column("recorded_from_letter_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        _RECORDED_FROM_FK,
        "letters",
        "letters",
        ["recorded_from_letter_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_letters_recorded_from_letter_id",
        "letters",
        ["recorded_from_letter_id"],
        unique=True,
        postgresql_where=sa.text("recorded_from_letter_id IS NOT NULL"),
    )

    op.add_column(
        "letters",
        sa.Column("continuation_of_letter_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_letters_continuation_of_letter_id", "letters", ["continuation_of_letter_id"]
    )
    op.create_foreign_key(
        _CONTINUATION_OF_FK,
        "letters",
        "letters",
        ["continuation_of_letter_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "letter_number_sequences",
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", letter_direction_enum, nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("department_id", "direction"),
    )
    op.create_foreign_key(
        _SEQUENCE_DEPARTMENT_FK,
        "letter_number_sequences",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_table("letter_number_sequences")

    op.drop_constraint(_CONTINUATION_OF_FK, "letters", type_="foreignkey")
    op.drop_index("ix_letters_continuation_of_letter_id", table_name="letters")
    op.drop_column("letters", "continuation_of_letter_id")

    op.drop_index("uq_letters_recorded_from_letter_id", table_name="letters")
    op.drop_constraint(_RECORDED_FROM_FK, "letters", type_="foreignkey")
    op.drop_column("letters", "recorded_from_letter_id")

    op.drop_column("letters", "diary_number")

    op.drop_constraint(_DISPATCH_DEPARTMENT_FK, "letters", type_="foreignkey")
    op.drop_index("ix_letters_dispatch_department_id", table_name="letters")
    op.drop_column("letters", "dispatch_department_id")

    op.drop_index("ix_letters_direction", table_name="letters")
    op.drop_column("letters", "direction")

    letter_direction_enum.drop(op.get_bind(), checkfirst=True)
