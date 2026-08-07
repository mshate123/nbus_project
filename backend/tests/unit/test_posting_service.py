"""
Unit tests for posting_service.

Tests the double-entry invariant validation via the domain layer.
No DB; pure function testing through PostingService.validate_entry.
"""

import uuid
import pytest
from decimal import Decimal
from domain.money import Money
from domain.posting import PostingLine
from engine.posting_service import PostingService, PostingError


def _line(debit: str = "0", credit: str = "0", account_id=None) -> PostingLine:
    """Helper to build a PostingLine with sensible defaults."""
    return PostingLine(
        account_id=account_id or uuid.uuid4(),
        debit=Money(Decimal(debit)),
        credit=Money(Decimal(credit)),
    )


class TestPostingValidation:
    """Test entry validation."""

    @pytest.mark.asyncio
    async def test_balanced_entry_passes(self):
        """Valid balanced entry should pass validation."""
        acc1, acc2 = uuid.uuid4(), uuid.uuid4()
        lines = [
            _line(debit="100.0000", account_id=acc1),
            _line(credit="100.0000", account_id=acc2),
        ]
        # Should not raise
        await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_unbalanced_entry_fails(self):
        """Unbalanced entry should raise PostingError."""
        acc1, acc2 = uuid.uuid4(), uuid.uuid4()
        lines = [
            _line(debit="100.0000", account_id=acc1),
            _line(credit="90.0000", account_id=acc2),
        ]
        with pytest.raises(PostingError, match="balanced"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_zero_line_entry_fails(self):
        """Entry with zero lines should fail."""
        with pytest.raises(PostingError, match="at least 2 lines"):
            await PostingService.validate_entry([])

    @pytest.mark.asyncio
    async def test_single_line_entry_fails(self):
        """Single-line entry is unbalanced by definition."""
        lines = [_line(debit="100")]
        with pytest.raises(PostingError, match="at least 2 lines"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_more_than_4_decimal_places_fails(self):
        """Amount with >4 decimal places should fail at Money construction."""
        with pytest.raises(Exception, match="four decimal places"):
            _line(debit="100.00001")

    @pytest.mark.asyncio
    async def test_line_with_both_debit_and_credit_fails(self):
        """A line cannot have both debit and credit."""
        acc1, acc2 = uuid.uuid4(), uuid.uuid4()
        lines = [
            PostingLine(
                account_id=acc1,
                debit=Money(Decimal("100")),
                credit=Money(Decimal("50")),
            ),
            _line(credit="50", account_id=acc2),
        ]
        with pytest.raises(PostingError, match="one-sided"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_zero_amount_entry_fails(self):
        """Entry with all-zero lines should fail validation."""
        acc1, acc2 = uuid.uuid4(), uuid.uuid4()
        # PostingLine allows zero Money values, but validate_entry rejects
        # lines that are both-sides-zero (the domain layer's "nonzero" check).
        lines = [
            PostingLine(
                account_id=acc1,
                debit=Money(Decimal("0")),
                credit=Money(Decimal("0")),
            ),
            PostingLine(
                account_id=acc2,
                debit=Money(Decimal("0")),
                credit=Money(Decimal("0")),
            ),
        ]
        with pytest.raises(PostingError, match="nonzero"):
            await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_three_line_balanced_entry_passes(self):
        """Multi-line balanced entry should pass."""
        acc1, acc2, acc3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        lines = [
            _line(debit="100.0000", account_id=acc1),
            _line(debit="60.0000", account_id=acc2),
            _line(credit="160.0000", account_id=acc3),
        ]
        await PostingService.validate_entry(lines)

    @pytest.mark.asyncio
    async def test_decimal_precision_preserved(self):
        """Decimal amounts should maintain 4-place precision."""
        acc1, acc2 = uuid.uuid4(), uuid.uuid4()
        lines = [
            _line(debit="10.1234", account_id=acc1),
            _line(credit="10.1234", account_id=acc2),
        ]
        await PostingService.validate_entry(lines)  # Should pass
