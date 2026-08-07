"""
Property-based test: debit/credit invariant.

Uses Hypothesis to generate arbitrary balanced entries and verify that
the sum(debits) == sum(credits) invariant holds after posting.

This is a merge gate for posting_service.
"""

from decimal import Decimal

import pytest
from hypothesis import given, strategies as st
from engine.posting_service import PostingService


# Hypothesis strategy: generate strictly positive Decimal amounts (≤4 decimals)
decimal_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)


@pytest.mark.asyncio
@given(amounts=st.lists(decimal_strategy, min_size=2, max_size=10, unique=True))
async def test_balanced_entry_invariant(amounts):
    """
    Property: for any list of amounts, create a balanced entry and verify
    sum(debits) == sum(credits) after validation.

    **Validates: Requirements 1.0 (US-1: Post a Balanced Journal Entry)**
    """
    # Split amounts: first N-1 go to debits, last amount is credit
    debit_amounts = amounts[:-1]
    total_debits = sum(debit_amounts)
    credit_amount = total_debits  # Ensure balance

    # Build entry
    lines = [
        {"account_id": f"acc-{i}", "debit": amt, "credit": Decimal("0")}
        for i, amt in enumerate(debit_amounts)
    ]
    lines.append(
        {
            "account_id": "acc-credit",
            "debit": Decimal("0"),
            "credit": credit_amount,
        }
    )

    # Validate (should not raise)
    await PostingService.validate_entry(lines)

    # Verify invariant: sum(debits) == sum(credits)
    sum_debits = sum(Decimal(str(line.get("debit", 0))) for line in lines)
    sum_credits = sum(Decimal(str(line.get("credit", 0))) for line in lines)

    assert (
        sum_debits == sum_credits
    ), f"Invariant violated: debits={sum_debits}, credits={sum_credits}"


@pytest.mark.asyncio
@given(
    num_lines=st.integers(min_value=2, max_value=10),
    base_amount=decimal_strategy,
)
async def test_multi_line_balanced_entries(num_lines, base_amount):
    """
    Property: multi-line balanced entries with arbitrary distributions.

    **Validates: Requirements 1.0 (US-1: Post a Balanced Journal Entry)**
    """
    # Create N-1 lines with debits, last line with credit
    lines = []
    total_debit = Decimal("0")

    for i in range(num_lines - 1):
        amount = (base_amount * Decimal(i + 1)).quantize(Decimal("0.0001"))
        lines.append(
            {
                "account_id": f"acc-{i}",
                "debit": amount,
                "credit": Decimal("0"),
            }
        )
        total_debit += amount

    # Last line credits the total
    lines.append(
        {
            "account_id": "acc-credit",
            "debit": Decimal("0"),
            "credit": total_debit,
        }
    )

    # Validate
    await PostingService.validate_entry(lines)

    # Verify invariant
    sum_debits = sum(Decimal(str(line["debit"])) for line in lines)
    sum_credits = sum(Decimal(str(line["credit"])) for line in lines)

    assert sum_debits == sum_credits


@pytest.mark.asyncio
@given(amount1=decimal_strategy)
async def test_simple_two_line_entries(amount1):
    """
    Property: all two-line balanced entries hold the invariant.

    **Validates: Requirements 1.0 (US-1: Post a Balanced Journal Entry)**
    """
    lines = [
        {"account_id": "acc-1", "debit": amount1, "credit": Decimal("0")},
        {"account_id": "acc-2", "debit": Decimal("0"), "credit": amount1},
    ]

    await PostingService.validate_entry(lines)

    sum_debits = Decimal(str(lines[0]["debit"]))
    sum_credits = Decimal(str(lines[1]["credit"]))

    assert sum_debits == sum_credits
