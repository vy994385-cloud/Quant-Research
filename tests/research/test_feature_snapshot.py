from datetime import datetime, timezone

import pytest

from src.research.context import ResearchContext
from src.research.feature_snapshot import (
    FeatureSnapshot,
    FeatureValue,
    PITFeatureBuilder,
    build_feature_snapshot,
)


AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_context():
    return ResearchContext(
        symbol=" TEST ",
        timestamp=AS_OF,
        market=({"close": 100},),
        fundamentals=({"revenue_growth": 0.2},),
        source_ids=("SEC_EDGAR", "NSE_INDIA"),
    )


def test_feature_value_normalizes_name_and_sources():
    feature = FeatureValue(
        name=" Revenue_Growth ",
        value=0.25,
        source_ids=(
            "NSE_INDIA",
            "SEC_EDGAR",
            "SEC_EDGAR",
        ),
    )

    assert feature.name == "revenue_growth"
    assert feature.source_ids == (
        "nse_india",
        "sec_edgar",
    )


def test_non_finite_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="finite",
    ):
        FeatureValue(
            name="quality",
            value=float("nan"),
        )


def test_feature_snapshot_is_deterministically_ordered():
    snapshot = FeatureSnapshot(
        symbol="TEST",
        timestamp=AS_OF,
        features=(
            FeatureValue("z_score", 2.0),
            FeatureValue("alpha", 1.0),
        ),
    )

    assert [
        feature.name
        for feature in snapshot.features
    ] == [
        "alpha",
        "z_score",
    ]


def test_duplicate_features_are_rejected():
    with pytest.raises(
        ValueError,
        match="duplicate feature names",
    ):
        FeatureSnapshot(
            symbol="TEST",
            timestamp=AS_OF,
            features=(
                FeatureValue("quality", 1.0),
                FeatureValue("QUALITY", 2.0),
            ),
        )


def test_naive_snapshot_timestamp_is_rejected():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        FeatureSnapshot(
            symbol="TEST",
            timestamp=datetime(
                2026,
                8,
                10,
                12,
            ),
        )


def test_builder_inherits_context_identity_and_timestamp():
    snapshot = PITFeatureBuilder().build(
        make_context(),
        {
            "quality": 0.91,
            "growth": 0.27,
        },
    )

    assert snapshot.symbol == "TEST"
    assert snapshot.timestamp == AS_OF
    assert snapshot.feature_count == 2


def test_builder_attaches_context_sources_to_numeric_features():
    snapshot = build_feature_snapshot(
        make_context(),
        {
            "quality": 0.91,
        },
    )

    feature = snapshot.get("QUALITY")

    assert feature.value == 0.91
    assert feature.source_ids == (
        "nse_india",
        "sec_edgar",
    )


def test_feature_value_can_preserve_explicit_provenance():
    feature = FeatureValue(
        name="cash_quality",
        value=0.88,
        source_ids=("sec_edgar",),
        observation_ids=("cash-flow-2026-q2",),
    )

    snapshot = PITFeatureBuilder().build(
        make_context(),
        {
            "cash_quality": feature,
        },
    )

    assert snapshot.get("cash_quality") == feature
    assert snapshot.get(
        "cash_quality"
    ).observation_ids == (
        "cash-flow-2026-q2",
    )


def test_invalid_numeric_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="must be numeric",
    ):
        PITFeatureBuilder().build(
            make_context(),
            {
                "quality": "excellent",
            },
        )


def test_snapshot_dictionary_is_stable():
    snapshot = build_feature_snapshot(
        make_context(),
        {
            "growth": 0.20,
            "quality": 0.91,
            "risk": -0.10,
        },
    )

    assert snapshot.as_dict() == {
        "growth": 0.20,
        "quality": 0.91,
        "risk": -0.10,
    }
