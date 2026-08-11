from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from src.validation.ranking_validation import (
    RankingObservation,
    validate_rankings,
)
from src.validation.validation_artifact import (
    ValidationArtifact,
)
from src.validation.validation_artifact_store import (
    ValidationArtifactStore,
)
from src.validation.validation_stress import (
    ValidationStressResult,
)


@dataclass(frozen=True)
class ValidationPipelineResult:
    """
    Result of one deterministic validation-pipeline execution.

    The pipeline only orchestrates existing validation components.
    It does not optimize ranking parameters or modify ranking logic.
    """

    artifact: ValidationArtifact
    artifact_path: object | None = None


class ValidationPipeline:
    """
    Orchestrate ranking validation into an auditable artifact.

    Responsibilities:
    - validate historical ranking observations
    - attach supplied stress-test results
    - create one immutable ValidationArtifact
    - optionally persist the artifact

    This class deliberately contains no ranking-weight optimization.
    """

    def __init__(
        self,
        *,
        store: ValidationArtifactStore | None = None,
    ) -> None:
        self._store = store

    def run(
        self,
        *,
        observations: Sequence[RankingObservation],
        stress_test: ValidationStressResult | None = None,
        artifact_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> ValidationPipelineResult:
        if not observations:
            raise ValueError(
                "at least one ranking observation is required"
            )

        if artifact_id is not None and self._store is None:
            raise ValueError(
                "artifact store is required when artifact_id is supplied"
            )

        validation = validate_rankings(
            list(observations)
        )

        timestamp = (
            generated_at
            if generated_at is not None
            else datetime.now(timezone.utc)
        )

        if timestamp.tzinfo is None:
            raise ValueError(
                "generated_at must be timezone-aware"
            )

        validation_report = {
            "horizon": validation.horizon,
            "observation_count": validation.observation_count,
            "average_forward_return": (
                validation.average_forward_return
            ),
            "median_forward_return": (
                validation.median_forward_return
            ),
            "positive_return_rate": (
                validation.positive_return_rate
            ),
            "average_excess_return": (
                validation.average_excess_return
            ),
            "positive_excess_return_rate": (
                validation.positive_excess_return_rate
            ),
            "score_return_correlation": (
                validation.score_return_correlation
            ),
        }

        stress_result = (
    stress_test.to_dict()
    if stress_test is not None
    else {}
)

        artifact = ValidationArtifact(
            generated_at=timestamp,
            horizon=validation.horizon,
            validation_report=validation_report,
            stress_test_result=stress_result,
        )

        artifact_path = None

        if artifact_id is not None:
            artifact_path = self._store.save(
                artifact,
                artifact_id,
            )

        return ValidationPipelineResult(
            artifact=artifact,
            artifact_path=artifact_path,
        )


__all__ = [
    "ValidationPipeline",
    "ValidationPipelineResult",
]