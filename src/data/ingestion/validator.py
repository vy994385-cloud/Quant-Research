from collections import Counter
from datetime import date
from enum import Enum

from pydantic import BaseModel

from src.data.models import PriceBar


class ValidationStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ValidationIssue(BaseModel):
    code: str
    message: str
    status: ValidationStatus


class IngestionResult(BaseModel):
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


def validate_price_bars(
    bars: list[PriceBar],
    symbol: str,
    start_date: date,
    end_date: date,
) -> IngestionResult:
    """
    Validate normalized daily market data before it enters
    the research pipeline.

    This validator does not modify the supplied records.
    """

    accepted: list[PriceBar] = []
    rejected: list[PriceBar] = []
    issues: list[ValidationIssue] = []

    normalized_symbol = symbol.strip().upper()

    if start_date > end_date:
        issues.append(
            ValidationIssue(
                code="INVALID_DATE_RANGE",
                message="start_date must not be after end_date.",
                status=ValidationStatus.REJECT,
            )
        )

        return IngestionResult(
            accepted=[],
            rejected=list(bars),
            issues=issues,
        )

    date_counts = Counter(
        bar.trading_date
        for bar in bars
        if bar.symbol.strip().upper() == normalized_symbol
    )

    seen_dates: set[date] = set()

    for bar in bars:

        if bar.symbol.strip().upper() != normalized_symbol:
            rejected.append(bar)

            issues.append(
                ValidationIssue(
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
                ValidationIssue(
                    code="DATE_OUT_OF_RANGE",
                    message=(
                        f"{bar.trading_date} is outside "
                        f"requested range."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )

            continue

        if bar.trading_date in seen_dates:
            rejected.append(bar)

            issues.append(
                ValidationIssue(
                    code="DUPLICATE_DATE",
                    message=(
                        f"Duplicate trading date: "
                        f"{bar.trading_date}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )

            continue

        if date_counts[bar.trading_date] > 1:
            seen_dates.add(bar.trading_date)

            # The first occurrence is also unsafe because
            # we cannot determine which duplicate is correct.
            for existing in accepted[:]:
                if existing.trading_date == bar.trading_date:
                    accepted.remove(existing)
                    rejected.append(existing)

            rejected.append(bar)

            issues.append(
                ValidationIssue(
                    code="DUPLICATE_DATE",
                    message=(
                        f"Multiple records exist for "
                        f"{bar.trading_date}."
                    ),
                    status=ValidationStatus.REJECT,
                )
            )

            continue

        if not bar.is_valid_ohlc:
            rejected.append(bar)

            issues.append(
                ValidationIssue(
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
        seen_dates.add(bar.trading_date)

    accepted.sort(
        key=lambda item: item.trading_date
    )

    return IngestionResult(
        accepted=accepted,
        rejected=rejected,
        issues=issues,
    )
