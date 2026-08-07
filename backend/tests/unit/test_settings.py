from fastapi.testclient import TestClient

from main import create_app
from config import Settings


def test_default_stub_token_and_test_database():
    settings = Settings()

    assert settings.auth_stub_token == "dev-token"
    assert settings.database_url == (
        "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_test"
    )


def test_health_route_shape():
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
