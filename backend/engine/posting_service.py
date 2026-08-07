"""
posting_service — Core double-entry posting engine.

Invariants enforced:
1. sum(debits) == sum(credits) for every entry
2. Atomic write with row-level locks ordered by account_id (deadlock prevention)
3. Decimal precision only — no float arithmetic on money
4. Amounts must have at most 4 decimal places
"""

from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import JournalEntry, JournalLine, Account, EntryStatus


class PostingError(Exception):
    """Raised when posting validation fails."""

    pass


class PostingService:
    """Double-entry ledger posting engine."""

    @staticmethod
    async def validate_entry(lines: List[Dict[str, Any]]) -> None:
        """
        Validate journal entry lines for balance and structure.

        Raises PostingError if:
          - fewer than 2 lines
          - amounts have >4 decimal places
          - a line has both debit and credit non-zero
          - sum(debits) != sum(credits)
          - total amount is zero
        """
        if len(lines) < 2:
            raise PostingError("Entry must have at least 2 lines")

        total_debit = Decimal("0.0000")
        total_credit = Decimal("0.0000")

        for line in lines:
            debit = Decimal(str(line.get("debit", 0)))
            credit = Decimal(str(line.get("credit", 0)))

            # Validate precision: at most 4 decimal places
            if debit < 0 or credit < 0:
                raise PostingError("Amounts cannot be negative")
            if debit != 0 and debit.as_tuple().exponent < -4:
                raise PostingError("Amounts must have at most 4 decimal places")
            if credit != 0 and credit.as_tuple().exponent < -4:
                raise PostingError("Amounts must have at most 4 decimal places")

            # A single line cannot have both debit and credit
            if debit != Decimal("0") and credit != Decimal("0"):
                raise PostingError("A line cannot have both debit and credit")

            total_debit += debit
            total_credit += credit

        if total_debit != total_credit:
            raise PostingError(
                f"Entry is unbalanced: debits ({total_debit}) != credits ({total_credit})"
            )

        if total_debit == Decimal("0"):
            raise PostingError("Entry total must be greater than 0")

    @staticmethod
    async def post_entry(
        session: AsyncSession,
        lines: List[Dict[str, Any]],
        is_accrual: bool = False,
        accrual_account_id: str | None = None,
        accrual_date=None,
    ) -> JournalEntry:
        """
        Post a balanced journal entry atomically with ordered row locks.

        Acquires SELECT FOR UPDATE on accounts in ascending ID order to
        prevent deadlocks under concurrent posting.

        Returns the posted JournalEntry ORM instance.
        """
        # Validate structure and balance
        await PostingService.validate_entry(lines)

        try:
            account_ids = sorted({UUID(str(line["account_id"])) for line in lines})
        except (KeyError, ValueError, TypeError) as exc:
            raise PostingError("Each line must contain a valid account UUID") from exc

        # Acquire row-level locks on accounts in sorted order
        stmt = (
            select(Account)
            .where(Account.id.in_(account_ids))
            .with_for_update()
            .order_by(Account.id)
        )
        result = await session.execute(stmt)
        accounts_map = {str(a.id): a for a in result.scalars()}

        # Verify all accounts exist
        for aid in account_ids:
            if str(aid) not in accounts_map:
                raise PostingError(f"Account {aid} not found")

        # Create entry
        now = datetime.now(timezone.utc)
        entry = JournalEntry(
            status=EntryStatus.POSTED,
            posted_at=now,
            is_accrual=is_accrual,
            accrual_account_id=accrual_account_id,
            accrual_date=accrual_date,
        )
        session.add(entry)
        await session.flush()  # Get entry.id

        # Create journal lines
        for line_data in lines:
            jl = JournalLine(
                entry_id=entry.id,
                account_id=UUID(str(line_data["account_id"])),
                debit=Decimal(str(line_data.get("debit", 0))),
                credit=Decimal(str(line_data.get("credit", 0))),
            )
            session.add(jl)

        await session.flush()
        return entry
