"""
Unit tests for AccrualService.

Uses a mocked AsyncSession to exercise the actual service method
rather than just testing Decimal arithmetic in isolation.
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from engine.accrual_service import AccrualService
from models import Account, NormalBalance, AccountType, RateTier, RateSchedule


def _make_account(
    code: str = "2000",
    normal_balance: NormalBalance = NormalBalance.CREDIT,
    rate_tier: RateTier = RateTier.STANDARD,
    active: bool = True,
) -> Account:
    """Create a minimal Account for testing."""
    account = Account(
        id=uuid.uuid4(),
        code=code,
        name=f"Test {code}",
        type=AccountType.LIABILITY,
        normal_balance=normal_balance,
        rate_tier=rate_tier,
        active=active,
    )
    return account


def _make_income_account() -> Account:
    """Create the interest income account (code 4000)."""
    return Account(
        id=uuid.uuid4(),
        code="4000",
        name="Interest Income",
        type=AccountType.REVENUE,
        normal_balance=NormalBalance.CREDIT,
        rate_tier=RateTier.STANDARD,
        active=True,
    )


def _make_rate_schedule(tier: RateTier, rate: str) -> MagicMock:
    """Create a mock rate schedule row."""
    rs = MagicMock()
    rs.tier = tier
    rs.annual_rate = Decimal(rate)
    return rs


class TestAccrueInterestForDate:
    """Test AccrualService.accrue_interest_for_date with mocked session."""

    @pytest.mark.asyncio
    async def test_missing_income_account_returns_error(self):
        """If account 4000 is missing, return error without processing."""
        session = AsyncMock()
        # scalar returns None for the interest income account lookup
        session.scalar = AsyncMock(return_value=None)
        # scalars for rate schedule
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = []
        session.scalars = AsyncMock(return_value=mock_scalars_result)

        result = await AccrualService.accrue_interest_for_date(
            session, date(2026, 1, 15)
        )

        assert result["accounts_processed"] == 0
        assert "Interest income account 4000 is missing" in result["errors"]

    @pytest.mark.asyncio
    async def test_zero_balance_account_skipped(self):
        """Accounts with zero or negative balance get no accrual."""
        income = _make_income_account()
        account = _make_account(rate_tier=RateTier.STANDARD)

        session = AsyncMock()
        session.scalar = AsyncMock(return_value=income)

        # Rate schedule
        rate_scalars = MagicMock()
        rate_scalars.all.return_value = [
            _make_rate_schedule(RateTier.STANDARD, "0.035000")
        ]
        # Account list
        account_scalars = MagicMock()
        account_scalars.all.return_value = [account]

        session.scalars = AsyncMock(side_effect=[rate_scalars, account_scalars])

        # Mock BalanceService.get_balance to return 0
        with patch(
            "engine.accrual_service.BalanceService.get_balance",
            new_callable=AsyncMock,
            return_value=Decimal("0.0000"),
        ):
            result = await AccrualService.accrue_interest_for_date(
                session, date(2026, 1, 15)
            )

        assert result["accounts_processed"] == 1
        assert result["accruals_posted"] == 0

    @pytest.mark.asyncio
    async def test_successful_accrual_posts_entry(self):
        """Positive-balance account gets an interest accrual posted."""
        income = _make_income_account()
        account = _make_account(rate_tier=RateTier.PREMIUM)

        session = AsyncMock()
        session.scalar = AsyncMock(return_value=income)

        rate_scalars = MagicMock()
        rate_scalars.all.return_value = [
            _make_rate_schedule(RateTier.STANDARD, "0.035000"),
            _make_rate_schedule(RateTier.PREMIUM, "0.045000"),
        ]
        account_scalars = MagicMock()
        account_scalars.all.return_value = [account]
        session.scalars = AsyncMock(side_effect=[rate_scalars, account_scalars])

        # Savepoint context manager
        session.begin_nested = MagicMock(return_value=AsyncMock())

        with patch(
            "engine.accrual_service.BalanceService.get_balance",
            new_callable=AsyncMock,
            return_value=Decimal("100000.0000"),
        ), patch(
            "engine.accrual_service.PostingService.post_entry",
            new_callable=AsyncMock,
        ) as mock_post:
            result = await AccrualService.accrue_interest_for_date(
                session, date(2026, 1, 15)
            )

        assert result["accounts_processed"] == 1
        assert result["accruals_posted"] == 1
        assert result["errors"] == []
        # Verify post_entry was called with correct lines
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["is_accrual"] is True
        assert call_kwargs.kwargs["accrual_account_id"] == account.id

    @pytest.mark.asyncio
    async def test_integrity_error_skips_account(self):
        """IntegrityError (duplicate accrual) increments skipped count."""
        income = _make_income_account()
        account = _make_account()

        session = AsyncMock()
        session.scalar = AsyncMock(return_value=income)

        rate_scalars = MagicMock()
        rate_scalars.all.return_value = [
            _make_rate_schedule(RateTier.STANDARD, "0.035000")
        ]
        account_scalars = MagicMock()
        account_scalars.all.return_value = [account]
        session.scalars = AsyncMock(side_effect=[rate_scalars, account_scalars])

        # Make begin_nested raise IntegrityError on __aenter__
        mock_nested = AsyncMock()
        mock_nested.__aenter__ = AsyncMock(
            side_effect=IntegrityError("dup", None, None)
        )
        session.begin_nested = MagicMock(return_value=mock_nested)

        with patch(
            "engine.accrual_service.BalanceService.get_balance",
            new_callable=AsyncMock,
            return_value=Decimal("50000.0000"),
        ):
            result = await AccrualService.accrue_interest_for_date(
                session, date(2026, 1, 15)
            )

        assert result["accruals_skipped"] == 1
        assert result["accruals_posted"] == 0

    @pytest.mark.asyncio
    async def test_unexpected_error_logged_and_recorded(self):
        """Unexpected exceptions are captured in errors list."""
        income = _make_income_account()
        account = _make_account()

        session = AsyncMock()
        session.scalar = AsyncMock(return_value=income)

        rate_scalars = MagicMock()
        rate_scalars.all.return_value = [
            _make_rate_schedule(RateTier.STANDARD, "0.035000")
        ]
        account_scalars = MagicMock()
        account_scalars.all.return_value = [account]
        session.scalars = AsyncMock(side_effect=[rate_scalars, account_scalars])

        with patch(
            "engine.accrual_service.BalanceService.get_balance",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB connection lost"),
        ):
            result = await AccrualService.accrue_interest_for_date(
                session, date(2026, 1, 15)
            )

        assert result["accounts_processed"] == 1
        assert len(result["errors"]) == 1
        assert "DB connection lost" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_rate_tier_lookup_uses_account_tier(self):
        """Each account should use its own rate tier, not a hardcoded one."""
        income = _make_income_account()
        savings_account = _make_account(
            code="2100", rate_tier=RateTier.SAVINGS
        )

        session = AsyncMock()
        session.scalar = AsyncMock(return_value=income)

        rate_scalars = MagicMock()
        rate_scalars.all.return_value = [
            _make_rate_schedule(RateTier.STANDARD, "0.035000"),
            _make_rate_schedule(RateTier.SAVINGS, "0.055000"),
        ]
        account_scalars = MagicMock()
        account_scalars.all.return_value = [savings_account]
        session.scalars = AsyncMock(side_effect=[rate_scalars, account_scalars])

        session.begin_nested = MagicMock(return_value=AsyncMock())

        with patch(
            "engine.accrual_service.BalanceService.get_balance",
            new_callable=AsyncMock,
            return_value=Decimal("50000.0000"),
        ), patch(
            "engine.accrual_service.PostingService.post_entry",
            new_callable=AsyncMock,
        ) as mock_post:
            result = await AccrualService.accrue_interest_for_date(
                session, date(2026, 1, 15)
            )

        assert result["accruals_posted"] == 1
        # Verify the interest amount uses 5.5% rate, not 3.5%
        # 50000 * 0.055 / 365 = 7.5342
        lines = mock_post.call_args.args[1]
        interest_amount = next(
            l.credit.value for l in lines if l.account_id == savings_account.id
        )
        assert interest_amount == Decimal("7.5342")
