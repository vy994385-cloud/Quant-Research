from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.validation.validation_artifact import (
    VALIDATION_ARTIFACT_SCHEMA_VERSION,
    ValidationArtifact,
)


def make_artifact() -> ValidationArtifact:
    return ValidationArtifact(
        generated_at=datetime(
            2026,
            8,
            11,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        horizon="LONG_TERM",
        validation_report={
            "observation_count": 10,
            "average_forward_return": Decimal("0.125"),
            "positive_return_rate": Decimal("0.60"),
        },
        stress_test_result={
            "passed": True,
            "scenarios": ["baseline", "perturbed"],
        },
    )


def test_artifact_normalizes_horizon():
    artifact = make_artifact()

    assert artifact.horizon == "LONG_TERM"


def test_artifact_requires_timezone_aware_timestamp():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ValidationArtifact(
            generated_at=datetime(2026, 8, 11),
            horizon="LONG_TERM",
            validation_report={},
            stress_test_result={},
        )


def test_artifact_rejects_empty_horizon():
    with pytest.raises(
        ValueError,
        match="horizon",
    ):
        ValidationArtifact(
            generated_at=datetime(
                2026,
                8,
                11,
                tzinfo=timezone.utc,
            ),
            horizon=" ",
            validation_report={},
            stress_test_result={},
        )


def test_artifact_uses_current_schema_version():
    artifact = make_artifact()

    assert (
        artifact.schema_version
        == VALIDATION_ARTIFACT_SCHEMA_VERSION
    )


def test_decimal_values_are_serialized_deterministically():
    artifact = make_artifact()

    payload = artifact.to_json()

    assert '"0.125"' in payload
    assert artifact.to_json() == artifact.to_json()


def test_artifact_round_trip():
    original = make_artifact()

    restored = ValidationArtifact.from_json(
        original.to_json()
    )

    assert restored.schema_version == original.schema_version
    assert restored.generated_at == original.generated_at
    assert restored.horizon == original.horizon
    assert (
        restored.validation_report
        == original.to_dict()["validation_report"]
    )
    assert (
        restored.stress_test_result
        == original.to_dict()["stress_test_result"]
    )


def test_missing_required_field_is_rejected():
    payload = make_artifact().to_dict()

    del payload["horizon"]

    with pytest.raises(
        ValueError,
        match="missing required artifact fields",
    ):
        ValidationArtifact.from_dict(payload)


def test_unsupported_schema_version_is_rejected():
    payload = make_artifact().to_dict()
    payload["schema_version"] = "999.0"

    with pytest.raises(
        ValueError,
        match="unsupported",
    ):
        ValidationArtifact.from_dict(payload)


def test_artifact_does_not_mutate_input_data():
    validation_report = {
        "average_return": Decimal("0.10"),
        "nested": {
            "value": Decimal("0.20"),
        },
    }

    original = dict(validation_report)

    artifact = ValidationArtifact(
        generated_at=datetime(
            2026,
            8,
            11,
            tzinfo=timezone.utc,
        ),
        horizon="LONG_TERM",
        validation_report=validation_report,
        stress_test_result={},
    )

    artifact.to_json()

    assert validation_report == original