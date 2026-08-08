"""Tests for pagination on /accounts and /accounts/{id}/statement endpoints."""

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import TypeAdapter

from api.schemas import AccountResponse, AccountStatementResponse, StatementLineResponse


class TestAccountStatementPaginationSchema:
    """Verify the statement response schema includes pagination metadata."""

    def test_statement_response_includes_pagination_fields(self):
        """AccountStatementResponse must carry total, limit, and offset."""
        response = AccountStatementResponse(
            account_id="00000000-0000-0000-0000-000000000001",
            lines=[],
            total=0,
            limit=100,
            offset=0,
        )
        dumped = response.model_dump()
        assert dumped["total"] == 0
        assert dumped["limit"] == 100
        assert dumped["offset"] == 0
        assert dumped["lines"] == []

    def test_statement_response_with_lines_and_pagination(self):
        """Statement response with lines preserves pagination context."""
        line = StatementLineResponse(
            entry_id="11111111-1111-1111-1111-111111111111",
            posted_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            debit="100.0000",
            credit="0.0000",
            running_balance="100.0000",
            reversal_of_id=None,
        )
        response = AccountStatementResponse(
            account_id="00000000-0000-0000-0000-000000000001",
            lines=[line],
            total=50,
            limit=10,
            offset=5,
        )
        dumped = response.model_dump()
        assert dumped["total"] == 50
        assert dumped["limit"] == 10
        assert dumped["offset"] == 5
        assert len(dumped["lines"]) == 1

    def test_statement_response_rejects_extra_fields(self):
        """Schema still forbids unexpected wrapper fields."""
        import pytest

        with pytest.raises(Exception):
            AccountStatementResponse(
                account_id="00000000-0000-0000-0000-000000000001",
                lines=[],
                total=0,
                limit=100,
                offset=0,
                data="should not be here",  # type: ignore
            )


class TestAccountsListPaginationSchema:
    """Verify accounts list schema still works (remains a plain list)."""

    def test_accounts_response_is_plain_list(self):
        """Collection endpoint returns a bare list, not paginated wrapper."""
        accounts = TypeAdapter(list[AccountResponse]).validate_python(
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "code": "1000",
                    "name": "Cash",
                    "type": "ASSET",
                    "normal_balance": "DEBIT",
                    "rate_tier": "standard",
                    "active": True,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "code": "2000",
                    "name": "Savings",
                    "type": "LIABILITY",
                    "normal_balance": "CREDIT",
                    "rate_tier": "premium",
                    "active": True,
                },
            ]
        )
        assert len(accounts) == 2
        assert isinstance(accounts, list)
