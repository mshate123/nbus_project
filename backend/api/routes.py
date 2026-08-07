"""
API routes for the nbus ledger.

Endpoints:
- GET  /api/accounts                        — list all accounts
- GET  /api/accounts/{id}/balance           — real-time balance
- GET  /api/accounts/{id}/statement         — statement with running balance
- POST /api/journal-entries                 — post a balanced entry
- POST /api/journal-entries/{id}/reverse    — reverse a posted entry
- GET  /api/rate-schedule                   — interest rate tiers
"""

from decimal import Decimal
from uuid import UUID
from typing import AsyncIterator, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from models import Account, RateSchedule
from engine.posting_service import PostingService, PostingError
from engine.balance_service import BalanceService
from engine.reversal_service import ReversalService, ReversalError

router = APIRouter(prefix="/api", tags=["ledger"])


# ── Session dependency ────────────────────────────────────────────────────────


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped session and roll back failed transactions.

    Route handlers own successful commits.  If a handler or commit raises, the
    exception is sent back through this dependency and any open transaction is
    rolled back before the session is closed by the context manager.
    """
    async with request.app.state.session_factory() as session:
        try:
            yield session
        except BaseException:
            # A failed flush/commit leaves an AsyncSession in a failed
            # transaction state.  Roll it back before returning the connection
            # to the pool so the next request cannot inherit that transaction.
            if session.in_transaction():
                try:
                    await session.rollback()
                except Exception:
                    # Preserve the original route/database exception.  Closing
                    # the context-managed session still returns its connection.
                    pass
            raise


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class JournalLineRequest(BaseModel):
    account_id: UUID = Field(..., description="Account UUID")
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)


class PostJournalEntryRequest(BaseModel):
    lines: List[JournalLineRequest] = Field(..., min_length=2)


class JournalLineResponse(BaseModel):
    id: str
    account_id: str
    debit: str
    credit: str

    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    id: str
    status: str
    posted_at: datetime | None
    reversal_of_id: str | None
    is_accrual: bool
    lines: List[JournalLineResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    account_id: str
    balance: str


class StatementLineResponse(BaseModel):
    entry_id: str
    posted_at: datetime
    debit: str
    credit: str
    running_balance: str
    reversal_of_id: str | None = None


class AccountStatementResponse(BaseModel):
    account_id: str
    lines: List[StatementLineResponse]


class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    type: str
    normal_balance: str
    active: bool

    class Config:
        from_attributes = True


class RateScheduleResponse(BaseModel):
    tier: str
    annual_rate: str

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(session: AsyncSession = Depends(get_session)):
    """List all accounts."""
    stmt = select(Account).order_by(Account.code)
    results = await session.scalars(stmt)
    return [
        AccountResponse(
            id=str(a.id),
            code=a.code,
            name=a.name,
            type=a.type.value,
            normal_balance=a.normal_balance,
            active=a.active,
        )
        for a in results
    ]


@router.post(
    "/journal-entries",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_journal_entry(
    req: PostJournalEntryRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Post a balanced journal entry.
    Returns 422 if unbalanced or invalid, 201 on success.
    """
    lines = [
        {
            "account_id": line.account_id,
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in req.lines
    ]

    try:
        entry = await PostingService.post_entry(session, lines)
        await session.commit()
        await session.refresh(entry, attribute_names=["journal_lines"])

        return JournalEntryResponse(
            id=str(entry.id),
            status=entry.status.value,
            posted_at=entry.posted_at,
            reversal_of_id=str(entry.reversal_of_id) if entry.reversal_of_id else None,
            is_accrual=entry.is_accrual,
            lines=[
                JournalLineResponse(
                    id=str(ln.id),
                    account_id=str(ln.account_id),
                    debit=str(ln.debit),
                    credit=str(ln.credit),
                )
                for ln in entry.journal_lines
            ],
            created_at=entry.created_at,
        )
    except PostingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.post(
    "/journal-entries/{entry_id}/reverse",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reverse_entry(
    entry_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Reverse a POSTED entry with an offsetting entry.
    Returns 409 if not reversible, 201 on success.
    """
    try:
        reversing = await ReversalService.reverse_entry(session, entry_id)
        await session.commit()
        await session.refresh(reversing, attribute_names=["journal_lines"])

        return JournalEntryResponse(
            id=str(reversing.id),
            status=reversing.status.value,
            posted_at=reversing.posted_at,
            reversal_of_id=(
                str(reversing.reversal_of_id) if reversing.reversal_of_id else None
            ),
            is_accrual=reversing.is_accrual,
            lines=[
                JournalLineResponse(
                    id=str(ln.id),
                    account_id=str(ln.account_id),
                    debit=str(ln.debit),
                    credit=str(ln.credit),
                )
                for ln in reversing.journal_lines
            ],
            created_at=reversing.created_at,
        )
    except ReversalError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_account_balance(
    account_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Real-time balance computed as SUM(journal_lines). Never cached.
    Returns zero if no entries exist.
    """
    balance = await BalanceService.get_balance(session, account_id)
    return BalanceResponse(account_id=str(account_id), balance=str(balance))


@router.get("/accounts/{account_id}/statement", response_model=AccountStatementResponse)
async def get_account_statement(
    account_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Account statement: all POSTED entries in date order with running balance.
    """
    lines = await BalanceService.get_statement(session, account_id)
    return AccountStatementResponse(
        account_id=str(account_id),
        lines=[
            StatementLineResponse(
                entry_id=str(row["entry_id"]),
                posted_at=row["posted_at"],
                debit=str(row["debit"]),
                credit=str(row["credit"]),
                running_balance=str(row["running_balance"]),
                reversal_of_id=(
                    str(row["reversal_of_id"]) if row.get("reversal_of_id") else None
                ),
            )
            for row in lines
        ],
    )


@router.get("/rate-schedule", response_model=List[RateScheduleResponse])
async def get_rate_schedule(session: AsyncSession = Depends(get_session)):
    """Return all interest rate schedule tiers."""
    stmt = select(RateSchedule).order_by(RateSchedule.tier)
    results = await session.scalars(stmt)
    return [
        RateScheduleResponse(tier=r.tier, annual_rate=str(r.annual_rate))
        for r in results
    ]
