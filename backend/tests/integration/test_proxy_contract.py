"""Integration checks for the backend half of the API proxy contract."""

try:
    from backend.api.routes import router
except ImportError:  # Support pytest execution from the backend directory.
    from api.routes import router


def test_backend_routes_remain_under_api_prefix() -> None:
    """The backend route table must match the path that nginx forwards unchanged."""
    assert router.prefix == "/api"
    assert any(route.path == "/api/rate-schedule" for route in router.routes)
