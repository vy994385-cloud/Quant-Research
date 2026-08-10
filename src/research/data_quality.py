from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MarketBarLike:
    """
    Minimal market-bar representation used by the research
    quality checks.

    The research layer intentionally does not depend on a
    specific market-data vendor or storage implementation.
    """

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    symbol: str = ""


@dataclass(frozen=True)
class DataQualityIssue:
    """
    One deterministic market-data quality issue.
    """

    code: str
    message: str
    index: int


@dataclass(frozen=True)
class DataQualityReport:
    """
    Result of market-data quality validation.
    """

    total_records: int
    issues: tuple[DataQualityIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def requires_review(self) -> bool:
        return bool(self.issues)


def validate_market_bars(
    bars: Sequence[MarketBarLike],
) -> DataQualityReport:
    """
    Validate basic structural and price integrity.

    Checks include:

    - timezone-aware timestamps
    - strictly increasing timestamps
    - duplicate timestamps
    - positive OHLC prices
    - OHLC consistency
    - non-negative volume
    """

    issues: list[DataQualityIssue] = []

    previous_timestamp: datetime | None = None
    seen_timestamps: set[datetime] = set()

    for index, bar in enumerate(bars):
        if bar.timestamp.tzinfo is None:
            issues.append(
                DataQualityIssue(
                    code="NAIVE_TIMESTAMP",
                    message="timestamp must be timezone-aware",
                    index=index,
                )
            )

        if bar.timestamp in seen_timestamps:
            issues.append(
                DataQualityIssue(
                    code="DUPLICATE_TIMESTAMP",
                    message="duplicate timestamp",
                    index=index,
                )
            )

        seen_timestamps.add(bar.timestamp)

        if previous_timestamp is not None:
            if bar.timestamp <= previous_timestamp:
                issues.append(
                    DataQualityIssue(
                        code="NON_CHRONOLOGICAL",
                        message=(
                            "timestamps must be strictly increasing"
                        ),
                        index=index,
                    )
                )

        previous_timestamp = bar.timestamp

        prices = (
            ("open", bar.open),
            ("high", bar.high),
            ("low", bar.low),
            ("close", bar.close),
        )

        for name, value in prices:
            if value <= Decimal("0"):
                issues.append(
                    DataQualityIssue(
                        code="NON_POSITIVE_PRICE",
                        message=(
                            f"{name} must be greater than zero"
                        ),
                        index=index,
                    )
                )

        if bar.high < bar.low:
            issues.append(
                DataQualityIssue(
                    code="HIGH_BELOW_LOW",
                    message="high cannot be below low",
                    index=index,
                )
            )

        if not (
            bar.low
            <= bar.open
            <= bar.high
        ):
            issues.append(
                DataQualityIssue(
                    code="OPEN_OUTSIDE_RANGE",
                    message="open must lie between low and high",
                    index=index,
                )
            )

        if not (
            bar.low
            <= bar.close
            <= bar.high
        ):
            issues.append(
                DataQualityIssue(
                    code="CLOSE_OUTSIDE_RANGE",
                    message="close must lie between low and high",
                    index=index,
                )
            )

        if bar.volume < Decimal("0"):
            issues.append(
                DataQualityIssue(
                    code="NEGATIVE_VOLUME",
                    message="volume cannot be negative",
                    index=index,
                )
            )

    return DataQualityReport(
        total_records=len(bars),
        issues=tuple(issues),
    )
