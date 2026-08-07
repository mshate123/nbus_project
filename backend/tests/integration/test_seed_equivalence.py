"""Integration-level checks for production seed ownership and equivalence."""

import inspect

try:
    from backend import seed
    from backend.tests.fixtures import factories
except ImportError:  # The backend image copies this package into /app.
    import seed
    from tests.fixtures import factories


EXPECTED_RATES = {
    "standard": "0.035000",
    "premium": "0.045000",
    "savings": "0.050000",
}
EXPECTED_TIERS = set(EXPECTED_RATES)


def test_production_seed_has_three_rates_and_chart():
    """Production bootstrap exposes exactly the authoritative rates and a usable chart."""
    rates = {
        item["tier"]: format(item["annual_rate"], "f")
        for item in seed.PRODUCTION_RATES
    }

    assert rates == EXPECTED_RATES
    assert seed.PRODUCTION_CHART_OF_ACCOUNTS
    assert {item["rate_tier"] for item in seed.PRODUCTION_CHART_OF_ACCOUNTS} <= EXPECTED_TIERS
    assert len({item["code"] for item in seed.PRODUCTION_CHART_OF_ACCOUNTS}) == len(
        seed.PRODUCTION_CHART_OF_ACCOUNTS
    )
    for account in seed.PRODUCTION_CHART_OF_ACCOUNTS:
        assert {
            "code",
            "name",
            "type",
            "normal_balance",
            "rate_tier",
            "active",
        } <= account.keys()


def test_seed_entries_are_balanced():
    """Every deterministic demo entry has equal Decimal debit and credit totals."""
    assert seed.PRODUCTION_DEMO_ENTRIES

    for entry in seed.PRODUCTION_DEMO_ENTRIES:
        debit_total = sum((line["debit"] for line in entry["lines"]), seed.Decimal("0"))
        credit_total = sum((line["credit"] for line in entry["lines"]), seed.Decimal("0"))
        assert len(entry["lines"]) >= 2
        assert debit_total == credit_total
        assert debit_total > seed.Decimal("0")


def test_factory_does_not_define_production_seed_truth():
    """Test factories generate isolated data and do not define or import production rows."""
    factory_source = inspect.getsource(factories)

    assert not hasattr(factories, "CHART_OF_ACCOUNTS")
    assert not hasattr(factories, "RATE_SCHEDULE")
    assert not hasattr(factories, "DEMO_JOURNAL_ENTRIES")
    assert "backend.seed" not in factory_source
    assert "from seed" not in factory_source
    assert factories.create_balanced_entry("test-debit", "test-credit", seed.Decimal("1.0000"))[
        "lines"
    ]
