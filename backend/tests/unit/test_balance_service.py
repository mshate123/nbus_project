"""
Unit tests for BalanceService.

Uses a mocked AsyncSession to exercise the actual service methods
rather than just testing Decimal arithmetic in isolation.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.balance_service import BalanceService
from models import Account, NormalBalance, AccountType, RateTier


def _make_account(
    normal_balance: NormalBalance = NormalBalance.DEBIT,
    code: str = "1000",
) -> Account:
    """Create a minimal Account object for testing."""
    account = Account(
        id=uuid.uuid4(),
        code=code,
        name=f"Test {code}",
        type=AccountType.ASSET,
        normal_balance=normal_balance,
        rate_tier=RateTier.STANDARD,
        active=True,
    )
    return account


class TestGetBalance:
    """Test BalanceService.get_balance with mocked session."""

    @pytest.mark.asyncio
    async def test_debit_normal_account_balance(self):
        """Asset (DEBIT normal): balance = SUM(debit) - SUM(credit)."""
        account = _make_account(NormalBalance.DEBIT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        # Mock the query result: total_debit=1000, total_credit=300
        mock_result = MagicMock()
        mock_result.one.return_value = (Decimal("1000.0000"), Decimal("300.0000"))
        session.execute = AsyncMock(return_value=mock_result)

        balance = await BalanceService.get_balance(session, account.id)
        assert balance == Decimal("700.0000")

    @pytest.mark.asyncio
    async def test_credit_normal_account_balance(self):
        """Liability (CREDIT normal): balance = SUM(credit) - SUM(debit)."""
        account = _make_account(NormalBalance.CREDIT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        mock_result = MagicMock()
        mock_result.one.return_value = (Decimal("200.0000"), Decimal("500.0000"))
        session.execute = AsyncMock(return_value=mock_result)

        balance = await BalanceService.get_balance(session, account.id)
        assert balance == Decimal("300.0000")

    @pytest.mark.asyncio
    async def test_nonexistent_account_returns_zero(self):
        """Non-existent account returns Decimal('0.0000')."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        balance = await BalanceService.get_balance(session, uuid.uuid4())
        assert balance == Decimal("0.0000")

    @pytest.mark.asyncio
    async def test_no_entries_returns_zero(self):
        """Account with no journal lines returns zero balance."""
        account = _make_account(NormalBalance.DEBIT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        mock_result = MagicMock()
        mock_result.one.return_value = (Decimal("0"), Decimal("0"))
        session.execute = AsyncMock(return_value=mock_result)

        balance = await BalanceService.get_balance(session, account.id)
        assert balance == Decimal("0.0000")

    @pytest.mark.asyncio
    async def test_balance_quantized_to_4_places(self):
        """Result is always quantized to 4 decimal places."""
        account = _make_account(NormalBalance.DEBIT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        # Amounts that produce a result needing quantization
        mock_result = MagicMock()
        mock_result.one.return_value = (Decimal("100.00"), Decimal("33.33"))
        session.execute = AsyncMock(return_value=mock_result)

        balance = await BalanceService.get_balance(session, account.id)
        # Should be quantized to 4 places
        assert balance.as_tuple().exponent == -4


class TestGetStatement:
    """Test BalanceService.get_statement with mocked session."""

    @pytest.mark.asyncio
    async def test_nonexistent_account_returns_empty(self):
        """Non-existent account returns empty list and zero total."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        lines, total = await BalanceService.get_statement(session, uuid.uuid4())
        assert lines == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_statement_computes_running_balance_debit_normal(self):
        """Running balance accumulates correctly for DEBIT-normal accounts."""
        account = _make_account(NormalBalance.DEBIT)
        entry_id = uuid.uuid4()

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Mock count query
        session.scalar = AsyncMock(return_value=2)

        # Mock the statement rows
        Row = MagicMock
        rows = [
            Row(entry_id=entry_id, posted_at=now, debit=Decimal("100.0000"), credit=Decimal("0"), reversal_of_id=None),
            Row(entry_id=uuid.uuid4(), posted_at=now, debit=Decimal("0"), credit=Decimal("30.0000"), reversal_of_id=None),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        session.execute = AsyncMock(return_value=mock_result)

        lines, total = await BalanceService.get_statement(session, account.id)

        assert total == 2
        assert len(lines) == 2
        assert lines[0]["running_balance"] == Decimal("100.0000")
        assert lines[1]["running_balance"] == Decimal("70.0000")

    @pytest.mark.asyncio
    async def test_statement_pagination_returns_window(self):
        """Pagination returns only the requested window of rows."""
        account = _make_account(NormalBalance.DEBIT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=account)

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        session.scalar = AsyncMock(return_value=3)

        rows = [
            MagicMock(entry_id=uuid.uuid4(), posted_at=now, debit=Decimal("100.0000"), credit=Decimal("0"), reversal_of_id=None),
            MagicMock(entry_id=uuid.uuid4(), posted_at=now, debit=Decimal("50.0000"), credit=Decimal("0"), reversal_of_id=None),
            MagicMock(entry_id=uuid.uuid4(), posted_at=now, debit=Decimal("25.0000"), credit=Decimal("0"), reversal_of_id=None),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        session.execute = AsyncMock(return_value=mock_result)

        # Request only the second row
        lines, total = await BalanceService.get_statement(
            session, account.id, limit=1, offset=1
        )

        assert total == 3
        assert len(lines) == 1
        # Running balance at offset=1 should include prior rows
        assert lines[0]["running_balance"] == Decimal("150.0000")
