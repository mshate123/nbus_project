"""Daily interest accrual engine."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Account, RateSchedule
from engine.balance_service import BalanceService
from engine.posting_service import PostingService


class AccrualService:
    """Post one balanced interest entry per active account and calendar day."""

    @staticmethod
    async def accrue_interest_for_date(
        session: AsyncSession, accrual_date: date
    ) -> dict:
        results = {
            "date": accrual_date.isoformat(),
            "accounts_processed": 0,
            "accruals_posted": 0,
            "accruals_skipped": 0,
            "errors": [],
        }

        interest_income = await session.scalar(
            select(Account).where(Account.code == "4000")
        )
        rate_row = await session.scalar(
            select(RateSchedule).where(RateSchedule.tier == "standard")
        )
        annual_rate = (
            Decimal(str(rate_row.annual_rate)) if rate_row else Decimal("0.035000")
        )
        if interest_income is None:
            results["errors"].append("Interest income account 4000 is missing")
            return results

        accounts = (
            await session.scalars(
                select(Account)
                .where(Account.active.is_(True), Account.code != "4000")
                .order_by(Account.id)
            )
        ).all()
        for account in accounts:
            results["accounts_processed"] += 1
            try:
                balance = await BalanceService.get_balance(session, str(account.id))
                if balance <= 0:
                    continue
                daily_interest = (balance * annual_rate / Decimal("365")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
                if daily_interest <= 0:
                    continue

                # A liability/customer balance grows on the credit side; a debit-normal
                # balance grows on the debit side. Interest expense/income is the offset.
                if account.normal_balance == "CREDIT":
                    lines = [
                        {
                            "account_id": str(interest_income.id),
                            "debit": daily_interest,
                            "credit": 0,
                        },
                        {
                            "account_id": str(account.id),
                            "debit": 0,
                            "credit": daily_interest,
                        },
                    ]
                else:
                    lines = [
                        {
                            "account_id": str(account.id),
                            "debit": daily_interest,
                            "credit": 0,
                        },
                        {
                            "account_id": str(interest_income.id),
                            "debit": 0,
                            "credit": daily_interest,
                        },
                    ]

                # Savepoint isolates a duplicate from earlier successful accounts.
                async with session.begin_nested():
                    await PostingService.post_entry(
                        session,
                        lines,
                        is_accrual=True,
                        accrual_account_id=str(account.id),
                        accrual_date=accrual_date,
                    )
                results["accruals_posted"] += 1
            except IntegrityError:
                results["accruals_skipped"] += 1
            except Exception as exc:
                results["errors"].append(f"Account {account.code}: {exc}")

        return results
