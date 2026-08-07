"""Integration coverage for PostgreSQL ledger constraints.

These tests intentionally exercise the migrated database rather than metadata
``create_all`` so trigger- and index-backed invariants are covered.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, DataError, IntegrityError, InternalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import (
    Account,
    AccountType,
    EntryStatus,
    JournalEntry,
    JournalLine,
    RateSchedule,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_test"
)


@pytest.fixture
async def db_session():
    """Provide a real PostgreSQL session against the migrated schema."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def account(code: str, *, rate_tier: str = "standard") -> Account:
    return Account(
        id=uuid.uuid4(),
        code=code,
        name=f"Constraint test {code}",
        type=AccountType.ASSET,
        normal_balance="DEBIT",
        rate_tier=rate_tier,
        active=True,
    )


@pytest.mark.asyncio
async def test_rate_tier_constraint():
    """Accounts and rate schedules reject tiers outside the authoritative set."""
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Each violation needs its own session — asyncpg puts the connection into
    # an error state after a constraint failure. Using a fresh session per
    # assertion avoids needing to recover the connection.
    async with session_factory() as s:
        invalid_account = account(f"A{uuid.uuid4().hex[:9]}", rate_tier="vip")
        s.add(invalid_account)
        with pytest.raises((IntegrityError, DataError, DBAPIError)):
            await s.flush()

    async with session_factory() as s:
        invalid_schedule = RateSchedule(tier="vip", annual_rate=Decimal("0.055000"))
        s.add(invalid_schedule)
        with pytest.raises((IntegrityError, DataError, DBAPIError)):
            await s.flush()

    await engine.dispose()


@pytest.mark.asyncio
async def test_one_reversal_unique_constraint(db_session: AsyncSession):
    """Only one entry may reference a given original entry for reversal."""
    original = account(f"A{uuid.uuid4().hex[:9]}")
    db_session.add(original)
    await db_session.flush()

    source = JournalEntry(
        id=uuid.uuid4(), status=EntryStatus.POSTED, posted_at=datetime.now(timezone.utc)
    )
    first_reversal = JournalEntry(
        id=uuid.uuid4(),
        status=EntryStatus.POSTED,
        posted_at=datetime.now(timezone.utc),
        reversal_of_id=source.id,
    )
    db_session.add_all([source, first_reversal])
    await db_session.commit()

    duplicate_reversal = JournalEntry(
        id=uuid.uuid4(),
        status=EntryStatus.POSTED,
        posted_at=datetime.now(timezone.utc),
        reversal_of_id=source.id,
    )
    db_session.add(duplicate_reversal)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_one_accrual_per_account_date(db_session: AsyncSession):
    """The accrual key is unique for each account and accounting date."""
    accrual_account = account(f"A{uuid.uuid4().hex[:9]}")
    db_session.add(accrual_account)
    await db_session.flush()

    first = JournalEntry(
        id=uuid.uuid4(),
        status=EntryStatus.POSTED,
        posted_at=datetime.now(timezone.utc),
        is_accrual=True,
        accrual_account_id=accrual_account.id,
        accrual_date=date(2025, 1, 15),
    )
    db_session.add(first)
    await db_session.commit()

    duplicate = JournalEntry(
        id=uuid.uuid4(),
        status=EntryStatus.POSTED,
        posted_at=datetime.now(timezone.utc),
        is_accrual=True,
        accrual_account_id=accrual_account.id,
        accrual_date=date(2025, 1, 15),
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_posted_rows_are_immutable(db_session: AsyncSession):
    """Posted entries and their lines reject update and delete attempts."""
    debit_account = account(f"A{uuid.uuid4().hex[:9]}")
    credit_account = account(f"A{uuid.uuid4().hex[:9]}")
    db_session.add_all([debit_account, credit_account])
    await db_session.flush()

    entry = JournalEntry(
        id=uuid.uuid4(), status=EntryStatus.POSTED, posted_at=datetime.now(timezone.utc)
    )
    db_session.add(entry)
    await db_session.flush()
    line = JournalLine(
        id=uuid.uuid4(),
        entry_id=entry.id,
        account_id=debit_account.id,
        debit=Decimal("10.0000"),
        credit=Decimal("0.0000"),
    )
    db_session.add(line)
    await db_session.commit()

    # Each mutation attempt needs its own connection since asyncpg puts the
    # connection into an error state after a trigger-raised exception.
    # Must use conn.begin() so asyncpg runs inside a greenlet-aware transaction.
    engine = create_async_engine(DATABASE_URL)

    async with engine.connect() as conn:
        async with conn.begin():
            with pytest.raises((IntegrityError, InternalError)):
                await conn.execute(
                    text("UPDATE journal_entries SET posted_at = NOW() WHERE id = :id"),
                    {"id": str(entry.id)},
                )

    async with engine.connect() as conn:
        async with conn.begin():
            with pytest.raises((IntegrityError, InternalError)):
                await conn.execute(
                    text("UPDATE journal_lines SET debit = 11.0000 WHERE id = :id"),
                    {"id": str(line.id)},
                )

    async with engine.connect() as conn:
        async with conn.begin():
            with pytest.raises((IntegrityError, InternalError)):
                await conn.execute(
                    text("DELETE FROM journal_lines WHERE id = :lid"),
                    {"lid": str(line.id)},
                )

    async with engine.connect() as conn:
        async with conn.begin():
            remaining = await conn.scalar(
                text("SELECT COUNT(*) FROM journal_lines WHERE id = :id"),
                {"id": str(line.id)},
            )
            assert remaining == 1

    await engine.dispose()
