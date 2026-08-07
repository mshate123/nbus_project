"""Typed runtime settings for the ledger services."""

import os

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings with safe local test defaults."""

    database_url: str = "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_test"
    auth_stub_token: str = "dev-token"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Load typed settings from environment variables."""
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.model_fields["database_url"].default),
            auth_stub_token=os.getenv(
                "AUTH_STUB_TOKEN", cls.model_fields["auth_stub_token"].default
            ),
        )


def get_settings() -> Settings:
    """Return settings loaded from the current process environment."""
    return Settings.from_environment()
