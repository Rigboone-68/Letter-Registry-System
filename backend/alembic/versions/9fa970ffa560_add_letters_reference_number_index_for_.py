"""add letters reference_number index for registry search

Phase 4C. `reference_number` lost its implicit index when
`uq_letters_reference_number` was removed (migration `c887ab35e4a3`,
Phase 4B hardening pass) — a `UNIQUE` constraint is backed by an index
automatically; a non-unique column is not. Reference-number search is an
explicitly requested Phase 4C capability
(docs/architecture/registry-search.md §2-4), so a plain B-tree index is
justified here even though the actual query uses `ILIKE '%term%'` (which
can't use a B-tree index for the "contains" case) — the index still
benefits exact/prefix lookups on this column and is the one index this
phase's review concluded was justified (see that doc §15 — no index was
added for `subject`/`sender_name`/etc., since a plain B-tree gives them
no benefit at all for "contains" matching).

Revision ID: 9fa970ffa560
Revises: c887ab35e4a3
Create Date: 2026-08-23 00:04:59.529107
"""

from typing import Sequence, Union

from alembic import op

revision: str = "9fa970ffa560"
down_revision: Union[str, None] = "c887ab35e4a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_letters_reference_number", "letters", ["reference_number"])


def downgrade() -> None:
    op.drop_index("ix_letters_reference_number", table_name="letters")
