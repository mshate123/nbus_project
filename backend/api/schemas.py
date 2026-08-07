"""Pydantic schemas for the stable Ledger API contract."""

from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base schema that rejects accidental response wrapper fields."""

    model_config = ConfigDict(extra="forbid")


class JournalLineRequest(APIModel):
    account_id: UUID = Field(..., description="Account UUID")
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)


class PostJournalEntryRequest(APIModel):
    lines: List[JournalLineRequest] = Field(..., min_length=2)


class JournalLineResponse(APIModel):
    id: str
    account_id: str
    debit: str
    credit: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JournalEntryResponse(APIModel):
    id: str
    status: str
    posted_at: datetime | None
    reversal_of_id: str | None
    is_accrual: bool
    lines: List[JournalLineResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BalanceResponse(APIModel):
    account_id: str
    balance: str


class StatementLineResponse(APIModel):
    entry_id: str
    posted_at: datetime
    debit: str
    credit: str
    running_balance: str
    reversal_of_id: str | None = None


class AccountStatementResponse(APIModel):
    account_id: str
    lines: List[StatementLineResponse]


class AccountResponse(APIModel):
    id: str
    code: str
    name: str
    type: str
    normal_balance: str
    rate_tier: str
    active: bool

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class RateScheduleResponse(APIModel):
    tier: str
    annual_rate: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Collection responses are intentionally bare lists.  They are aliases rather
# than wrapper models so OpenAPI and runtime serialization expose array roots.
AccountsResponse = list[AccountResponse]
RateScheduleCollectionResponse = list[RateScheduleResponse]
