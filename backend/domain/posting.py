"""Typed, pure validation for balanced double-entry postings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from .money import Money


class PostingValidationError(ValueError):
    """Raised when a journal posting violates a domain invariant."""


@dataclass(frozen=True, slots=True)
class PostingLine:
    """One account line; a valid line has exactly one positive side."""

    account_id: UUID
    debit: Money = field(default_factory=Money.zero)
    credit: Money = field(default_factory=Money.zero)

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, UUID):
            raise TypeError("Posting line account_id must be a UUID")
        object.__setattr__(self, "debit", _as_money(self.debit, "debit"))
        object.__setattr__(self, "credit", _as_money(self.credit, "credit"))


@dataclass(frozen=True, slots=True)
class Posting:
    """An immutable validated posting and its exact Decimal totals."""

    lines: tuple[PostingLine, ...]
    debit_total: Decimal = field(init=False)
    credit_total: Decimal = field(init=False)

    def __post_init__(self) -> None:
        lines = tuple(self.lines)
        debit_total, credit_total = _validate_lines(lines)
        object.__setattr__(self, "lines", lines)
        object.__setattr__(self, "debit_total", debit_total)
        object.__setattr__(self, "credit_total", credit_total)


def _as_money(value: Any, side: str) -> Money:
    if isinstance(value, Money):
        return value
    if isinstance(value, Decimal):
        return Money(value)
    raise TypeError(f"Posting line {side} must be a Money or Decimal value")


def _validate_lines(lines: tuple[PostingLine, ...]) -> tuple[Decimal, Decimal]:
    if len(lines) < 2:
        raise PostingValidationError("A posting must contain at least 2 lines")

    debit_total = Decimal("0")
    credit_total = Decimal("0")
    for line in lines:
        if not isinstance(line, PostingLine):
            raise TypeError("Posting lines must be PostingLine instances")

        debit = line.debit.value
        credit = line.credit.value
        if debit < 0 or credit < 0:
            raise PostingValidationError("Posting line amounts cannot be negative")
        if debit == 0 and credit == 0:
            raise PostingValidationError("Posting lines must be nonzero")
        if debit != 0 and credit != 0:
            raise PostingValidationError("Posting lines must be one-sided")

        debit_total += debit
        credit_total += credit

    if debit_total == 0 or credit_total == 0:
        raise PostingValidationError("A posting must have a nonzero total")
    if debit_total != credit_total:
        raise PostingValidationError(
            f"Posting must be balanced: debits ({debit_total}) != credits ({credit_total})"
        )
    return debit_total, credit_total


def validate_posting(lines: Sequence[PostingLine]) -> Posting:
    """Validate and return an immutable posting with exact Decimal totals."""
    if isinstance(lines, (str, bytes)):
        raise TypeError("Posting lines must be a sequence of PostingLine instances")
    return Posting(tuple(lines))


# The domain name used by some application callers is journal entry validation.
validate_entry = validate_posting
