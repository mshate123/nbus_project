"""
Integration test: pagination on BalanceService.get_statement.

Verifies limit/offset work correctly and that running_balance is computed
from the start of the ledger regardless of the pagination window.

Requires the migrated PostgreSQL schema (alembic upgrade head).
"""

import os
import uuid

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from domain.money import Money
from domain.posting import PostingLine
from models import Account, AccountType
from engine.posting_service import PostingService
from engine.balance_service import BalanceService

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_test"
)


@pytest.fixture
async def pagination_db():
    """Create test accounts and post multiple entries for pagination testing."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    unique = uuid.uuid4().hex[:6]

    async with session_factory() as session:
        # Create a debit-normal account (asset) and a credit-normal offset account.
        asset_account = Account(
            id=uuid.uuid4(),
            code=f"A{unique[:4]}",
            name="Test Asset",
            type=AccountType.ASSET,
            normal_balance="DEBIT",
            rate_tier="standard",
            active=True,
        )
        offset_account = Account(
            id=uuid.uuid4(),
            code=f"L{unique[:4]}",
            name="Test Liability",
            type=AccountType.LIABILITY,
            normal_balance="CREDIT",
            rate_tier="standard",
            active=True,
        )
        session.add(asset_account)
        session.add(offset_account)
        await session.commit()
        await session.refresh(asset_account)
        await session.refresh(offset_account)

        # Post 5 entries of $100 each to the asset account.
        for i in range(5):
            lines = [
                PostingLine(
                    account_id=asset_account.id,
                    debit=Money(Decimal("100.0000")),
                    credit=Money.zero(),
                ),
                PostingLine(
                    account_id=offset_account.id,
                    debit=Money.zero(),
                    credit=Money(Decimal("100.0000")),
                ),
            ]
            await PostingService.post_entry(session, lines)
            await session.commit()

        yield session_factory, asset_account.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_statement_returns_all_when_no_pagination(pagination_db):
    """Default limit=100 returns all 5 entries."""
    session_factory, account_id = pagination_db

    async with session_factory() as session:
        lines, total = await BalanceService.get_statement(session, account_id)

    assert total == 5
    assert len(lines) == 5
    # Running balance of last entry should be 5 * 100 = 500
    assert lines[-1]["running_balance"] == Decimal("500.0000")


@pytest.mark.asyncio
async def test_statement_limit_restricts_page_size(pagination_db):
    """limit=2 returns only 2 entries."""
    session_factory, account_id = pagination_db

    async with session_factory() as session:
        lines, total = await BalanceService.get_statement(
            session, account_id, limit=2, offset=0
        )

    assert total == 5
    assert len(lines) == 2
    # First page: running balances should be 100, 200
    assert lines[0]["running_balance"] == Decimal("100.0000")
    assert lines[1]["running_balance"] == Decimal("200.0000")


@pytest.mark.asyncio
async def test_statement_offset_skips_entries(pagination_db):
    """offset=2 starts from the 3rd entry with correct running balance."""
    session_factory, account_id = pagination_db

    async with session_factory() as session:
        lines, total = await BalanceService.get_statement(
            session, account_id, limit=2, offset=2
        )

    assert total == 5
    assert len(lines) == 2
    # offset=2 means we get entries 3 and 4 (0-indexed).
    # Running balance at entry 3 = 300, entry 4 = 400.
    assert lines[0]["running_balance"] == Decimal("300.0000")
    assert lines[1]["running_balance"] == Decimal("400.0000")


@pytest.mark.asyncio
async def test_statement_offset_beyond_total_returns_empty(pagination_db):
    """offset past the total returns an empty page but correct total."""
    session_factory, account_id = pagination_db

    async with session_factory() as session:
        lines, total = await BalanceService.get_statement(
            session, account_id, limit=10, offset=100
        )

    assert total == 5
    assert len(lines) == 0


@pytest.mark.asyncio
async def test_statement_nonexistent_account_returns_empty(pagination_db):
    """Non-existent account returns empty list and total=0."""
    session_factory, _ = pagination_db

    async with session_factory() as session:
        lines, total = await BalanceService.get_statement(
            session, uuid.uuid4(), limit=10, offset=0
        )

    assert total == 0
    assert len(lines) == 0
