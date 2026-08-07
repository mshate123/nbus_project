"""Contract tests for direct API success response shapes."""

from pydantic import TypeAdapter

from api.schemas import (
    AccountResponse,
    AccountStatementResponse,
    BalanceResponse,
    RateScheduleResponse,
)


def test_collections_are_plain_arrays() -> None:
    """Collection response schemas validate a JSON array, not an items wrapper."""
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
            }
        ]
    )
    rates = TypeAdapter(list[RateScheduleResponse]).validate_python(
        [{"tier": "standard", "annual_rate": "0.035000"}]
    )

    assert isinstance(accounts, list)
    assert isinstance(rates, list)
    assert not isinstance(accounts, dict)
    assert not isinstance(rates, dict)


def test_resources_are_direct_objects() -> None:
    """Single-resource schemas validate the resource itself, not a data wrapper."""
    balance = BalanceResponse(
        account_id="00000000-0000-0000-0000-000000000001",
        balance="0.0000",
    )
    statement = AccountStatementResponse(
        account_id="00000000-0000-0000-0000-000000000001",
        lines=[],
    )

    assert balance.model_dump() == {
        "account_id": "00000000-0000-0000-0000-000000000001",
        "balance": "0.0000",
    }
    assert statement.model_dump() == {
        "account_id": "00000000-0000-0000-0000-000000000001",
        "lines": [],
    }
    assert "data" not in balance.model_dump()
    assert "items" not in statement.model_dump()
