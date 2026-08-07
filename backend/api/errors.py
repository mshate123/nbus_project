"""Stable error responses for the Ledger API."""

from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorEnvelope(BaseModel):
    """The sole public JSON shape for an API error."""

    model_config = ConfigDict(extra="forbid")

    error: str


def error_response(status_code: int, message: str) -> JSONResponse:
    """Serialize an application error without ``detail`` or wrapper keys."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(error=message).model_dump(mode="json"),
    )


def validation_error_response(exc: RequestValidationError) -> JSONResponse:
    """Normalize framework validation failures to the stable 422 envelope."""
    return error_response(status_code=422, message="validation error")


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """FastAPI-compatible handler for malformed paths and request bodies."""
    return validation_error_response(exc)


def error_body(message: str) -> Mapping[str, Any]:
    """Return the validated envelope body for callers that need JSON content."""
    return ErrorEnvelope(error=message).model_dump(mode="json")
