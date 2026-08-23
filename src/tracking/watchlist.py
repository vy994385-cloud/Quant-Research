"""
Watchlist / tracked-companies foundation.

A watchlist is a named, ordered set of tracked companies. The
evaluation is deterministic and read-only: for every symbol it
summarizes the current research state (coverage, freshness, gaps,
PIT status) plus the cross-domain change counts from the existing
tracking foundation.

Watchlists and their evaluations serialize deterministically so a
client can save research context and reproduce it later. No
persistence layer is introduced here; no price-alert or ranking
logic exists in this module.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field

from src.tracking.research_changes import build_research_change_result


class WatchlistSpec(BaseModel):
    """A named watchlist of tracked companies."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    symbols: tuple[str, ...] = Field(min_length=1)
    notes: str = ""

    @classmethod
    def create(
        cls,
        *,
        name: str,
        symbols: tuple[str, ...] | list[str],
        notes: str = "",
        validate_symbol=None,
    ) -> "WatchlistSpec":
        """
        Build a watchlist with normalized, deduplicated symbols.

        `validate_symbol` (optional) normalizes/validates each symbol
        against the company registry.
        """

        if not name.strip():
            raise ValueError("watchlist name cannot be empty")

        if not symbols:
            raise ValueError("watchlist requires at least one symbol")

        normalized: list[str] = []
        seen: set[str] = set()

        for raw in symbols:
            symbol = (
                validate_symbol(raw)
                if validate_symbol is not None
                else raw.strip().upper()
            )

            if not symbol:
                raise ValueError("watchlist symbols cannot be empty")

            if symbol in seen:
                continue

            seen.add(symbol)
            normalized.append(symbol)

        return cls(
            name=name.strip(),
            symbols=tuple(normalized),
            notes=notes,
        )


class TrackedCompanySummary(BaseModel):
    """One tracked company's research-state summary."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    sector: str | None = None
    research_available: bool = False

    intel_item_count: int = 0
    financial_period_count: int = 0

    latest_published_at: datetime | None = None
    days_since_latest_published: int | None = None

    stale_source_count: int = 0
    gap_coverage_score: str | None = None
    pit_checks_passed: bool | None = None

    significant_change_count: int = 0
    notable_change_count: int = 0
    info_change_count: int = 0


class WatchlistEvaluation(BaseModel):
    """
    Deterministic evaluation of one watchlist at one point in time.

    Point-in-time pure: every number was computable from data that
    was knowable at as_of.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    as_of: datetime
    notes: str = ""

    tracked: tuple[TrackedCompanySummary, ...] = ()
    unavailable_symbols: tuple[str, ...] = ()

    tracked_count: int = 0

    @classmethod
    def from_summaries(
        cls,
        *,
        name: str,
        as_of: datetime,
        tracked: tuple[TrackedCompanySummary, ...],
        unavailable_symbols: tuple[str, ...],
        notes: str = "",
    ) -> "WatchlistEvaluation":
        return cls(
            name=name,
            as_of=as_of,
            notes=notes,
            tracked=tuple(tracked),
            unavailable_symbols=tuple(unavailable_symbols),
            tracked_count=len(tracked),
        )


def _summary_for_result(result, service) -> TrackedCompanySummary:
    """Build one tracked-company summary from a research result."""

    intel = result.intelligence

    summary = TrackedCompanySummary(
        symbol=result.company,
        company_name=service.company_name(result.company),
        sector=service.company_sector(result.company),
        research_available=True,
    )

    if intel is None:
        return summary

    summary.intel_item_count = len(intel.items)

    fi = intel.financial_intelligence
    if fi is not None:
        summary.financial_period_count = fi.period_count

    status = intel.status
    if status is not None:
        summary.latest_published_at = status.freshness.latest_published_at
        summary.days_since_latest_published = (
            status.freshness.days_since_latest_published
        )

    summary.stale_source_count = sum(
        1 for source in intel.source_statuses if source.stale
    )

    gaps = intel.research_gaps
    if gaps is not None:
        summary.gap_coverage_score = gaps.coverage_score

    bool_checks = [
        value
        for value in (result.pit_checks or {}).values()
        if isinstance(value, bool)
    ]
    summary.pit_checks_passed = all(bool_checks) if bool_checks else None

    tracking = build_research_change_result(result, result.as_of)
    summary.significant_change_count = tracking.significant_count
    summary.notable_change_count = tracking.notable_count
    summary.info_change_count = max(
        0,
        tracking.change_count
        - tracking.significant_count
        - tracking.notable_count,
    )

    return summary


class WatchlistEvaluator:
    """
    Evaluates watchlists against the recorded research service.

    The evaluator holds no mutable state beyond the service cache;
    repeated evaluations with identical inputs are identical.
    """

    def __init__(self, service) -> None:
        self._service = service
        self._lock = Lock()

    @property
    def service(self):
        return self._service

    def evaluate_spec(
        self,
        spec: WatchlistSpec,
        *,
        as_of: datetime | None = None,
    ) -> WatchlistEvaluation:
        from src.verification.real_data import DEFAULT_AS_OF

        captured_at = as_of or DEFAULT_AS_OF

        tracked: list[TrackedCompanySummary] = []
        unavailable: list[str] = []

        for symbol in spec.symbols:
            try:
                normalized = self._service.validate_company(symbol)
            except Exception:
                unavailable.append(symbol.strip().upper())
                continue

            if not self._service.research_available(normalized):
                unavailable.append(normalized)
                continue

            result = self._service.run(normalized, as_of=captured_at)
            tracked.append(_summary_for_result(result, self._service))

        notes = ""
        if unavailable:
            notes = (
                f"{len(unavailable)} symbol(s) have no recorded "
                f"research and are excluded."
            )

        return WatchlistEvaluation.from_summaries(
            name=spec.name,
            as_of=captured_at,
            tracked=tuple(tracked),
            unavailable_symbols=tuple(unavailable),
            notes=notes,
        )

    def evaluate_symbols(
        self,
        symbols: tuple[str, ...] | list[str],
        *,
        name: str = "ad-hoc",
        as_of: datetime | None = None,
    ) -> WatchlistEvaluation:
        spec = WatchlistSpec.create(
            name=name,
            symbols=symbols,
            validate_symbol=self._safe_validate,
        )
        return self.evaluate_spec(spec, as_of=as_of)

    def _safe_validate(self, raw: str) -> str:
        try:
            return self._service.validate_company(raw)
        except Exception:
            return raw.strip().upper()


__all__ = [
    "TrackedCompanySummary",
    "WatchlistEvaluation",
    "WatchlistEvaluator",
    "WatchlistSpec",
]
