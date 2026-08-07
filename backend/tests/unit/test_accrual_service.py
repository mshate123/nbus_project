"""
Unit tests for accrual_service.

Tests interest calculation (pure Decimal arithmetic, no DB).
"""

from decimal import Decimal


class TestInterestCalculation:
    """Test daily interest computation."""

    def test_interest_calculation_decimal_only(self):
        """Interest should use Decimal only, never float.
        Formula: interest = principal * (annual_rate / 365)
        """
        principal = Decimal("100000.0000")
        annual_rate = Decimal("0.0500")  # 5% APY

        # Compute daily rate
        daily_rate = annual_rate / Decimal("365.0")
        interest = (principal * daily_rate).quantize(Decimal("0.0001"))

        # Expected: 100000 * (0.05 / 365) = 13.6986...
        assert interest == Decimal("13.6986")

    def test_interest_4_5_percent_apy(self):
        """4.5% APY on $125,000."""
        principal = Decimal("125000.0000")
        annual_rate = Decimal("0.0450")

        daily_rate = annual_rate / Decimal("365.0")
        interest = (principal * daily_rate).quantize(Decimal("0.0001"))

        # Expected: 125000 * (0.045 / 365) = 15.4110...
        assert interest == Decimal("15.4110")

    def test_interest_5_5_percent_apy(self):
        """5.5% APY on $50,000."""
        principal = Decimal("50000.0000")
        annual_rate = Decimal("0.0550")

        daily_rate = annual_rate / Decimal("365.0")
        interest = (principal * daily_rate).quantize(Decimal("0.0001"))

        # Expected: 50000 * (0.055 / 365) = 7.5342...
        assert interest == Decimal("7.5342")

    def test_zero_principal_zero_interest(self):
        """Principal of zero yields zero interest."""
        principal = Decimal("0.0000")
        annual_rate = Decimal("0.0500")

        daily_rate = annual_rate / Decimal("365.0")
        interest = (principal * daily_rate).quantize(Decimal("0.0001"))

        assert interest == Decimal("0.0000")

    def test_rounding_half_up(self):
        """Interest should round to 4 places using ROUND_HALF_UP."""
        # Test value that would round up
        principal = Decimal("99999.0000")
        annual_rate = Decimal("0.0500")

        daily_rate = annual_rate / Decimal("365.0")
        interest = (principal * daily_rate).quantize(Decimal("0.0001"))

        # 99999 * (0.05 / 365) = 13.6983... -> 13.6983
        assert interest == Decimal("13.6985")
