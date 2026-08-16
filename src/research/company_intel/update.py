"""
Periodic intelligence update engine.

The engine pulls candidates from providers, validates them,
deduplicates, archives raw records, and extracts point-in-time
items. Provider failures are isolated: one failing provider does
not stop the others, and the run is marked DEGRADED.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.company_intel.models import (
    CorporateIntelItem,
    UpdateEngineStatus,
)
from src.research.company_intel.sources import (
    IntelExtractor,
    IntelSourceProvider,
    IntelSourceValidator,
    candidate_to_raw_record,
    deduplicate_candidates,
)
from src.research.raw_archive import RawArchive


class PeriodicUpdateResult(BaseModel):
    """
    Result of one update cycle.

    The result is descriptive: it reports what was discovered,
    accepted, rejected, deduplicated, and extracted.
    """

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: datetime
    status: UpdateEngineStatus

    discovered_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    deduplicated_count: int = Field(ge=0)
    extracted_count: int = Field(ge=0)

    items: tuple[CorporateIntelItem, ...] = ()
    rejected_reasons: tuple[str, ...] = ()
    provider_failures: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class PeriodicUpdateEngine:
    """
    Orchestrates one intelligence update cycle for one company.
    """

    def __init__(
        self,
        *,
        providers: Sequence[IntelSourceProvider],
        validator: IntelSourceValidator | None = None,
        extractor: IntelExtractor | None = None,
        archive: RawArchive | None = None,
    ) -> None:
        self._providers = list(providers)
        self._validator = validator or IntelSourceValidator()
        self._extractor = extractor or IntelExtractor()
        self._archive = archive

    def run(
        self,
        company: str,
        *,
        as_of: datetime,
        since: datetime | None = None,
    ) -> PeriodicUpdateResult:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        discovered: list = []
        provider_failures: list[str] = []

        for provider in self._providers:
            try:
                fetched = provider.fetch(
                    company,
                    since=since,
                    as_of=as_of,
                )
                discovered.extend(fetched)
            except Exception as exc:  # noqa: BLE001 - provider isolation
                provider_failures.append(
                    f"{provider.source_name}:{type(exc).__name__}"
                )

        accepted: list = []
        rejected: list[str] = []

        for candidate in discovered:
            valid, reason = self._validator.validate(
                candidate,
                company=company,
                as_of=as_of,
            )

            if valid:
                accepted.append(candidate)
            else:
                rejected.append(
                    f"{candidate.candidate_id}: {reason}"
                )

        deduplicated, deduplicated_count = (
            deduplicate_candidates(accepted)
        )

        archive_failures: list[str] = []

        if self._archive is not None:
            for candidate in deduplicated:
                record = candidate_to_raw_record(
                    candidate,
                    retrieved_at=as_of,
                )

                if self._archive.exists(record):
                    continue

                try:
                    self._archive.save(record)
                except Exception as exc:  # noqa: BLE001 - archive isolation
                    archive_failures.append(
                        f"{candidate.candidate_id}:{type(exc).__name__}"
                    )

        items: list[CorporateIntelItem] = []

        for candidate in deduplicated:
            item = self._extractor.extract(
                candidate,
                company=company,
                as_of=as_of,
            )

            if item is not None:
                items.append(item)

        ordered_items = tuple(
            sorted(
                items,
                key=lambda i: (
                    i.available_at.isoformat()
                    if i.available_at
                    else "",
                    i.item_id,
                ),
            )
        )

        status = (
            UpdateEngineStatus.DEGRADED
            if provider_failures or archive_failures
            else UpdateEngineStatus.OK
        )

        notes: list[str] = []

        if provider_failures:
            notes.append(
                f"{len(provider_failures)} provider(s) failed; "
                "remaining providers were still processed."
            )

        if archive_failures:
            notes.append(
                f"{len(archive_failures)} raw record(s) could not "
                "be archived."
            )

        return PeriodicUpdateResult(
            company=company,
            as_of=as_of,
            status=status,
            discovered_count=len(discovered),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            deduplicated_count=deduplicated_count,
            extracted_count=len(ordered_items),
            items=ordered_items,
            rejected_reasons=tuple(
                sorted(rejected)
            ),
            provider_failures=tuple(
                sorted(provider_failures)
            ),
            notes=tuple(notes),
        )


__all__ = [
    "PeriodicUpdateEngine",
    "PeriodicUpdateResult",
]
