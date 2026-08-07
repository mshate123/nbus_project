"""Strengthen the ledger schema and protect posted history.

Revision ID: 002_ledger_rewrite
Revises: 001_initial
"""

from alembic import op


revision = "002_ledger_rewrite"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def _create_enum(name: str, values: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({values});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def _add_check_constraint(table: str, name: str, expression: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def upgrade() -> None:
    _create_enum("normal_balance", "'DEBIT', 'CREDIT'")
    _create_enum("rate_tier", "'standard', 'premium', 'savings'")

    op.execute(
        "ALTER TABLE journal_lines ALTER COLUMN debit TYPE NUMERIC(18, 4) "
        "USING debit::numeric(18, 4)"
    )
    op.execute(
        "ALTER TABLE journal_lines ALTER COLUMN credit TYPE NUMERIC(18, 4) "
        "USING credit::numeric(18, 4)"
    )
    op.execute(
        "ALTER TABLE rate_schedule ALTER COLUMN annual_rate TYPE NUMERIC(8, 6) "
        "USING annual_rate::numeric(8, 6)"
    )

    op.execute(
        """
        ALTER TABLE accounts
            ADD COLUMN IF NOT EXISTS rate_tier rate_tier
                NOT NULL DEFAULT 'standard'
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'accounts'
                  AND column_name = 'normal_balance'
                  AND data_type = 'character varying'
            ) THEN
                ALTER TABLE accounts
                    ALTER COLUMN normal_balance TYPE normal_balance
                    USING normal_balance::text::normal_balance;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'rate_schedule'
                  AND column_name = 'tier'
                  AND data_type = 'character varying'
            ) THEN
                ALTER TABLE rate_schedule
                    ALTER COLUMN tier TYPE rate_tier
                    USING tier::text::rate_tier;
            END IF;
        END $$;
        """
    )

    _add_check_constraint(
        "accounts",
        "ck_account_normal_balance",
        "normal_balance IN ('DEBIT', 'CREDIT')",
    )
    _add_check_constraint(
        "accounts",
        "ck_account_rate_tier",
        "rate_tier IN ('standard', 'premium', 'savings')",
    )
    _add_check_constraint(
        "rate_schedule",
        "ck_rate_schedule_tier",
        "tier IN ('standard', 'premium', 'savings')",
    )
    _add_check_constraint(
        "rate_schedule", "ck_rate_schedule_nonnegative", "annual_rate >= 0"
    )
    _add_check_constraint(
        "journal_lines", "ck_journal_line_nonzero", "debit > 0 OR credit > 0"
    )
    _add_check_constraint(
        "journal_entries",
        "ck_posted_entry_has_timestamp",
        "(status = 'POSTED' AND posted_at IS NOT NULL) OR status = 'DRAFT'",
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_reversal_of_id
        ON journal_entries (reversal_of_id)
        WHERE reversal_of_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_accrual_per_account_day
        ON journal_entries (accrual_account_id, accrual_date)
        WHERE is_accrual = true
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_accounts_active ON accounts (active)"
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_entry_id ON journal_lines (entry_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_account_id ON journal_lines (account_id)"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_posted_entry_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status = 'POSTED' THEN
                RAISE EXCEPTION 'posted journal entries are immutable'
                    USING ERRCODE = '23000';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_reject_posted_entry_mutation ON journal_entries")
    op.execute(
        """
        CREATE TRIGGER trg_reject_posted_entry_mutation
        BEFORE UPDATE OR DELETE ON journal_entries
        FOR EACH ROW EXECUTE FUNCTION reject_posted_entry_mutation()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_posted_line_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_entry_id UUID;
            target_status entry_status;
        BEGIN
            target_entry_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
            SELECT status INTO target_status
            FROM journal_entries
            WHERE id = target_entry_id;
            IF target_status = 'POSTED' THEN
                RAISE EXCEPTION 'journal lines belonging to posted entries are immutable'
                    USING ERRCODE = '23000';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_reject_posted_line_mutation ON journal_lines")
    op.execute(
        """
        CREATE TRIGGER trg_reject_posted_line_mutation
        BEFORE UPDATE OR DELETE ON journal_lines
        FOR EACH ROW EXECUTE FUNCTION reject_posted_line_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_reject_posted_line_mutation ON journal_lines"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_reject_posted_entry_mutation ON journal_entries"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_posted_line_mutation()")
    op.execute("DROP FUNCTION IF EXISTS reject_posted_entry_mutation()")
    op.execute("ALTER TABLE accounts DROP CONSTRAINT IF EXISTS ck_account_rate_tier")
    op.execute(
        "ALTER TABLE accounts DROP CONSTRAINT IF EXISTS ck_account_normal_balance"
    )
    op.execute("ALTER TABLE rate_schedule DROP CONSTRAINT IF EXISTS ck_rate_schedule_tier")
    op.execute(
        "ALTER TABLE rate_schedule DROP CONSTRAINT IF EXISTS ck_rate_schedule_nonnegative"
    )
    op.execute(
        "ALTER TABLE journal_lines DROP CONSTRAINT IF EXISTS ck_journal_line_nonzero"
    )
    op.execute(
        "ALTER TABLE journal_entries DROP CONSTRAINT IF EXISTS ck_posted_entry_has_timestamp"
    )
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS rate_tier")
    op.execute(
        "ALTER TABLE rate_schedule ALTER COLUMN tier TYPE VARCHAR(50) "
        "USING tier::text"
    )
    op.execute(
        "ALTER TABLE accounts ALTER COLUMN normal_balance TYPE VARCHAR(6) "
        "USING normal_balance::text"
    )
    op.execute("DROP TYPE IF EXISTS rate_tier")
    op.execute("DROP TYPE IF EXISTS normal_balance")
