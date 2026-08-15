from datetime import date, datetime, timezone

import pytest

from src.data.company.evidence import Evidence


def make_evidence(
    *,
    available_at: datetime | None,
) -> Evidence:
    return Evidence(
        evidence_id="evidence-1",
        source_name="Example Exchange",
        source_type="REGULATORY",
        title="Corporate announcement",
        published_date=date(2026, 8, 1),
        available_at=available_at,
        retrieved_at=datetime(
            2026,
            8,
            1,
            10,
            5,
            tzinfo=timezone.utc,
        ),
        reliability_tier=1,
    )


def test_high_quality_evidence():
    evidence = make_evidence(
        available_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    assert evidence.is_high_quality


def test_evidence_requires_stable_identity():
    evidence = make_evidence(
        available_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    assert evidence.evidence_id == "evidence-1"


def test_evidence_without_available_at_is_not_pit_eligible():
    evidence = make_evidence(available_at=None)

    assert not evidence.is_point_in_time_eligible


def test_evidence_known_before_available_time_is_false():
    evidence = make_evidence(
        available_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    assert not evidence.is_known_at(
        datetime(
            2026,
            8,
            1,
            9,
            59,
            tzinfo=timezone.utc,
        )
    )


def test_evidence_known_exactly_at_available_time_is_true():
    available = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    evidence = make_evidence(available_at=available)

    assert evidence.is_known_at(available)


def test_evidence_known_after_available_time_is_true():
    evidence = make_evidence(
        available_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    assert evidence.is_known_at(
        datetime(
            2026,
            8,
            1,
            10,
            1,
            tzinfo=timezone.utc,
        )
    )


def test_missing_available_at_is_never_assumed_known():
    evidence = make_evidence(available_at=None)

    assert not evidence.is_known_at(
        datetime(
            2026,
            8,
            15,
            12,
            tzinfo=timezone.utc,
        )
    )


def test_naive_as_of_is_rejected():
    evidence = make_evidence(
        available_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    with pytest.raises(
        ValueError,
        match="as_of must be timezone-aware",
    ):
        evidence.is_known_at(
            datetime(2026, 8, 15, 12)
        )


def test_naive_available_at_is_rejected():
    evidence = make_evidence(
        available_at=datetime(2026, 8, 1, 10, 0)
    )

    with pytest.raises(
        ValueError,
        match="available_at must be timezone-aware",
    ):
        evidence.is_known_at(
            datetime(
                2026,
                8,
                15,
                12,
                tzinfo=timezone.utc,
            )
        )
