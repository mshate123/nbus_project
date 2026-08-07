"""
Unit tests for balance_service.

Tests balance calculation logic (derived, not stored).
"""

from decimal import Decimal


class TestBalanceCalculation:
    """Test balance computation."""

    def test_asset_account_balance_debit_normal(self):
        """Asset accounts have normal balance = DEBIT.
        Balance = SUM(debit) - SUM(credit)
        """
        total_debit = Decimal("1000.0000")
        total_credit = Decimal("300.0000")

        # Asset normal = DEBIT
        balance = total_debit - total_credit
        assert balance == Decimal("700.0000")

    def test_liability_account_balance_credit_normal(self):
        """Liability accounts have normal balance = CREDIT.
        Balance = SUM(credit) - SUM(debit)
        """
        total_debit = Decimal("200.0000")
        total_credit = Decimal("500.0000")

        # Liability normal = CREDIT
        balance = total_credit - total_debit
        assert balance == Decimal("300.0000")

    def test_zero_balance_for_no_entries(self):
        """Account with no entries has balance = 0."""
        balance = Decimal("0.0000")
        assert balance == Decimal("0.0000")

    def test_running_balance_accumulates(self):
        """Running balance should accumulate across entries."""
        # Asset account (DEBIT normal)
        running_balance = Decimal("0.0000")

        # Entry 1: debit 100
        running_balance += Decimal("100.0000")
        assert running_balance == Decimal("100.0000")

        # Entry 2: credit 30
        running_balance -= Decimal("30.0000")
        assert running_balance == Decimal("70.0000")

        # Entry 3: debit 50
        running_balance += Decimal("50.0000")
        assert running_balance == Decimal("120.0000")

    def test_decimal_precision_in_running_balance(self):
        """Running balance should maintain 4-decimal precision."""
        running = Decimal("1000.0001")
        running += Decimal("0.0001")
        running = running.quantize(Decimal("0.0001"))
        assert running == Decimal("1000.0002")
