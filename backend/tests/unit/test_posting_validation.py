"""Unit tests for typed Decimal posting validation."""

from decimal import Decimal
from uuid import uuid4

import pytest

from domain.money import Money
from domain.posting import PostingLine, PostingValidationError, validate_posting


def line(*, debit: str = "0", credit: str = "0") -> PostingLine:
    return PostingLine(account_id=uuid4(), debit=Money(Decimal(debit)), credit=Money(Decimal(credit)))


def test_rejects_zero_and_both_sided_lines() -> None:
    with pytest.raises(PostingValidationError, match="one-sided|nonzero"):
        validate_posting([line(), line(credit="1")])

    with pytest.raises(PostingValidationError, match="one-sided|both"):
        validate_posting([line(debit="1", credit="1"), line(credit="1")])


def test_rejects_more_than_four_decimal_places() -> None:
    with pytest.raises(ValueError, match="four decimal places"):
        Money(Decimal("1.00001"))


def test_rejects_unbalanced_entries() -> None:
    with pytest.raises(PostingValidationError, match="balanced"):
        validate_posting([line(debit="10"), line(credit="9")])


def test_accepts_balanced_one_sided_entry() -> None:
    posting = validate_posting([line(debit="10.1250"), line(credit="10.1250")])

    assert posting.debit_total == Decimal("10.1250")
    assert posting.credit_total == Decimal("10.1250")
