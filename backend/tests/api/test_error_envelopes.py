"""Contract tests for the API error envelope."""

from fastapi.exceptions import RequestValidationError
from pydantic import TypeAdapter

from api.errors import ErrorEnvelope, validation_error_response


def test_validation_error_is_single_error_key() -> None:
    """Validation failures serialize to exactly one stable ``error`` key."""
    response = validation_error_response(RequestValidationError([]))

    assert response.status_code == 422
    body = response.body.decode("utf-8")
    envelope = TypeAdapter(ErrorEnvelope).validate_json(body)
    assert envelope.model_dump() == {"error": "validation error"}

    assert set(envelope.model_dump()) == {"error"}
    assert "detail" not in body


def test_error_envelope_serializes_without_wrappers() -> None:
    """The public error model cannot introduce data/items wrappers."""
    envelope = ErrorEnvelope(error="account not found")

    assert envelope.model_dump() == {"error": "account not found"}
    assert set(envelope.model_dump()) == {"error"}
