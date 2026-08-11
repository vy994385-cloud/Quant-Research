from datetime import datetime, timezone

import pytest

from src.research.context import ResearchContext
from src.research.features.snapshot import (
    FeatureSnapshotBuilder,
)
from src.research.features.models import FeatureStatus


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def test_snapshot_builder_calculates_registered_features():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {
                "close": 100,
            },
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    feature = snapshot.get("market_close")

    assert feature.value == pytest.approx(100.0)
    assert feature.status == FeatureStatus.VALID


def test_snapshot_features_are_sorted():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {
                "close": 100,
            },
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    assert snapshot.feature_ids == tuple(
        sorted(snapshot.feature_ids)
    )


def test_snapshot_unknown_feature_raises():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    with pytest.raises(KeyError):
        snapshot.get("does_not_exist")


def test_snapshot_is_point_in_time_bounded():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {
                "close": 100,
            },
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    assert all(
        feature.observation_at
        <= feature.calculated_at
        for feature in snapshot.features
    )


def test_snapshot_preserves_symbol():
    context = ResearchContext(
        symbol="test",
        timestamp=AS_OF,
        market=(
            {
                "close": 100,
            },
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    assert snapshot.symbol == "TEST"


def test_snapshot_feature_count_matches_features():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {
                "close": 100,
            },
        ),
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    assert snapshot.feature_count == len(
        snapshot.features
    )
