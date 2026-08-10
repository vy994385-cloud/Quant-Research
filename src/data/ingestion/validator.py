from collections import Counter
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict

from src.data.ingestion.anomalies import (
    AnomalySeverity,
    detect_market_anomalies,
)
from src.data.models import PriceBar


class ValidationStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    status: ValidationStatus


class IngestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: list[PriceBar]
    rejected: list[PriceBar]
    issues: list[ValidationIssue]

    @property
    def status(self) -> ValidationStatus:
        if any(
            issue.status == ValidationStatus.REJECT
            for issue in self.issues
        ):
            return ValidationStatus.REJECT

        if any(
            issue.status == ValidationStatus.NEEDS_REVIEW
            for issue in self.issues
        ):
            return ValidationStatus.NEEDS_REVIEW

        return ValidationStatus.ACCEPT

    @property
    def is_clean(self) -> bool:
        return self.status == ValidationStatus.ACCEPT

    @property
    def requires_review(self) -> bool:
        return self.status == ValidationStatus.NEEDS_REVIEW


def _issue(
    code: str,
    message: str,
    status: ValidationStatus,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        status=status,
    )


def validate_price_bars(
    bars: list[PriceBar],
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    price_jump_warning_pct=None,
    price_jump_critical_pct=None,
    volume_spike_multiple=None,
) -> IngestionResult:
    """
    Validate normalized daily OHLCV market data before it enters
    the research pipeline.

    Responsibilities:

    1. Validate requested date range.
    2. Enforce the requested symbol.
    3. Enforce requested date boundaries.
    4. Reject duplicate symbol/date records.
    5. Detect non-chronological input.
    6. Validate OHLC relationships.
    7. Detect suspicious price movements.
    8. Detect abnormal volume.
    9. Return explainable ACCEPT / REJECT / NEEDS_REVIEW status.

    The validator never silently repairs or modifies PriceBar records.

    Suspicious market observations are not automatically considered
    bad data. They produce NEEDS_REVIEW so legitimate events such as
    earnings, corporate actions, acquisitions, or major news can be
    investigated separately.
    """

    normalized_symbol = symbol.strip().upper()

    if start_date > end_date:
        issue = _issue(
            code="INVALID_DATE_RANGE",
            message="start_date must not be after end_date.",
            status=ValidationStatus.REJECT,
        )

        return IngestionResult(
            accepted=[],
            rejected=list(bars),
            issues=[issue],
        )

    if not normalized_symbol:
        issue = _issue(
            code="INVALID_SYMBOL",
            message="symbol must not be empty.",
            status=ValidationStatus.REJECT,
        )

        return IngestionResult(
            accepted=[],
            rejected=list(bars),
            issues=[issue],
        )

    issues: list[ValidationIssue] = []
    accepted: list[PriceBar] = []
    rejected: list[PriceBar] = []

    expected_symbol_bars = [
        bar
        for bar in bars
        if bar.symbol.strip().upper() == normalized_symbol
    ]

    date_counts = Counter(
        bar.trading_date
        for bar in expected_symbol_bars
    )

    # Input order is part of ingestion quality. We still return
    # accepted records chronologically so downstream consumers receive
    # deterministic ordering.
    input_dates = [
        bar.trading_date
        for bar in expected_symbol_bars
    ]

    if input_dates != sorted(input_dates):
        issues.append(
            _issue(
                code="NON_CHRONOLOGICAL_INPUT",
                message=(
                    "Input records are not in chronological "
                    "trading-date order."
                ),
                status=ValidationStatus.NEEDS_REVIEW,
            )
        )

    duplicate_dates = {
        trading_date
        for trading_date, count in date_counts.items()
        if count > 1
    }

    for bar in bars:
        bar_symbol = bar.symbol.strip().upper()

        if bar_symbol != normalized_symbol:
            rejected.append(bar)

            issues.append(
                _issue(
                    code="SYMBOL_MISMATCH",
                    message=(
                        f"Expected symbol {normalized_symbol}, "
                        f"received {bar.symbol}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )
            continue

        if not (
            start_date
            <= bar.trading_date
            <= end_date
        ):
            rejected.append(bar)

            issues.append(
                _issue(
                    code="DATE_OUT_OF_RANGE",
                    message=(
                        f"{bar.trading_date} is outside "
                        f"requested range "
                        f"{start_date} to {end_date}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )
            continue

        if bar.trading_date in duplicate_dates:
            rejected.append(bar)

            issues.append(
                _issue(
                    code="DUPLICATE_SYMBOL_DATE",
                    message=(
                        f"Multiple records exist for "
                        f"{normalized_symbol} on "
                        f"{bar.trading_date}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )
            continue

        if not bar.is_valid_ohlc:
            rejected.append(bar)

            issues.append(
                _issue(
                    code="INVALID_OHLC",
                    message=(
                        f"Invalid OHLC relationship for "
                        f"{bar.symbol} on {bar.trading_date}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )
            continue

        accepted.append(bar)

    accepted.sort(
        key=lambda item: item.trading_date
    )

    # Only run market anomaly detection against structurally valid
    # records. Invalid records must not contaminate the anomaly baseline.
    if accepted:
        anomaly_kwargs = {}

        if price_jump_warning_pct is not None:
            anomaly_kwargs["price_jump_warning_pct"] = (
                price_jump_warning_pct
            )

        if price_jump_critical_pct is not None:
            anomaly_kwargs["price_jump_critical_pct"] = (
                price_jump_critical_pct
            )

        if volume_spike_multiple is not None:
            anomaly_kwargs["volume_spike_multiple"] = (
                volume_spike_multiple
            )

        anomalies = detect_market_anomalies(
            accepted,
            **anomaly_kwargs,
        )

        for anomaly in anomalies:
            if anomaly.severity == AnomalySeverity.CRITICAL:
                status = ValidationStatus.NEEDS_REVIEW
            else:
                status = ValidationStatus.NEEDS_REVIEW

            issues.append(
                _issue(
                    code=anomaly.code,
                    message=anomaly.message,
                    status=status,
                )
            )

    return IngestionResult(
        accepted=accepted,
        rejected=rejected,
        issues=issues,
    )
