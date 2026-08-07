"""
reversal_service — Entry reversal via offsetting entries.

Rules:
- Never delete a posted entry; create a reversing entry with swapped debit/credit.
- Link via reversal_of_id.
- Reject reversal of an entry that is itself a reversal (409).
- Reject reversal of non-POSTED entries (409).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from domain.money import Money
from domain.posting import PostingLine
from models import JournalEntry, JournalLine, EntryStatus
from engine.posting_service import PostingService


class ReversalError(Exception):
    """Raised when reversal validation fails."""

    pass


class ReversalService:
    """Entry reversal engine — offsetting entries only, never deletes."""

    @staticmethod
    async def reverse_entry(
        session: AsyncSession,
        entry_id: UUID,
    ) -> JournalEntry:
        """
        Reverse a POSTED entry by creating an offsetting entry.

        Raises ReversalError if:
          - entry not found
          - entry is not POSTED
          - entry is itself a reversal
        """
        original = await session.scalar(
            select(JournalEntry).where(JournalEntry.id == entry_id).with_for_update()
        )
        if not original:
            raise ReversalError(f"Entry {entry_id} not found")

        if original.status != EntryStatus.POSTED:
            raise ReversalError(
                f"Cannot reverse entry with status {original.status.value}; must be POSTED"
            )

        if original.reversal_of_id is not None:
            raise ReversalError(
                f"Entry {entry_id} is itself a reversal — cannot reverse a reversal"
            )

        # Check if already reversed (another entry has reversal_of_id pointing here)
        existing_reversal_stmt = select(JournalEntry).where(
            JournalEntry.reversal_of_id == entry_id
        )
        existing = await session.scalar(existing_reversal_stmt)
        if existing:
            raise ReversalError(f"Entry {entry_id} has already been reversed")

        # Get original lines
        lines_stmt = select(JournalLine).where(JournalLine.entry_id == entry_id)
        original_lines = (await session.scalars(lines_stmt)).all()

        if not original_lines:
            raise ReversalError(f"Entry {entry_id} has no lines")

        # Build reversing lines: swap debit/credit
        reversing_lines = [
            PostingLine(
                account_id=line.account_id,
                debit=Money(line.credit),
                credit=Money(line.debit),
            )
            for line in original_lines
        ]

        # Post the reversing entry
        reversing_entry = await PostingService.post_entry(session, reversing_lines)

        # Link to original — the unique partial index on reversal_of_id prevents
        # concurrent double-reversals at the DB level.
        reversing_entry.reversal_of_id = original.id
        try:
            await session.flush()
        except IntegrityError:
            raise ReversalError(f"Entry {entry_id} has already been reversed")

        return reversing_entry
