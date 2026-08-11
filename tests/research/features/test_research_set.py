from datetime import datetime, timezone

import pytest

from src.research.context import ResearchContext
from src.research.features.research_set import (
    ResearchFeatureSetBuilder,
)
from src.research.features.snapshot import (
    FeatureSnapshotBuilder,
)
from src.research.features.validation import (
    FeatureSnapshotValidator,
)


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def build_validation():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {"close": 100},
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    validation = FeatureSnapshotValidator().validate(
        snapshot
    )

    return snapshot, validation


def test_research_set_contains_only_usable_features():
    snapshot, validation = build_validation()

    result = ResearchFeatureSetBuilder().build(
        snapshot,
        validation,
    )

    assert all(
        feature.feature_id
        in validation.usable_features
        for feature in result.features
    )


def test_research_set_preserves_rejected_features():
    snapshot, validation = build_validation()

    result = ResearchFeatureSetBuilder().build(
        snapshot,
        validation,
    )

    assert set(result.rejected_feature_ids) == set(
        validation.rejected_features
    )


def test_research_set_get_returns_feature():
    snapshot, validation = build_validation()

    result = ResearchFeatureSetBuilder().build(
        snapshot,
        validation,
    )

    feature = result.get("market_close")

    assert feature.value == pytest.approx(100.0)


def test_research_set_unknown_feature_raises():
    snapshot, validation = build_validation()

    result = ResearchFeatureSetBuilder().build(
        snapshot,
        validation,
    )

    with pytest.raises(KeyError):
        result.get("does_not_exist")


def test_snapshot_and_validation_must_match():
    snapshot, validation = build_validation()

    wrong_validation = type(validation)(
        symbol="OTHER",
        timestamp=validation.timestamp,
        results=validation.results,
    )

    with pytest.raises(ValueError):
        ResearchFeatureSetBuilder().build(
            snapshot,
            wrong_validation,
        )


def test_research_set_counts_are_consistent():
    snapshot, validation = build_validation()

    result = ResearchFeatureSetBuilder().build(
        snapshot,
        validation,
    )

    assert (
        result.feature_count
        + result.rejected_count
        == snapshot.feature_count
    )
