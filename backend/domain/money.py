"""Decimal-only money value object used by ledger domain rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


_MAX_SCALE = 4


class MoneyValidationError(ValueError):
    """Raised when a value cannot represent ledger money."""


def _validate_decimal(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError("Money values must be Decimal instances")
    if not value.is_finite():
        raise MoneyValidationError("Money values must be finite")
    if value.as_tuple().exponent < -_MAX_SCALE:
        raise MoneyValidationError("Money values must have at most four decimal places")
    return value


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable monetary amount with exact four-place ledger precision.

    Construction is deliberately strict: floats, strings, and implicit numeric
    conversions are rejected so domain calculations cannot lose precision.
    Negative values are supported for derived balances; posting-line direction
    and non-negativity are enforced by :mod:`domain.posting`.
    """

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value)

    @property
    def amount(self) -> Decimal:
        """Compatibility alias for callers that name the value ``amount``."""
        return self.value

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0"))

    def __add__(self, other: Any) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.value + other.value)

    def __sub__(self, other: Any) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.value - other.value)

    def __neg__(self) -> Money:
        return Money(-self.value)

    def __radd__(self, other: Any) -> Money:
        if other == 0:
            return self
        return NotImplemented
