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

The structured envelope applies to the versioned research API
(``/api/v1/...``) — including request-validation failures (422) and
routing-level 404/405 responses. Legacy routes keep their original
FastAPI ``{"detail": ...}`` bodies for backwards compatibility.

No Python traceback or internal implementation detail is ever
exposed through these responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

V1_API_PREFIX = "/api/v1"


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


def _is_v1_request(request: Request) -> bool:
    """True when the request targets the versioned research API."""

    return request.url.path.startswith(V1_API_PREFIX)


def _structured_http_payload(exc: StarletteHTTPException) -> dict[str, Any]:
    """Map a routing-level HTTP exception onto the error contract."""

    code = "http_error"
    if exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 405:
        code = "method_not_allowed"

    message = exc.detail if isinstance(exc.detail, str) and exc.detail else {
        404: "Resource not found.",
        405: "Method not allowed.",
    }.get(exc.status_code, f"HTTP {exc.status_code}.")

    return {
        "error": {
            "code": code,
            "message": message,
            "details": {"status_code": exc.status_code},
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

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())

        if _is_v1_request(request):
            # Unified structured envelope for the v1 research API.
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "validation_error",
                        "message": "Request validation failed.",
                        "details": {"errors": errors},
                    }
                },
            )

        # Legacy routes keep FastAPI's default body verbatim.
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        headers = getattr(exc, "headers", None) or {}

        if _is_v1_request(request):
            # Routing-level misses (unknown path, wrong method) join
            # the structured envelope for v1 clients.
            return JSONResponse(
                status_code=exc.status_code,
                content=_structured_http_payload(exc),
                headers=headers,
            )

        # Legacy routes keep FastAPI's default body verbatim.
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )


__all__ = [
    "ApiError",
    "InvalidAsOfError",
    "InvalidHorizonError",
    "MalformedRequestError",
    "ResearchDataUnavailableError",
    "UnknownCompanyError",
    "V1_API_PREFIX",
    "api_error_payload",
    "register_api_error_handlers",
]
