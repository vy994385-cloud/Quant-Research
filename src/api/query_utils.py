"""
Shared query parameter and serialization utilities for the API layer.

Canonical location for parse_as_of, normalize_horizon, utc_iso, and
related helpers. Eliminates duplication across routers and serializers.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from src.api.errors import InvalidAsOfError, InvalidHorizonError

SUPPORTED_HORIZONS = ("INTRADAY", "SWING", "LONG_TERM")

HORIZON_ALIASES: dict[str, str] = {
    "INTRADAY": "INTRADAY",
    "INTRA": "INTRADAY",
    "SWING": "SWING",
    "LONG_TERM": "LONG_TERM",
    "LONG-TERM": "LONG_TERM",
    "LONGTERM": "LONG_TERM",
}


def parse_as_of(value: str | None) -> datetime | None:
    """Parse and validate an optional as_of query parameter."""

    if value is None:
        return None

    text = value.strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise InvalidAsOfError(
            "as_of must be an ISO 8601 timestamp",
            details={"as_of": value},
        ) from None

    if parsed.tzinfo is None:
        if "T" in text:
            raise InvalidAsOfError(
                "as_of must include a timezone offset",
                details={"as_of": value},
            )

        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def normalize_horizon(horizon: str) -> str:
    """Normalize a ranking horizon string."""

    requested = horizon.strip().upper()

    normalized = HORIZON_ALIASES.get(requested)

    if normalized is None:
        raise InvalidHorizonError(
            "unsupported ranking horizon",
            details={
                "horizon": horizon,
                "supported": list(SUPPORTED_HORIZONS),
            },
        )

    return normalized


def clean_sector(value: str | None) -> str | None:
    """
    Canonical sector serialization.

    Unknown/unavailable/blank sector data is null — never a sentinel
    string or empty string. Genuine sector values are passed through
    exactly as provided.
    """

    if isinstance(value, str) and value.strip():
        return value
    return None


def company_info(
    service,
    symbol: str,
) -> dict:
    """Build a standardized company info dict."""

    return {
        "symbol": symbol,
        "company_name": service.company_name(symbol),
        "sector": clean_sector(service.company_sector(symbol)),
        "research_available": service.research_available(symbol),
    }


def utc_iso(value: datetime | date | str | None) -> str | None:
    """
    Canonical timestamp serialization for API payloads.

    - None            -> None (missing data stays null)
    - naive datetime  -> assumed UTC, normalized
    - aware datetime  -> converted to UTC ISO-8601 instant
    - date            -> plain calendar date (YYYY-MM-DD); a date has
      no time component and must not gain a fabricated midnight time
    - str             -> passed through unchanged
    """

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def company_identity(
    symbol: str,
    *,
    as_of: datetime | None = None,
) -> dict[str, str | None]:
    """
    Canonical company envelope for endpoints without a research
    service: resolves the registered display name and sector where
    known, falling back to the normalized symbol. Unknown sector is
    null — never a fabricated value.
    """

    from src.api.recorded_research import COMPANY_NAMES, COMPANY_SECTORS

    normalized = symbol.strip().upper()

    info: dict[str, str | None] = {
        "symbol": normalized,
        "company_name": COMPANY_NAMES.get(normalized, normalized),
        "sector": COMPANY_SECTORS.get(normalized),
    }

    if as_of is not None:
        info["as_of"] = utc_iso(as_of)

    return info


__all__ = [
    "HORIZON_ALIASES",
    "SUPPORTED_HORIZONS",
    "clean_sector",
    "company_identity",
    "company_info",
    "normalize_horizon",
    "parse_as_of",
    "utc_iso",
]
