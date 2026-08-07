"""Initial schema: accounts, journal_entries, journal_lines, rate_schedule.

The migration is deliberately rerunnable.  This matters when a PostgreSQL
transaction is interrupted after the enum types or some schema objects have
been committed by an earlier migration attempt.
"""

from alembic import op


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _create_enum(name: str, values: str) -> None:
    # PostgreSQL has no CREATE TYPE IF NOT EXISTS.  duplicate_object is scoped
    # to this block, so an enum left by a partial upgrade is harmless.
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({values});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """
    )


def _add_check_constraint(table: str, name: str, expression: str) -> None:
    # CREATE TABLE IF NOT EXISTS does not help when a previous attempt created
    # the table but failed before adding a later constraint.
    op.execute(
        f"""
        DO $$ BEGIN
            ALTER TABLE {table}
                ADD CONSTRAINT {name} CHECK ({expression});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """
    )


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    _create_enum(
        "account_type",
        "'ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'",
    )
    _create_enum("entry_status", "'DRAFT', 'POSTED'")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            code VARCHAR(10) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            type account_type NOT NULL,
            normal_balance VARCHAR(6) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts (code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_accounts_active ON accounts (active)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            status entry_status NOT NULL DEFAULT 'DRAFT',
            posted_at TIMESTAMPTZ,
            reversal_of_id UUID REFERENCES journal_entries(id),
            is_accrual BOOLEAN NOT NULL DEFAULT FALSE,
            accrual_account_id UUID REFERENCES accounts(id),
            accrual_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )
    # Repair tables created by an older/partial migration before applying
    # constraints and indexes below.  ADD COLUMN IF NOT EXISTS is safe on a
    # fresh database and preserves existing data on a persistent volume.
    op.execute(
        "ALTER TABLE journal_entries "
        "ADD COLUMN IF NOT EXISTS accrual_account_id UUID "
        "REFERENCES accounts(id)"
    )
    op.execute(
        "ALTER TABLE journal_entries " "ADD COLUMN IF NOT EXISTS accrual_date DATE"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_status ON journal_entries (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_posted_at ON journal_entries (posted_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_is_accrual ON journal_entries (is_accrual)"
    )
    _add_check_constraint(
        "journal_entries",
        "ck_accrual_fields_consistent",
        "(is_accrual = false AND accrual_account_id IS NULL AND accrual_date IS NULL) OR "
        "(is_accrual = true AND accrual_account_id IS NOT NULL AND accrual_date IS NOT NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_reversal_of_id "
        "ON journal_entries (reversal_of_id) WHERE reversal_of_id IS NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_lines (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            entry_id UUID NOT NULL REFERENCES journal_entries(id),
            account_id UUID NOT NULL REFERENCES accounts(id),
            debit NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
            credit NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_entry_id ON journal_lines (entry_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_account_id ON journal_lines (account_id)"
    )
    _add_check_constraint(
        "journal_lines", "ck_journal_line_nonnegative", "debit >= 0 AND credit >= 0"
    )
    _add_check_constraint(
        "journal_lines", "ck_journal_line_one_side", "NOT (debit > 0 AND credit > 0)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_schedule (
            tier VARCHAR(50) PRIMARY KEY,
            annual_rate NUMERIC(8, 6) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )

    # Use the stored DATE column rather than a cast expression.  This keeps
    # the index usable and makes the idempotency key match the ORM/service.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_accrual_per_account_day "
        "ON journal_entries (accrual_account_id, accrual_date) "
        "WHERE is_accrual = true"
    )
    op.execute(
        """
        INSERT INTO rate_schedule (tier, annual_rate)
        VALUES ('standard', 0.035000), ('premium', 0.045000), ('savings', 0.050000)
        ON CONFLICT (tier) DO NOTHING
    """
    )


def downgrade() -> None:
    # Drop in dependency order; CASCADE also handles indexes/constraints left
    # behind by a partially completed upgrade.
    op.execute("DROP TABLE IF EXISTS rate_schedule CASCADE")
    op.execute("DROP TABLE IF EXISTS journal_lines CASCADE")
    op.execute("DROP TABLE IF EXISTS journal_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")

    # Do not remove an enum still referenced by another schema object.  This
    # also makes downgrade safe when the enum predated this migration.
    for enum_name in ("entry_status", "account_type"):
        op.execute(
            f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}')
                   AND NOT EXISTS (
                       SELECT 1 FROM pg_depend d
                       JOIN pg_type t ON t.oid = d.refobjid
                       WHERE t.typname = '{enum_name}'
                   ) THEN
                    EXECUTE 'DROP TYPE {enum_name}';
                END IF;
            END $$;
        """
        )
