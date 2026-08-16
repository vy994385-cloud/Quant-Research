"""
Deterministic recorded company-research service.

This service exposes the existing verification/research path through a
stable, as_of-aware product contract without any live network access.

It reuses the recorded real-data verification pipeline
(src.verification.real_data) which replays captured market, financial,
and company-disclosure fixtures through the existing provider ->
archive -> acquisition -> evidence -> report architecture.

The supported-company registry is derived from the existing
COMPANIES / COMPANY_SECTORS registry rather than duplicated here.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock

from src.api.errors import (
    ResearchDataUnavailableError,
    UnknownCompanyError,
)
from src.verification.real_data import (
    COMPANIES,
    COMPANY_SECTORS,
    DEFAULT_AS_OF,
    DEFAULT_FIXTURE_DIR,
    RealDataVerificationResult,
    run_real_data_verification,
)

# The recorded fixtures cover these real companies. Names are not
# carried by the market/financial providers, so they are supplied here
# as static metadata alongside the authoritative symbol/sector registry.
COMPANY_NAMES: dict[str, str] = {
    "TCS": "Tata Consultancy Services",
    "RELIANCE": "Reliance Industries",
    "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank",
    "SUNPHARMA": "Sun Pharmaceutical Industries",
    "M&M": "Mahindra & Mahindra",
}

DEFAULT_ARCHIVE_ROOT = Path("data/raw/research_api")

_CACHE_MAX_ENTRIES = 64


def _fixture_files_for(company: str) -> tuple[str, str, str]:
    prefix = company.strip().upper().lower()

    return (
        f"{prefix}_market.csv",
        f"{prefix}_financials.json",
        f"{prefix}_sources.json",
    )


class RecordedCompanyResearchService:
    """
    Thin, deterministic facade over the recorded research path.

    Results are cached per (symbol, as_of) because the recorded
    fixtures are immutable and repeated requests are identical.
    """

    def __init__(
        self,
        *,
        archive_root: str | Path = DEFAULT_ARCHIVE_ROOT,
        fixture_dir: str | Path | None = None,
    ) -> None:
        self._archive_root = Path(archive_root)
        self._fixture_dir = Path(
            fixture_dir or DEFAULT_FIXTURE_DIR
        )

        self._cache: dict[
            tuple[str, datetime], RealDataVerificationResult
        ] = {}
        self._cache_lock = Lock()

    # ------------------------------------------------------------------
    # Company registry
    # ------------------------------------------------------------------

    @property
    def companies(self) -> tuple[str, ...]:
        return COMPANIES

    @property
    def sectors(self) -> dict[str, str]:
        return dict(COMPANY_SECTORS)

    def company_name(self, symbol: str) -> str | None:
        return COMPANY_NAMES.get(symbol.strip().upper())

    def company_sector(self, symbol: str) -> str | None:
        return COMPANY_SECTORS.get(symbol.strip().upper())

    def research_available(self, symbol: str) -> bool:
        normalized = symbol.strip().upper()

        if normalized not in COMPANY_SECTORS:
            return False

        return all(
            (self._fixture_dir / name).exists()
            for name in _fixture_files_for(normalized)
        )

    def validate_company(self, symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise UnknownCompanyError(
                "symbol cannot be empty",
                details={"symbol": symbol},
            )

        if normalized not in COMPANY_SECTORS:
            raise UnknownCompanyError(
                "unknown company",
                details={
                    "symbol": normalized,
                    "supported": list(COMPANIES),
                },
            )

        return normalized

    # ------------------------------------------------------------------
    # Research execution
    # ------------------------------------------------------------------

    def run(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        include_future_sources: bool = False,
    ) -> RealDataVerificationResult:
        normalized = self.validate_company(symbol)

        captured_at = as_of or DEFAULT_AS_OF

        if captured_at.tzinfo is None:
            from src.api.errors import InvalidAsOfError

            raise InvalidAsOfError(
                "as_of must be timezone-aware",
                details={
                    "as_of": captured_at.isoformat(),
                },
            )

        key = (normalized, captured_at)

        with self._cache_lock:
            cached = self._cache.get(key)

            if cached is not None:
                return cached

        try:
            result = run_real_data_verification(
                company=normalized,
                as_of=captured_at,
                archive_root=self._archive_root,
                fixture_dir=self._fixture_dir,
                include_future_sources=include_future_sources,
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            raise ResearchDataUnavailableError(
                f"usable research data is not available for "
                f"{normalized} at {captured_at.isoformat()}",
                details={
                    "symbol": normalized,
                    "as_of": captured_at.isoformat(),
                },
            ) from exc

        with self._cache_lock:
            if key not in self._cache:
                if len(self._cache) >= _CACHE_MAX_ENTRIES:
                    oldest = next(
                        iter(self._cache),
                    )
                    self._cache.pop(oldest)

                self._cache[key] = result

        return result


__all__ = [
    "COMPANY_NAMES",
    "DEFAULT_ARCHIVE_ROOT",
    "RecordedCompanyResearchService",
]
