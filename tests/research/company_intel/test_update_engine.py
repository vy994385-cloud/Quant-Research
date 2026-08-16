from __future__ import annotations

import pytest

from src.research.company_intel import (
    IntelSourceProvider,
    PeriodicUpdateEngine,
    UpdateEngineStatus,
    candidate_to_raw_record,
)
from src.research.company_intel.models import IntelCandidate
from src.research.raw_archive import RawArchive

from .conftest import AS_OF, ts
from .test_sources import make_candidate


class FailingProvider(IntelSourceProvider):
    source_name = "failing_provider"

    def fetch(self, company, *, since, as_of):
        raise RuntimeError("provider exploded")


class EmptyProvider(IntelSourceProvider):
    source_name = "empty_provider"

    def fetch(self, company, *, since, as_of):
        return []


def test_engine_ok_status_and_counts():
    engine = PeriodicUpdateEngine(
        providers=[
            EmptyProvider(),
            EmptyProvider(),
        ],
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.status == UpdateEngineStatus.OK
    assert result.discovered_count == 0
    assert result.accepted_count == 0
    assert result.extracted_count == 0
    assert result.items == ()
    assert result.provider_failures == ()


def test_engine_extracts_and_orders_items():
    engine = PeriodicUpdateEngine(
        providers=[
            _provider(
                make_candidate(
                    candidate_id="b",
                    available_at=ts(2026, 8, 1),
                ),
                make_candidate(
                    candidate_id="a",
                    available_at=ts(2026, 7, 1),
                ),
            )
        ],
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.status == UpdateEngineStatus.OK
    assert result.discovered_count == 2
    assert result.accepted_count == 2
    assert result.extracted_count == 2
    assert [i.item_id for i in result.items] == [
        "TCS:a",
        "TCS:b",
    ]


def test_engine_filters_future_candidates_at_provider_boundary():
    engine = PeriodicUpdateEngine(
        providers=[
            _provider(
                make_candidate(
                    candidate_id="future",
                    available_at=ts(2026, 9, 1),
                ),
                make_candidate(
                    candidate_id="known",
                    available_at=ts(2026, 7, 1),
                ),
            )
        ],
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.discovered_count == 1
    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.extracted_count == 1
    assert result.items[0].item_id == "TCS:known"


def test_engine_validator_rejects_future_candidates():
    from src.research.company_intel import (
        RecordedIntelSourceProvider,
    )

    provider = RecordedIntelSourceProvider(
        [
            make_candidate(
                candidate_id="future",
                available_at=ts(2026, 9, 1),
            ),
            make_candidate(
                candidate_id="known",
                available_at=ts(2026, 7, 1),
            ),
        ],
        include_future=True,
    )

    engine = PeriodicUpdateEngine(providers=[provider])

    result = engine.run("TCS", as_of=AS_OF)

    assert result.discovered_count == 2
    assert result.accepted_count == 1
    assert result.rejected_count == 1
    assert result.extracted_count == 1
    assert result.items[0].item_id == "TCS:known"
    assert any(
        "not knowable" in reason
        for reason in result.rejected_reasons
    )


def test_engine_isolates_provider_failure():
    engine = PeriodicUpdateEngine(
        providers=[
            FailingProvider(),
            _provider(
                make_candidate(
                    candidate_id="survivor",
                    available_at=ts(2026, 7, 1),
                ),
            ),
        ],
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.status == UpdateEngineStatus.DEGRADED
    assert result.provider_failures == (
        "failing_provider:RuntimeError",
    )
    assert [i.item_id for i in result.items] == [
        "TCS:survivor"
    ]
    assert any(
        "provider(s) failed" in note
        for note in result.notes
    )


def test_engine_rejects_naive_as_of():
    engine = PeriodicUpdateEngine(providers=[EmptyProvider()])

    with pytest.raises(ValueError):
        engine.run(
            "TCS",
            as_of=AS_OF.replace(tzinfo=None),
        )


def test_engine_archives_deduplicated_candidates(tmp_path):
    archive = RawArchive(tmp_path)

    candidate = make_candidate(
        candidate_id="candidate-1",
        available_at=ts(2026, 7, 1),
    )

    engine = PeriodicUpdateEngine(
        providers=[
            _provider(candidate),
        ],
        archive=archive,
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.status == UpdateEngineStatus.OK
    assert archive.exists(
        candidate_to_raw_record(candidate, retrieved_at=AS_OF)
    )


def test_engine_skips_already_archived_candidates(tmp_path):
    archive = RawArchive(tmp_path)

    candidate = make_candidate(
        candidate_id="candidate-1",
        available_at=ts(2026, 7, 1),
    )

    engine = PeriodicUpdateEngine(
        providers=[_provider(candidate)],
        archive=archive,
    )

    first = engine.run("TCS", as_of=AS_OF)
    second = engine.run("TCS", as_of=AS_OF)

    assert first.status == UpdateEngineStatus.OK
    assert second.status == UpdateEngineStatus.OK
    assert second.extracted_count == 1
    assert archive.exists(
        candidate_to_raw_record(candidate, retrieved_at=AS_OF)
    )


def test_engine_deduplicates_between_providers():
    engine = PeriodicUpdateEngine(
        providers=[
            _provider(
                make_candidate(
                    candidate_id="dup-a",
                    title="Same story",
                    source_url="https://example.invalid/story",
                ),
            ),
            _provider(
                make_candidate(
                    candidate_id="dup-b",
                    title="Same story",
                    source_url="https://example.invalid/story",
                ),
            ),
        ],
    )

    result = engine.run("TCS", as_of=AS_OF)

    assert result.accepted_count == 2
    assert result.deduplicated_count == 1
    assert result.extracted_count == 1


def _provider(*candidates: IntelCandidate) -> IntelSourceProvider:
    from src.research.company_intel import (
        RecordedIntelSourceProvider,
    )

    return RecordedIntelSourceProvider(candidates)
