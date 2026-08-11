from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.validation.ranking_validation import (
    RankingValidationResult,
)
from src.validation.ranking_validation_report import (
    RankingValidationReport,
    build_ranking_validation_report,
)


@dataclass(frozen=True)
class ValidationStressResult:
    """
    Descriptive stress-test summary for the ranking-validation
    framework.

    This does not modify ranking scores or optimize parameters.
    """

    scenario_count: int
    passed_count: int
    failed_count: int
    pass_rate: Decimal
    failures: tuple[str, ...]

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0


def _validate_report_invariants(
    report: RankingValidationReport,
) -> list[str]:
    failures: list[str] = []

    if report.window_count <= 0:
        failures.append("window_count must be positive")

    if report.observation_count <= 0:
        failures.append("observation_count must be positive")

    if not (
        Decimal("0")
        <= report.successful_window_rate
        <= Decimal("1")
    ):
        failures.append(
            "successful_window_rate must be between 0 and 1"
        )

    if report.weak_window_count < 0:
        failures.append(
            "weak_window_count cannot be negative"
        )

    if report.weak_window_count > report.window_count:
        failures.append(
            "weak_window_count cannot exceed window_count"
        )

    if report.average_excess_return is not None:
        if report.positive_excess_return_rate is None:
            failures.append(
                "positive excess rate missing with excess return"
            )

    if report.average_excess_return is None:
        if report.positive_excess_return_rate is not None:
            failures.append(
                "positive excess rate exists without excess return"
            )

    return failures


def stress_test_validation(
    scenarios: dict[
        str,
        list[RankingValidationResult],
    ],
) -> ValidationStressResult:
    """
    Run validation reports against multiple research scenarios.

    Each scenario is evaluated independently.

    A scenario passes when its resulting report satisfies the
    structural invariants of the validation framework.
    """

    if not scenarios:
        raise ValueError(
            "at least one stress scenario is required"
        )

    failures: list[str] = []

    for name, results in scenarios.items():
        if not name.strip():
            failures.append(
                "unnamed stress scenario"
            )
            continue

        try:
            report = build_ranking_validation_report(
                results
            )

            invariant_failures = (
                _validate_report_invariants(report)
            )

            for failure in invariant_failures:
                failures.append(
                    f"{name}: {failure}"
                )

        except Exception as exc:
            failures.append(
                f"{name}: {type(exc).__name__}: {exc}"
            )

    scenario_count = len(scenarios)
    failed_names = {
        failure.split(":", 1)[0]
        for failure in failures
    }

    failed_count = len(failed_names)
    passed_count = (
        scenario_count - failed_count
    )

    pass_rate = (
        Decimal(passed_count)
        / Decimal(scenario_count)
    )

    return ValidationStressResult(
        scenario_count=scenario_count,
        passed_count=passed_count,
        failed_count=failed_count,
        pass_rate=pass_rate,
        failures=tuple(failures),
    )


__all__ = [
    "ValidationStressResult",
    "stress_test_validation",
]