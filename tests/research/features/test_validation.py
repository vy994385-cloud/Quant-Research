from datetime import datetime, timezone

from src.research.context import ResearchContext
from src.research.features.models import FeatureStatus
from src.research.features.snapshot import FeatureSnapshotBuilder
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


def test_valid_features_are_research_ready():
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

    assert "market_close" in validation.usable_features


def test_missing_features_are_rejected():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
    )

    snapshot = FeatureSnapshotBuilder().build(context)

    validation = FeatureSnapshotValidator().validate(
        snapshot
    )

    market_close = next(
        result
        for result in validation.results
        if result.feature_id == "market_close"
    )

    assert market_close.usable is False
    assert market_close.status == FeatureStatus.MISSING


def test_validation_counts_are_consistent():
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

    assert (
        validation.usable_count
        + validation.rejected_count
        == snapshot.feature_count
    )
