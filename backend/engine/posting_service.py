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
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.posting import PostingLine, validate_posting, PostingValidationError
from models import JournalEntry, JournalLine, Account, EntryStatus


class PostingError(Exception):
    """Raised when posting validation fails."""

    pass


class PostingService:
    """Double-entry ledger posting engine."""

    @staticmethod
    async def validate_entry(lines: List[PostingLine]) -> None:
        """
        Validate journal entry lines for balance and structure.

        Delegates to the domain layer's strict immutable validation.
        Raises PostingError on failure.
        """
        try:
            validate_posting(lines)
        except (PostingValidationError, TypeError) as exc:
            raise PostingError(str(exc)) from exc

    @staticmethod
    async def post_entry(
        session: AsyncSession,
        lines: List[PostingLine],
        is_accrual: bool = False,
        accrual_account_id: UUID | None = None,
        accrual_date=None,
    ) -> JournalEntry:
        """
        Post a balanced journal entry atomically with ordered row locks.

        Acquires SELECT FOR UPDATE on accounts in ascending ID order to
        prevent deadlocks under concurrent posting.

        Returns the posted JournalEntry ORM instance.
        """
        # Validate structure and balance via domain layer
        await PostingService.validate_entry(lines)

        account_ids = sorted({line.account_id for line in lines})

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
        for line in lines:
            jl = JournalLine(
                entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit.value,
                credit=line.credit.value,
            )
            session.add(jl)

        await session.flush()
        return entry
