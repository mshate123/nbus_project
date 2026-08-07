"""SQLAlchemy 2 ORM models for the append-only double-entry ledger."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum


class Base(DeclarativeBase):
    """Declarative base shared by the application and Alembic."""


class AccountType(str, PyEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class NormalBalance(str, PyEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class RateTier(str, PyEnum):
    STANDARD = "standard"
    PREMIUM = "premium"
    SAVINGS = "savings"


class EntryStatus(str, PyEnum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"


def _enum_values(enum_type: type[PyEnum]) -> list[str]:
    """Persist enum values, including the lowercase authoritative rate tiers."""
    return [member.value for member in enum_type]


ACCOUNT_TYPE = SQLEnum(
    AccountType,
    name="account_type",
    values_callable=_enum_values,
    native_enum=True,
    create_constraint=False,
)
NORMAL_BALANCE = SQLEnum(
    NormalBalance,
    name="normal_balance",
    values_callable=_enum_values,
    native_enum=True,
    create_constraint=False,
)
RATE_TIER = SQLEnum(
    RateTier,
    name="rate_tier",
    values_callable=_enum_values,
    native_enum=True,
    create_constraint=False,
)
ENTRY_STATUS = SQLEnum(
    EntryStatus,
    name="entry_status",
    values_callable=_enum_values,
    native_enum=True,
    create_constraint=False,
)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "normal_balance IN ('DEBIT', 'CREDIT')",
            name="ck_account_normal_balance",
        ),
        CheckConstraint(
            "rate_tier IN ('standard', 'premium', 'savings')",
            name="ck_account_rate_tier",
        ),
        Index("ix_accounts_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[AccountType] = mapped_column(ACCOUNT_TYPE)
    normal_balance: Mapped[NormalBalance] = mapped_column(NORMAL_BALANCE)
    rate_tier: Mapped[RateTier] = mapped_column(
        RATE_TIER, default=RateTier.STANDARD, server_default="standard"
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    journal_lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="account"
    )
    accrual_entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="accrual_account", foreign_keys="JournalEntry.accrual_account_id"
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "(is_accrual = false AND accrual_account_id IS NULL AND accrual_date IS NULL) "
            "OR (is_accrual = true AND accrual_account_id IS NOT NULL AND accrual_date IS NOT NULL)",
            name="ck_accrual_fields_consistent",
        ),
        CheckConstraint(
            "(status = 'POSTED' AND posted_at IS NOT NULL) OR status = 'DRAFT'",
            name="ck_posted_entry_has_timestamp",
        ),
        Index(
            "uq_reversal_of_id",
            "reversal_of_id",
            unique=True,
            postgresql_where=text("reversal_of_id IS NOT NULL"),
        ),
        Index(
            "uq_accrual_per_account_day",
            "accrual_account_id",
            "accrual_date",
            unique=True,
            postgresql_where=text("is_accrual = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[EntryStatus] = mapped_column(
        ENTRY_STATUS, default=EntryStatus.DRAFT, server_default="DRAFT", index=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    is_accrual: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), index=True
    )
    accrual_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    accrual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    journal_lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    reversal_entry: Mapped["JournalEntry | None"] = relationship(
        remote_side="JournalEntry.id", foreign_keys=[reversal_of_id]
    )
    accrual_account: Mapped[Account | None] = relationship(
        back_populates="accrual_entries", foreign_keys=[accrual_account_id]
    )


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "debit >= 0 AND credit >= 0", name="ck_journal_line_nonnegative"
        ),
        CheckConstraint(
            "NOT (debit > 0 AND credit > 0)", name="ck_journal_line_one_side"
        ),
        CheckConstraint(
            "debit > 0 OR credit > 0", name="ck_journal_line_nonzero"
        ),
        Index("ix_journal_lines_entry_id", "entry_id"),
        Index("ix_journal_lines_account_id", "account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), index=True
    )
    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), server_default="0.0000"
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), server_default="0.0000"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entry: Mapped[JournalEntry] = relationship(back_populates="journal_lines")
    account: Mapped[Account] = relationship(back_populates="journal_lines")


class RateSchedule(Base):
    __tablename__ = "rate_schedule"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('standard', 'premium', 'savings')",
            name="ck_rate_schedule_tier",
        ),
        CheckConstraint("annual_rate >= 0", name="ck_rate_schedule_nonnegative"),
    )

    tier: Mapped[RateTier] = mapped_column(RATE_TIER, primary_key=True)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
