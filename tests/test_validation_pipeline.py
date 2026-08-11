from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.validation.ranking_outcomes import (
    build_ranking_outcome,
)
from src.validation.ranking_validation import (
    RankingObservation,
)
from src.validation.validation_artifact_store import (
    ValidationArtifactStore,
)
from src.validation.validation_pipeline import (
    ValidationPipeline,
)


def make_observation(
    symbol: str,
    score: str,
    entry: str,
    outcome: str,
) -> RankingObservation:
    ranking_date = date(2024, 1, 1)
    outcome_date = date(2024, 4, 1)

    result = build_ranking_outcome(
        symbol=symbol,
        ranking_date=ranking_date,
        outcome_date=outcome_date,
        horizon="LONG_TERM",
        entry_price=Decimal(entry),
        outcome_price=Decimal(outcome),
    )

    return RankingObservation(
        symbol=symbol,
        ranking_date=ranking_date,
        horizon="LONG_TERM",
        score=Decimal(score),
        outcome=result,
    )


def observations():
    return [
        make_observation("AAA", "100", "100", "120"),
        make_observation("BBB", "80", "100", "110"),
        make_observation("CCC", "60", "100", "90"),
    ]


def test_pipeline_produces_artifact():
    pipeline = ValidationPipeline()

    result = pipeline.run(
        observations=observations(),
        generated_at=datetime(
            2026,
            8,
            11,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result.artifact.horizon == "LONG_TERM"
    assert result.artifact.validation_report[
        "observation_count"
    ] == 3
    assert result.artifact_path is None


def test_pipeline_is_deterministic_for_fixed_timestamp():
    timestamp = datetime(
        2026,
        8,
        11,
        10,
        0,
        tzinfo=timezone.utc,
    )

    pipeline = ValidationPipeline()

    first = pipeline.run(
        observations=observations(),
        generated_at=timestamp,
    )

    second = pipeline.run(
        observations=observations(),
        generated_at=timestamp,
    )

    assert first.artifact.to_json() == second.artifact.to_json()


def test_pipeline_persists_artifact(
    tmp_path,
):
    store = ValidationArtifactStore(tmp_path)

    pipeline = ValidationPipeline(
        store=store,
    )

    result = pipeline.run(
        observations=observations(),
        artifact_id="run-001",
        generated_at=datetime(
            2026,
            8,
            11,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result.artifact_path == (
        tmp_path / "run-001.json"
    )

    restored = store.load("run-001")

    assert restored.to_json() == (
        result.artifact.to_json()
    )


def test_artifact_id_requires_store():
    pipeline = ValidationPipeline()

    with pytest.raises(
        ValueError,
        match="artifact store",
    ):
        pipeline.run(
            observations=observations(),
            artifact_id="run-001",
        )


def test_empty_observations_are_rejected():
    pipeline = ValidationPipeline()

    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        pipeline.run(
            observations=[],
        )


def test_naive_generated_at_is_rejected():
    pipeline = ValidationPipeline()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        pipeline.run(
            observations=observations(),
            generated_at=datetime(
                2026,
                8,
                11,
            ),
        )


def test_pipeline_does_not_change_observations():
    source = observations()

    before = tuple(source)

    pipeline = ValidationPipeline()

    pipeline.run(
        observations=source,
        generated_at=datetime(
            2026,
            8,
            11,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert tuple(source) == before


def test_duplicate_artifact_id_is_rejected(
    tmp_path,
):
    store = ValidationArtifactStore(tmp_path)

    pipeline = ValidationPipeline(
        store=store,
    )

    timestamp = datetime(
        2026,
        8,
        11,
        10,
        0,
        tzinfo=timezone.utc,
    )

    pipeline.run(
        observations=observations(),
        artifact_id="run-001",
        generated_at=timestamp,
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        pipeline.run(
            observations=observations(),
            artifact_id="run-001",
            generated_at=timestamp,
        )