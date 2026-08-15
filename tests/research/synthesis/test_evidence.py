from datetime import datetime, timezone
from decimal import Decimal

from src.research.synthesis.evidence import (
    synthesize_evidence,
)
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceType,
)


AS_OF = datetime(
    2026,
    6,
    30,
    tzinfo=timezone.utc,
)


def _evidence(
    evidence_id: str,
    symbol: str,
    direction: EvidenceDirection,
    confidence: str,
    observation_at: datetime,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        symbol=symbol,
        evidence_type=EvidenceType.FEATURE,
        title=evidence_id,
        explanation="Research evidence.",
        direction=direction,
        confidence=Decimal(confidence),
        observation_at=observation_at,
    )


def test_synthesis_keeps_only_point_in_time_evidence():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.80",
            datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.NEGATIVE,
            "0.90",
            datetime(
                2026,
                7,
                1,
                tzinfo=timezone.utc,
            ),
        ),
        _evidence(
            "E3",
            "XYZ",
            EvidenceDirection.POSITIVE,
            "0.95",
            datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
        ),
    ]

    result = synthesize_evidence(
        symbol="abc",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_id == "E1"


def test_positive_and_negative_evidence_produces_mixed():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.80",
            datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.NEGATIVE,
            "0.60",
            datetime(
                2026,
                5,
                2,
                tzinfo=timezone.utc,
            ),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert result.direction == EvidenceDirection.MIXED
    assert result.positive_count == 1
    assert result.negative_count == 1


def test_average_confidence_is_deterministic():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.80",
            datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.60",
            datetime(
                2026,
                5,
                2,
                tzinfo=timezone.utc,
            ),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert result.average_confidence == Decimal("0.70")


def test_empty_evidence_is_not_positive_or_negative():
    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=[],
    )

    assert result.direction == EvidenceDirection.MIXED
    assert result.positive_count == 0
    assert result.negative_count == 0
    assert result.average_confidence == Decimal("0")


def test_strong_positive_and_weak_negative_remains_mixed():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.99",
            datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.NEGATIVE,
            "0.10",
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert result.direction == EvidenceDirection.MIXED
    assert result.conflict_detected is True


def test_only_positive_evidence_is_positive():
    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=[
            _evidence(
                "E1",
                "ABC",
                EvidenceDirection.POSITIVE,
                "0.90",
                datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
        ],
    )

    assert result.direction == EvidenceDirection.POSITIVE
    assert result.conflict_detected is False


def test_only_negative_evidence_is_negative():
    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=[
            _evidence(
                "E1",
                "ABC",
                EvidenceDirection.NEGATIVE,
                "0.90",
                datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
        ],
    )

    assert result.direction == EvidenceDirection.NEGATIVE
    assert result.conflict_detected is False


def test_only_neutral_evidence_is_neutral():
    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=[
            _evidence(
                "E1",
                "ABC",
                EvidenceDirection.NEUTRAL,
                "0.90",
                datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
        ],
    )

    assert result.direction == EvidenceDirection.NEUTRAL
    assert result.conflict_detected is False


def test_future_evidence_is_excluded():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.90",
            datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.NEGATIVE,
            "0.90",
            datetime(2027, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert len(result.evidence) == 1
    assert result.positive_count == 1
    assert result.negative_count == 0
    assert result.direction == EvidenceDirection.POSITIVE


def test_wrong_symbol_evidence_is_excluded():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.90",
            datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        _evidence(
            "E2",
            "XYZ",
            EvidenceDirection.NEGATIVE,
            "0.90",
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert len(result.evidence) == 1
    assert result.positive_count == 1
    assert result.negative_count == 0
    assert result.conflict_detected is False


def test_conflict_flag_requires_both_directions():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.80",
            datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.NEGATIVE,
            "0.60",
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert result.conflict_detected is True
    assert result.positive_count == 1
    assert result.negative_count == 1


def test_excluded_evidence_does_not_affect_confidence():
    included = _evidence(
        "E1",
        "ABC",
        EvidenceDirection.POSITIVE,
        "0.80",
        datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    future = _evidence(
        "E2",
        "ABC",
        EvidenceDirection.NEGATIVE,
        "0.10",
        datetime(2027, 1, 1, tzinfo=timezone.utc),
    )

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=[included, future],
    )

    assert result.average_confidence == Decimal("0.80")
    assert result.positive_count == 1
    assert result.negative_count == 0


def test_weighted_confidence_is_deterministic():
    evidence = [
        _evidence(
            "E1",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.80",
            datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        _evidence(
            "E2",
            "ABC",
            EvidenceDirection.POSITIVE,
            "0.60",
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        ),
    ]

    result = synthesize_evidence(
        symbol="ABC",
        as_of=AS_OF,
        evidence=evidence,
    )

    assert result.weighted_confidence >= Decimal("0")
    assert result.weighted_confidence <= Decimal("1")
    assert result.positive_weight >= Decimal("0")
    assert result.negative_weight == Decimal("0")
