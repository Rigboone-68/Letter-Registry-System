"""remove premature reference number global uniqueness assumption

Phase 4B hardening pass. `48ec742d9e8f` added `uq_letters_reference_number`
— a *global* uniqueness constraint — reading the finalized business
decision "Reference Number ... Must be UNIQUE" as globally scoped. On
review, that scope was never actually confirmed: the decision says
"unique", not "globally unique", "unique per receiving department",
"unique per source", or "unique per year". This is a real government
multi-department registry — two different sending departments could
legitimately each use their own overlapping internal numbering (e.g. both
issuing a "001/2026"), and a global constraint would silently reject the
second as a 409 conflict for a scope the business never actually asked
for.

Rather than keep a guessed constraint because it happened to already be
implemented, or replace it with a *different* guessed scope (e.g.
per-department), this migration removes the constraint entirely and
enforces nothing beyond "required, non-blank string" until the business
confirms the actual uniqueness scope — see
docs/architecture/letter-registry.md §2.3/§12 (PENDING BUSINESS
CLARIFICATION) and docs/PROJECT_STATUS.md. `reference_number` itself
remains required (`NOT NULL`) — only its confirmed-but-then-guessed
*uniqueness scope* is being walked back; existence and format were never
in question.

Downgrade caveat: re-adding the unique constraint will fail if any
duplicate `reference_number` values were inserted while it was absent —
an expected, accepted asymmetry (downgrading after real data has
diverged from the constraint you're restoring is inherently unsafe, not
specific to this migration).

Revision ID: c887ab35e4a3
Revises: 48ec742d9e8f
Create Date: 2026-08-22 23:07:23.522306
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c887ab35e4a3"
down_revision: Union[str, None] = "48ec742d9e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_letters_reference_number", "letters", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_letters_reference_number", "letters", ["reference_number"]
    )
