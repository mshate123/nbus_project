"""
Unit tests for pagination on balance_service.get_statement and route params.

Tests the windowing logic: running balance is computed from the full ledger,
then sliced by offset/limit. Total count is returned for client pagination.
"""

from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from engine.balance_service import BalanceService
from models import NormalBalance


def _make_account(normal_balance=NormalBalance.DEBIT):
    """Create a mock Account object."""
    account = MagicMock()
    account.id = uuid4()
    account.normal_balance = normal_balance
    return account


def _make_journal_row(debit, credit, entry_id=None, reversal_of_id=None):
    """Create a mock row matching the get_statement query shape."""
    row = MagicMock()
    row.entry_id = entry_id or uuid4()
    row.posted_at = datetime.now(timezone.utc)
    row.debit = Decimal(debit)
    row.credit = Decimal(credit)
    row.reversal_of_id = reversal_of_id
    return row


@pytest.mark.asyncio
async def test_get_statement_returns_total_count():
    """get_statement should return total line count for pagination metadata."""
    account = _make_account()
    rows = [_make_journal_row("100.0000", "0") for _ in range(5)]

    session = AsyncMock()
    session.get = AsyncMock(return_value=account)
    session.scalar = AsyncMock(return_value=5)

    # Mock the execute call that fetches the actual rows
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)

    lines, total = await BalanceService.get_statement(session, account.id)

    assert total == 5
    assert len(lines) == 5


@pytest.mark.asyncio
async def test_get_statement_limit_restricts_returned_rows():
    """limit param should restrict how many rows are returned."""
    account = _make_account()
    rows = [_make_journal_row("50.0000", "0") for _ in range(10)]

    session = AsyncMock()
    session.get = AsyncMock(return_value=account)
    session.scalar = AsyncMock(return_value=10)

    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)

    lines, total = await BalanceService.get_statement(
        session, account.id, limit=3, offset=0
    )

    assert total == 10
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_get_statement_offset_skips_rows():
    """offset param should skip leading rows."""
    account = _make_account()
    rows = [_make_journal_row(f"{(i + 1) * 10}.0000", "0") for i in range(5)]

    session = AsyncMock()
    session.get = AsyncMock(return_value=account)
    session.scalar = AsyncMock(return_value=5)

    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)

    lines, total = await BalanceService.get_statement(
        session, account.id, limit=2, offset=2
    )

    assert total == 5
    assert len(lines) == 2
    # Third row (index 2) has debit=30, running balance after 3 rows = 10+20+30=60
    assert lines[0]["debit"] == Decimal("30.0000")
    assert lines[0]["running_balance"] == Decimal("60.0000")


@pytest.mark.asyncio
async def test_get_statement_running_balance_accounts_for_prior_rows():
    """Running balance on page 2 should include the effect of page 1 rows."""
    account = _make_account(NormalBalance.DEBIT)
    # 4 rows: 100, 200, 300, 400
    rows = [_make_journal_row(f"{(i + 1) * 100}.0000", "0") for i in range(4)]

    session = AsyncMock()
    session.get = AsyncMock(return_value=account)
    session.scalar = AsyncMock(return_value=4)

    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)

    # Get page 2 (offset=2, limit=2)
    lines, total = await BalanceService.get_statement(
        session, account.id, limit=2, offset=2
    )

    assert len(lines) == 2
    # Row 3 (index 2): running = 100+200+300 = 600
    assert lines[0]["running_balance"] == Decimal("600.0000")
    # Row 4 (index 3): running = 100+200+300+400 = 1000
    assert lines[1]["running_balance"] == Decimal("1000.0000")


@pytest.mark.asyncio
async def test_get_statement_empty_account():
    """Non-existent account returns empty list and zero total."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    lines, total = await BalanceService.get_statement(session, uuid4())

    assert lines == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_statement_credit_normal_balance():
    """Credit-normal accounts compute running balance as credit - debit."""
    account = _make_account(NormalBalance.CREDIT)
    rows = [
        _make_journal_row("0", "500.0000"),
        _make_journal_row("100.0000", "0"),
    ]

    session = AsyncMock()
    session.get = AsyncMock(return_value=account)
    session.scalar = AsyncMock(return_value=2)

    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)

    lines, total = await BalanceService.get_statement(session, account.id)

    assert total == 2
    # Credit-normal: running = +500, then +500 - 100 = 400
    assert lines[0]["running_balance"] == Decimal("500.0000")
    assert lines[1]["running_balance"] == Decimal("400.0000")
