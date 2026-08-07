"""
Integration test: concurrency under load.

Tests the SELECT FOR UPDATE row locking mechanism.
Fires 10 simultaneous POSTs to the same account and verifies:
1. Final balance is correct (no race conditions)
2. No deadlocks occurred
3. All entries posted successfully

Requires the migrated PostgreSQL schema (alembic upgrade head).
"""

import os

import pytest
import asyncio
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
async def test_db():
    """Fixture: create test accounts in the already-migrated schema."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    import uuid

    unique = uuid.uuid4().hex[:6]

    async with session_factory() as session:
        test_account = Account(
            id=uuid.uuid4(),
            code=f"T{unique[:4]}",
            name="Test Savings",
            type=AccountType.ASSET,
            normal_balance="DEBIT",
            rate_tier="standard",
            active=True,
        )
        session.add(test_account)
        await session.commit()
        await session.refresh(test_account)

        yield session, test_account.id, session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_posts_no_deadlock(test_db):
    """
    Post 10 entries simultaneously to the same account.

    Each entry: debit test_account (amount), credit reserve account (amount).
    Expected final balance = 10 * amount (all debits succeed).
    """
    session, test_account_id, session_maker = test_db

    # Create a second account for credits
    import uuid as _uuid

    reserve = Account(
        id=_uuid.uuid4(),
        code=f"R{_uuid.uuid4().hex[:4]}",
        name="Reserve",
        type=AccountType.LIABILITY,
        normal_balance="CREDIT",
        rate_tier="standard",
        active=True,
    )
    session.add(reserve)
    await session.commit()
    await session.refresh(reserve)

    # Define concurrent posting tasks
    async def post_entry(amount: Decimal, task_id: int):
        async with session_maker() as s:
            lines = [
                PostingLine(
                    account_id=test_account_id,
                    debit=Money(amount),
                    credit=Money.zero(),
                ),
                PostingLine(
                    account_id=reserve.id,
                    debit=Money.zero(),
                    credit=Money(amount),
                ),
            ]
            try:
                entry = await PostingService.post_entry(s, lines)
                await s.commit()
                return f"Task {task_id} posted entry {entry.id}"
            except Exception:
                await s.rollback()
                raise

    # Fire 10 concurrent posts (each $100)
    amount = Decimal("100.0000")
    tasks = [post_entry(amount, i) for i in range(10)]

    # Execute all concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check results
    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"Concurrency test had errors: {errors}"

    # Verify final balance
    async with session_maker() as s:
        final_balance = await BalanceService.get_balance(s, test_account_id)

    # Asset account (DEBIT normal) should have: 10 * $100 = $1,000
    expected_balance = amount * Decimal("10")
    assert (
        final_balance == expected_balance
    ), f"Expected {expected_balance}, got {final_balance}"


@pytest.mark.asyncio
async def test_concurrent_posts_ordered_locks(test_db):
    """
    Verify that row locks are acquired in deterministic order (no deadlocks).

    This test documents that the posting_service acquires locks in ascending
    account_id order, preventing circular wait conditions.
    """
    session, test_account_id, session_maker = test_db

    # Create 3 accounts: A, B, C
    import uuid as _uuid

    accounts = []
    for i in range(3):
        acc = Account(
            id=_uuid.uuid4(),
            code=f"X{_uuid.uuid4().hex[:4]}",
            name=f"Account {i}",
            type=AccountType.ASSET,
            normal_balance="DEBIT",
            rate_tier="standard",
            active=True,
        )
        accounts.append(acc)

    async with session_maker() as s:
        for acc in accounts:
            s.add(acc)
        await s.commit()
        for acc in accounts:
            await s.refresh(acc)

    # Post entries in different orders (should still succeed due to ordered locking)
    async def post_transfer(from_idx: int, to_idx: int, amount: Decimal):
        async with session_maker() as s:
            lines = [
                PostingLine(
                    account_id=accounts[from_idx].id,
                    debit=Money(amount),
                    credit=Money.zero(),
                ),
                PostingLine(
                    account_id=accounts[to_idx].id,
                    debit=Money.zero(),
                    credit=Money(amount),
                ),
            ]
            entry = await PostingService.post_entry(s, lines)
            await s.commit()
            return entry

    # Issue transfers in various orders (should not deadlock)
    tasks = [
        post_transfer(0, 1, Decimal("50")),  # A -> B
        post_transfer(1, 2, Decimal("30")),  # B -> C
        post_transfer(
            2, 0, Decimal("20")
        ),  # C -> A (would create circular wait without ordering)
        post_transfer(0, 2, Decimal("40")),  # A -> C
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"Concurrency test had deadlock: {errors}"
