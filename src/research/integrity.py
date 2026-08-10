from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.research.data_quality import (
    DataQualityIssue,
    DataQualityReport,
    MarketBarLike,
    validate_market_bars,
)
from src.research.leakage import (
    LeakageViolation,
    find_future_data,
)
from src.research.provenance import DataProvenance


@dataclass(frozen=True)
class ResearchIntegrityReport:
    """
    Combined research-integrity result.

    This report is intentionally conservative:
    an unknown provenance timestamp or data-quality failure
    causes the experiment to require review.
    """

    data_quality: DataQualityReport
    leakage_violations: tuple[LeakageViolation, ...]

    @property
    def is_valid(self) -> bool:
        return (
            self.data_quality.is_valid
            and not self.leakage_violations
        )

    @property
    def requires_review(self) -> bool:
        return not self.is_valid

    @property
    def issue_count(self) -> int:
        return (
            self.data_quality.issue_count
            + len(self.leakage_violations)
        )


def validate_research_integrity(
    bars: Sequence[MarketBarLike],
    provenance_records: Iterable[DataProvenance],
    *,
    research_timestamp,
) -> ResearchIntegrityReport:
    """
    Run the minimum integrity gate before historical research.

    The function does not modify data and does not make trading
    decisions.
    """

    data_quality = validate_market_bars(bars)

    leakage_violations = find_future_data(
        provenance_records,
        timestamp=research_timestamp,
    )

    return ResearchIntegrityReport(
        data_quality=data_quality,
        leakage_violations=leakage_violations,
    )
