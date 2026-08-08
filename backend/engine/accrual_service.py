"""Daily interest accrual engine."""

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from domain.money import Money
from domain.posting import PostingLine
from models import Account, RateSchedule, NormalBalance
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
        # Load all rate tiers into a lookup map so each account uses its own rate.
        rate_rows = (
            await session.scalars(select(RateSchedule))
        ).all()
        rate_map = {
            str(r.tier.value if hasattr(r.tier, "value") else r.tier): Decimal(str(r.annual_rate))
            for r in rate_rows
        }
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
                # Look up the rate for this account's tier; fall back to standard.
                account_tier = str(
                    account.rate_tier.value
                    if hasattr(account.rate_tier, "value")
                    else account.rate_tier
                )
                annual_rate = rate_map.get(account_tier, Decimal("0.035000"))

                balance = await BalanceService.get_balance(session, account.id)
                if balance <= 0:
                    continue
                daily_interest = (balance * annual_rate / Decimal("365")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
                if daily_interest <= 0:
                    continue

                # A liability/customer balance grows on the credit side; a debit-normal
                # balance grows on the debit side. Interest expense/income is the offset.
                if account.normal_balance == NormalBalance.CREDIT:
                    lines = [
                        PostingLine(
                            account_id=interest_income.id,
                            debit=Money(daily_interest),
                            credit=Money.zero(),
                        ),
                        PostingLine(
                            account_id=account.id,
                            debit=Money.zero(),
                            credit=Money(daily_interest),
                        ),
                    ]
                else:
                    lines = [
                        PostingLine(
                            account_id=account.id,
                            debit=Money(daily_interest),
                            credit=Money.zero(),
                        ),
                        PostingLine(
                            account_id=interest_income.id,
                            debit=Money.zero(),
                            credit=Money(daily_interest),
                        ),
                    ]

                # Savepoint isolates a duplicate from earlier successful accounts.
                async with session.begin_nested():
                    await PostingService.post_entry(
                        session,
                        lines,
                        is_accrual=True,
                        accrual_account_id=account.id,
                        accrual_date=accrual_date,
                    )
                results["accruals_posted"] += 1
            except IntegrityError:
                results["accruals_skipped"] += 1
            except Exception as exc:
                logger.error(
                    "Accrual failed for account %s (code=%s) on %s: %s",
                    account.id,
                    account.code,
                    accrual_date,
                    exc,
                    exc_info=True,
                )
                results["errors"].append(f"Account {account.code}: {exc}")

        return results
