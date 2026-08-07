# Data Models

## Tables

### accounts
`id UUID PK`, `code VARCHAR(10) UNIQUE`, `name VARCHAR(255)`, `type account_type`, `normal_balance VARCHAR(6)`, `active BOOLEAN`, `created_at TIMESTAMPTZ`.

### journal_entries
`id UUID PK`, `status entry_status`, `posted_at TIMESTAMPTZ nullable`, `reversal_of_id UUID self-FK nullable`, `is_accrual BOOLEAN`, `accrual_account_id UUID FK nullable`, `accrual_date DATE nullable`, timestamps. Constraints require accrual metadata to be all present or all absent. Partial unique index `uq_reversal_of_id` permits at most one reversal per original; `uq_accrual_per_account_day` enforces one accrual per account/date where `is_accrual=true`.

### journal_lines
`id UUID PK`, `entry_id FK`, `account_id FK`, `debit NUMERIC(18,4)`, `credit NUMERIC(18,4)`, `created_at`. Constraints require nonnegative amounts and forbid both sides being positive. There is no database constraint enforcing entry-level debit/credit equality.

### rate_schedule
`tier VARCHAR(50) PK`, `annual_rate NUMERIC(8,6)`, timestamps. Initial migration seeds `standard=0.035000`, `premium=0.045000`, `savings=0.050000`.

## Domain rules observed
- Account balance is derived, never stored.
- Debit-normal accounts use debits minus credits; credit-normal accounts use credits minus debits.
- Posted entries are intended to be append-only, but the database schema does not fully enforce immutability.
- Account `normal_balance` is a free-form string in the ORM, not an enum/check constraint.
- Rate tiers are not linked to accounts, despite the requirement phrase “per account's rate tier”; accrual currently always uses the `standard` row.
- Migration text and fixtures disagree on rate values and tier names: migration uses standard/premium/savings at 3.5/4.5/5.0%; factories use standard/premium/vip at 4.5/5.0/5.5%.
