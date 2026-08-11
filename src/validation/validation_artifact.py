from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from typing import Any


VALIDATION_ARTIFACT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ValidationArtifact:
    """
    Immutable, auditable representation of a validation run.

    The artifact stores serialized research-validation outputs so
    historical validation results can be persisted and compared
    without changing the underlying research objects.
    """

    generated_at: datetime
    horizon: str
    validation_report: dict[str, Any]
    stress_test_result: dict[str, Any]
    schema_version: str = VALIDATION_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError(
                "generated_at must be timezone-aware"
            )

        horizon = self.horizon.strip().upper()

        if not horizon:
            raise ValueError("horizon cannot be empty")

        if not isinstance(self.validation_report, dict):
            raise TypeError(
                "validation_report must be a dictionary"
            )

        if not isinstance(self.stress_test_result, dict):
            raise TypeError(
                "stress_test_result must be a dictionary"
            )

        if not self.schema_version.strip():
            raise ValueError(
                "schema_version cannot be empty"
            )

        object.__setattr__(self, "horizon", horizon)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "horizon": self.horizon,
            "validation_report": _serialize_value(
                self.validation_report
            ),
            "stress_test_result": _serialize_value(
                self.stress_test_result
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "ValidationArtifact":
        if not isinstance(payload, dict):
            raise TypeError(
                "validation artifact payload must be a dictionary"
            )

        required = {
            "schema_version",
            "generated_at",
            "horizon",
            "validation_report",
            "stress_test_result",
        }

        missing = required.difference(payload)

        if missing:
            raise ValueError(
                "missing required artifact fields: "
                + ", ".join(sorted(missing))
            )

        if (
            payload["schema_version"]
            != VALIDATION_ARTIFACT_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported validation artifact schema version"
            )

        generated_at = datetime.fromisoformat(
            payload["generated_at"]
        )

        return cls(
            schema_version=payload["schema_version"],
            generated_at=generated_at,
            horizon=payload["horizon"],
            validation_report=payload["validation_report"],
            stress_test_result=payload["stress_test_result"],
        )

    @classmethod
    def from_json(
        cls,
        payload: str,
    ) -> "ValidationArtifact":
        if not payload.strip():
            raise ValueError(
                "validation artifact JSON cannot be empty"
            )

        data = json.loads(payload)

        return cls.from_dict(data)


def _serialize_value(value: Any) -> Any:
    """
    Convert Decimal and nested containers into deterministic
    JSON-compatible values without mutating the source.
    """

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _serialize_value(item)
            for item in value
        ]

    if isinstance(value, set):
        return [
            _serialize_value(item)
            for item in sorted(value, key=str)
        ]

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    raise TypeError(
        f"unsupported validation artifact value: "
        f"{type(value).__name__}"
    )


__all__ = [
    "VALIDATION_ARTIFACT_SCHEMA_VERSION",
    "ValidationArtifact",
]