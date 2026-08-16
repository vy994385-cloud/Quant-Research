"""
Structured API error contract.

Every documented L3 failure mode is represented by a typed exception
that serializes to a consistent JSON body:

    {
      "error": {
        "code": "unknown_company",
        "message": "Human readable summary.",
        "details": { ... }
      }
    }

No Python traceback or internal implementation detail is ever
exposed through these responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """
    Base class for the structured research-API error contract.

    Subclasses define a stable machine-readable `code`, an HTTP
    `status_code`, and optional structured `details`.
    """

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message
        self.details = details or {}


class UnknownCompanyError(ApiError):
    """The requested company has no recorded research fixture."""

    status_code = 404
    code = "unknown_company"


class ResearchDataUnavailableError(ApiError):
    """The company is known, but usable research data is unavailable."""

    status_code = 404
    code = "research_data_unavailable"


class InvalidAsOfError(ApiError):
    """The supplied as_of cannot be parsed or is not timezone-aware."""

    status_code = 400
    code = "invalid_as_of"


class InvalidHorizonError(ApiError):
    """The requested ranking horizon is not supported."""

    status_code = 400
    code = "invalid_horizon"


class MalformedRequestError(ApiError):
    """The request itself is malformed."""

    status_code = 400
    code = "malformed_request"


def api_error_payload(error: ApiError) -> dict[str, Any]:
    """Serialize an ApiError into the stable error body."""

    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        }
    }


def register_api_error_handlers(app: FastAPI) -> None:
    """Register FastAPI handlers for the structured error contract."""

    @app.exception_handler(ApiError)
    async def _api_error_handler(
        request: Request,
        exc: ApiError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=api_error_payload(exc),
        )


__all__ = [
    "ApiError",
    "InvalidAsOfError",
    "InvalidHorizonError",
    "MalformedRequestError",
    "ResearchDataUnavailableError",
    "UnknownCompanyError",
    "api_error_payload",
    "register_api_error_handlers",
]
