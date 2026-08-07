"""
balance_service — Derived real-time account balance calculation.

Balance is always computed as SUM(journal_lines) per account, never stored.
This eliminates drift bugs entirely.
"""

from decimal import Decimal
from typing import List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import JournalLine, Account, JournalEntry, EntryStatus


class BalanceService:
    """Compute real-time account balances from journal lines."""

    @staticmethod
    async def get_balance(session: AsyncSession, account_id: str) -> Decimal:
        """
        Compute account balance as SUM(journal_lines) at request time.

        Balance direction depends on normal_balance:
          DEBIT accounts:  SUM(debit) - SUM(credit)
          CREDIT accounts: SUM(credit) - SUM(debit)

        Returns Decimal("0.0000") if account has no entries or doesn't exist.
        """
        account = await session.get(Account, account_id)
        if not account:
            return Decimal("0.0000")

        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.debit), Decimal("0")),
                func.coalesce(func.sum(JournalLine.credit), Decimal("0")),
            )
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .where(
                and_(
                    JournalLine.account_id == account_id,
                    JournalEntry.status == EntryStatus.POSTED,
                )
            )
        )

        result = await session.execute(stmt)
        row = result.one()
        total_debit = Decimal(str(row[0]))
        total_credit = Decimal(str(row[1]))

        if account.normal_balance == "DEBIT":
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        return balance.quantize(Decimal("0.0001"))

    @staticmethod
    async def get_statement(
        session: AsyncSession,
        account_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get account statement: all POSTED entries in date order with running balance.

        Returns list of dicts with keys:
          entry_id, posted_at, debit, credit, running_balance, reversal_of_id
        """
        account = await session.get(Account, account_id)
        if not account:
            return []

        stmt = (
            select(
                JournalEntry.id.label("entry_id"),
                JournalEntry.posted_at,
                JournalLine.debit,
                JournalLine.credit,
                JournalEntry.reversal_of_id,
            )
            .select_from(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .where(
                and_(
                    JournalLine.account_id == account_id,
                    JournalEntry.status == EntryStatus.POSTED,
                )
            )
            .order_by(JournalEntry.posted_at.asc(), JournalLine.created_at.asc())
        )

        result = await session.execute(stmt)
        rows = result.all()

        statement: List[Dict[str, Any]] = []
        running_balance = Decimal("0.0000")

        for row in rows:
            debit = Decimal(str(row.debit)) if row.debit else Decimal("0.0000")
            credit = Decimal(str(row.credit)) if row.credit else Decimal("0.0000")

            if account.normal_balance == "DEBIT":
                running_balance += debit - credit
            else:
                running_balance += credit - debit

            running_balance = running_balance.quantize(Decimal("0.0001"))

            statement.append(
                {
                    "entry_id": row.entry_id,
                    "posted_at": row.posted_at,
                    "debit": debit,
                    "credit": credit,
                    "running_balance": running_balance,
                    "reversal_of_id": row.reversal_of_id,
                }
            )

        return statement
