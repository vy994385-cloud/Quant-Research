from datetime import datetime, timezone

import pytest

from src.research.acquisition.models import SourceCandidate
from src.research.acquisition.validator import SourceValidator


AS_OF = datetime(
    2026,
    8,
    15,
    12,
    tzinfo=timezone.utc,
)


def make_source(**overrides) -> SourceCandidate:
    values = {
        "source_id": "source-1",
        "source_name": "Example Source",
        "source_type": "REGULATORY",
        "url": "https://example.com/source-1",
        "title": "Example filing",
        "available_at": datetime(
            2026,
            8,
            10,
            12,
            tzinfo=timezone.utc,
        ),
        "reliability_tier": 1,
    }

    values.update(overrides)
    return SourceCandidate(**values)


def test_valid_source_is_accepted():
    validator = SourceValidator()

    assert validator.validate(
        make_source(),
        AS_OF,
    )


def test_missing_availability_is_rejected():
    validator = SourceValidator()

    assert not validator.validate(
        make_source(available_at=None),
        AS_OF,
    )


def test_future_source_is_rejected():
    validator = SourceValidator()

    assert not validator.validate(
        make_source(
            available_at=datetime(
                2026,
                8,
                16,
                12,
                tzinfo=timezone.utc,
            )
        ),
        AS_OF,
    )


def test_future_publication_is_rejected():
    validator = SourceValidator()

    assert not validator.validate(
        make_source(
            published_at=datetime(
                2026,
                8,
                16,
                12,
                tzinfo=timezone.utc,
            )
        ),
        AS_OF,
    )


def test_naive_as_of_is_rejected():
    validator = SourceValidator()

    with pytest.raises(
        ValueError,
        match="as_of must be timezone-aware",
    ):
        validator.validate(
            make_source(),
            datetime(2026, 8, 15, 12),
        )


def test_naive_available_at_is_rejected():
    validator = SourceValidator()

    assert not validator.validate(
        make_source(
            available_at=datetime(
                2026,
                8,
                10,
                12,
            )
        ),
        AS_OF,
    )


def test_naive_published_at_is_rejected():
    validator = SourceValidator()

    assert not validator.validate(
        make_source(
            published_at=datetime(
                2026,
                8,
                10,
                12,
            )
        ),
        AS_OF,
    )


def test_validate_many_removes_duplicates():
    validator = SourceValidator()

    sources = [
        make_source(),
        make_source(),
        make_source(
            source_id="source-2",
            title="Second filing",
        ),
    ]

    accepted = validator.validate_many(
        sources,
        AS_OF,
    )

    assert [source.source_id for source in accepted] == [
        "source-1",
        "source-2",
    ]


def test_rejected_source_does_not_become_negative_evidence():
    validator = SourceValidator()

    rejected = validator.validate(
        make_source(available_at=None),
        AS_OF,
    )

    assert rejected is False
