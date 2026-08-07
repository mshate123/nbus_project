"""Generated test data factories.

These helpers intentionally contain no production chart, rate, or demo-entry
rows. Production bootstrap data is owned by the seed module and migrations;
tests create only the rows needed for each scenario.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

try:
    from backend.models import Account, AccountType, EntryStatus, RateSchedule
except ImportError:  # Support pytest execution from the backend directory.
    from models import Account, AccountType, EntryStatus, RateSchedule


def create_account(
    code: str,
    name: str,
    account_type: AccountType,
    normal_balance: str,
    active: bool = True,
    rate_tier: str = "standard",
) -> Account:
    """Create an isolated account for a test scenario."""
    account = Account(
        id=uuid.uuid4(),
        code=code,
        name=name,
        type=account_type,
        normal_balance=normal_balance,
        active=active,
    )
    # The rate_tier column is added by the rewrite migration. This compatibility
    # guard keeps the factory importable while earlier schema tasks are pending.
    if hasattr(Account, "rate_tier"):
        account.rate_tier = rate_tier
    return account


def create_balanced_entry(
    debit_account_code: str,
    credit_account_code: str,
    amount: Decimal,
    is_accrual: bool = False,
) -> dict[str, Any]:
    """Generate one fresh balanced entry for a test; never a production row."""
    return {
        "id": uuid.uuid4(),
        "status": EntryStatus.POSTED,
        "posted_at": datetime.now(timezone.utc),
        "is_accrual": is_accrual,
        "lines": [
            {
                "account_code": debit_account_code,
                "debit": amount,
                "credit": Decimal("0.0000"),
            },
            {
                "account_code": credit_account_code,
                "debit": Decimal("0.0000"),
                "credit": amount,
            },
        ],
    }


def create_rate_tier(tier: str, annual_rate: Decimal) -> RateSchedule:
    """Create an isolated rate row for a test scenario."""
    return RateSchedule(tier=tier, annual_rate=annual_rate)
