"""Authoritative production bootstrap data and explicit seed command.

This module is the production owner of stable account codes, rate tiers, and
balanced demo entries. Test factories must generate their own rows and must
not import these values.
"""

from __future__ import annotations

from decimal import Decimal
import os
from uuid import UUID, uuid5

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


PRODUCTION_RATES = (
    {"tier": "standard", "annual_rate": Decimal("0.035000")},
    {"tier": "premium", "annual_rate": Decimal("0.045000")},
    {"tier": "savings", "annual_rate": Decimal("0.050000")},
)

PRODUCTION_CHART_OF_ACCOUNTS = (
    {
        "id": "10000000-0000-0000-0000-000000000001",
        "code": "1000",
        "name": "Cash & Liquidity Reserve",
        "type": "ASSET",
        "normal_balance": "DEBIT",
        "rate_tier": "standard",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000002",
        "code": "1100",
        "name": "Customer Deposits Escrow",
        "type": "ASSET",
        "normal_balance": "DEBIT",
        "rate_tier": "standard",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000003",
        "code": "2000",
        "name": "Customer Savings Accounts",
        "type": "LIABILITY",
        "normal_balance": "CREDIT",
        "rate_tier": "savings",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000004",
        "code": "2100",
        "name": "Accrued Interest Payable",
        "type": "LIABILITY",
        "normal_balance": "CREDIT",
        "rate_tier": "savings",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000005",
        "code": "3000",
        "name": "Bank Equity Capital",
        "type": "EQUITY",
        "normal_balance": "CREDIT",
        "rate_tier": "standard",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000006",
        "code": "4000",
        "name": "Interest Income",
        "type": "REVENUE",
        "normal_balance": "CREDIT",
        "rate_tier": "standard",
        "active": True,
    },
    {
        "id": "10000000-0000-0000-0000-000000000007",
        "code": "5000",
        "name": "Interest Expense (Savings)",
        "type": "EXPENSE",
        "normal_balance": "DEBIT",
        "rate_tier": "savings",
        "active": True,
    },
)

PRODUCTION_DEMO_ENTRIES = (
    {
        "id": "70000000-0000-0000-0000-000000000001",
        "posted_at": "2024-01-01T00:00:00+00:00",
        "lines": (
            {"account_code": "1000", "debit": Decimal("500000.0000"), "credit": Decimal("0.0000")},
            {"account_code": "3000", "debit": Decimal("0.0000"), "credit": Decimal("500000.0000")},
        ),
    },
    {
        "id": "70000000-0000-0000-0000-000000000002",
        "posted_at": "2024-01-15T00:00:00+00:00",
        "lines": (
            {"account_code": "1100", "debit": Decimal("125000.0000"), "credit": Decimal("0.0000")},
            {"account_code": "2000", "debit": Decimal("0.0000"), "credit": Decimal("125000.0000")},
        ),
    },
)


def _seed_rates(connection: Connection) -> None:
    for rate in PRODUCTION_RATES:
        connection.execute(
            text(
                """
                INSERT INTO rate_schedule (tier, annual_rate)
                VALUES (:tier, :annual_rate)
                ON CONFLICT (tier) DO UPDATE
                SET annual_rate = EXCLUDED.annual_rate, updated_at = NOW()
                """
            ),
            rate,
        )
    connection.execute(text("DELETE FROM rate_schedule WHERE tier NOT IN ('standard', 'premium', 'savings')"))


def _seed_accounts(connection: Connection) -> dict[str, UUID]:
    connection.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS rate_tier VARCHAR(50)"))
    for account in PRODUCTION_CHART_OF_ACCOUNTS:
        connection.execute(
            text(
                """
                INSERT INTO accounts
                    (id, code, name, type, normal_balance, rate_tier, active)
                VALUES
                    (:id, :code, :name, CAST(:type AS account_type), :normal_balance, :rate_tier, :active)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    normal_balance = EXCLUDED.normal_balance,
                    rate_tier = EXCLUDED.rate_tier,
                    active = EXCLUDED.active
                """
            ),
            account,
        )
    connection.execute(text("ALTER TABLE accounts ALTER COLUMN rate_tier SET NOT NULL"))
    rows = [
        (
            account["code"],
            connection.execute(
                text("SELECT id FROM accounts WHERE code = :code"),
                {"code": account["code"]},
            ).scalar_one(),
        )
        for account in PRODUCTION_CHART_OF_ACCOUNTS
    ]
    return dict(rows)


def _seed_entries(connection: Connection, account_ids: dict[str, UUID]) -> None:
    for entry in PRODUCTION_DEMO_ENTRIES:
        connection.execute(
            text(
                """
                INSERT INTO journal_entries
                    (id, status, posted_at, is_accrual)
                VALUES (:id, 'POSTED', :posted_at, FALSE)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": entry["id"], "posted_at": entry["posted_at"]},
        )
        for index, line in enumerate(entry["lines"], start=1):
            connection.execute(
                text(
                    """
                    INSERT INTO journal_lines
                        (id, entry_id, account_id, debit, credit)
                    VALUES (:id, :entry_id, :account_id, :debit, :credit)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid5(UUID(entry["id"]), f"journal-line-{index}")),
                    "entry_id": entry["id"],
                    "account_id": account_ids[line["account_code"]],
                    "debit": line["debit"],
                    "credit": line["credit"],
                },
            )


def seed_database(connection: Connection) -> None:
    """Insert or repair the complete production bootstrap in one transaction."""
    _seed_rates(connection)
    account_ids = _seed_accounts(connection)
    _seed_entries(connection, account_ids)


def main() -> None:
    """Run the explicit production seed command against DATABASE_URL."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://ledger:ledger@localhost:5432/ledger",
    ).replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            seed_database(connection)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
