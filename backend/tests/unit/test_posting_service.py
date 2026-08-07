"""
Unit tests for posting_service.

Tests the double-entry invariant validation and atomic posting logic.
No DB; pure function testing.
"""

import pytest
from decimal import Decimal
from engine.posting_service import PostingService, PostingError


class TestPostingValidation:
    """Test entry validation."""

    @pytest.mark.asyncio
    async def test_balanced_entry_passes(self):
        """Valid balanced entry should pass validation."""
        lines = [
            {
                "account_id": "acc-1",
                "debit": Decimal("100.0000"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-2",
                "debit": Decimal("0"),
                "credit": Decimal("100.0000"),
            },
        ]
        # Should not raise
        await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_unbalanced_entry_fails(self):
        """Unbalanced entry should raise PostingError."""
        lines = [
            {
                "account_id": "acc-1",
                "debit": Decimal("100.0000"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-2",
                "debit": Decimal("0"),
                "credit": Decimal("90.0000"),
            },  # Off by 10
        ]
        with pytest.raises(PostingError, match="unbalanced"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_zero_line_entry_fails(self):
        """Entry with zero lines should fail."""
        with pytest.raises(PostingError, match="at least 2 lines"):
            await PostingService.validate_entry([])

    @pytest.mark.asyncio
    async def test_single_line_entry_fails(self):
        """Single-line entry is unbalanced by definition."""
        lines = [
            {"account_id": "acc-1", "debit": Decimal("100"), "credit": Decimal("0")},
        ]
        with pytest.raises(PostingError, match="at least 2 lines"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_more_than_4_decimal_places_fails(self):
        """Amount with >4 decimal places should fail."""
        lines = [
            {
                "account_id": "acc-1",
                "debit": Decimal("100.00001"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-2",
                "debit": Decimal("0"),
                "credit": Decimal("100.00001"),
            },
        ]
        with pytest.raises(PostingError, match="4 decimal places"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_line_with_both_debit_and_credit_fails(self):
        """A line cannot have both debit and credit."""
        lines = [
            {"account_id": "acc-1", "debit": Decimal("100"), "credit": Decimal("50")},
            {"account_id": "acc-2", "debit": Decimal("0"), "credit": Decimal("0")},
        ]
        with pytest.raises(PostingError, match="both debit and credit"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_zero_amount_entry_fails(self):
        """Entry with zero total amount should fail."""
        lines = [
            {"account_id": "acc-1", "debit": Decimal("0"), "credit": Decimal("0")},
            {"account_id": "acc-2", "debit": Decimal("0"), "credit": Decimal("0")},
        ]
        with pytest.raises(PostingError, match="greater than 0"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_three_line_balanced_entry_passes(self):
        """Multi-line balanced entry should pass."""
        lines = [
            {
                "account_id": "acc-1",
                "debit": Decimal("100.0000"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-2",
                "debit": Decimal("60.0000"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-3",
                "debit": Decimal("0"),
                "credit": Decimal("160.0000"),
            },
        ]
        await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_decimal_precision_preserved(self):
        """Decimal amounts should maintain 4-place precision."""
        lines = [
            {
                "account_id": "acc-1",
                "debit": Decimal("10.1234"),
                "credit": Decimal("0"),
            },
            {
                "account_id": "acc-2",
                "debit": Decimal("0"),
                "credit": Decimal("10.1234"),
            },
        ]
        await PostingService.validate_entry(lines)  # Should pass
