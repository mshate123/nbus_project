"""Own the deterministic production chart, rates, and demo ledger entries.

NOTE: This migration imports and calls `seed.seed_database()` at migration time.
This is an intentional coupling — the seed logic is idempotent and deterministic,
so replaying migrations produces the same result. However, if `seed.py` ever gains
non-deterministic behavior, external dependencies, or schema-incompatible changes,
this migration will break on replay. If that becomes a concern, inline the SQL
directly into this migration's upgrade() function.
"""

from alembic import op

from seed import seed_database


revision = "003_seed_ledger"
down_revision = "002_ledger_rewrite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the same idempotent production seed used by the seed command."""
    seed_database(op.get_bind())


def downgrade() -> None:
    """Remove only rows owned by this production bootstrap."""
    op.execute(
        """
        DELETE FROM journal_lines
        WHERE entry_id IN (
            '70000000-0000-0000-0000-000000000001',
            '70000000-0000-0000-0000-000000000002'
        )
        """
    )
    op.execute(
        """
        DELETE FROM journal_entries
        WHERE id IN (
            '70000000-0000-0000-0000-000000000001',
            '70000000-0000-0000-0000-000000000002'
        )
        """
    )
    op.execute(
        """
        DELETE FROM accounts
        WHERE code IN ('1000', '1100', '2000', '2100', '3000', '4000', '5000')
          AND id IN (
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000003',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000005',
            '10000000-0000-0000-0000-000000000006',
            '10000000-0000-0000-0000-000000000007'
          )
        """
    )
    op.execute(
        """
        DELETE FROM rate_schedule
        WHERE tier IN ('standard', 'premium', 'savings')
        """
    )
