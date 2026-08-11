from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable

from src.data.models import PriceBar


class ValidationStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    status: ValidationStatus


@dataclass
class IngestionResult:
    accepted: list[PriceBar] = field(default_factory=list)
    rejected: list[PriceBar] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

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


def _make_issue(
    code: str,
    message: str,
    status: ValidationStatus,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        status=status,
    )


def _decimal_threshold(
    value: Decimal | float | None,
    *,
    default: Decimal,
) -> Decimal:
    if value is None:
        return default

    threshold = Decimal(str(value))

    if threshold <= 0:
        raise ValueError(
            "Validation thresholds must be greater than zero."
        )

    return threshold


def _validate_ohlc(
    bar: PriceBar,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    valid = True

    if bar.open <= 0:
        valid = False

    if bar.high <= 0:
        valid = False

    if bar.low <= 0:
        valid = False

    if bar.close <= 0:
        valid = False

    if bar.volume < 0:
        valid = False

    if bar.high < bar.low:
        valid = False

    if bar.high < bar.open:
        valid = False

    if bar.high < bar.close:
        valid = False

    if bar.low > bar.open:
        valid = False

    if bar.low > bar.close:
        valid = False

    if not valid:
        issues.append(
            _make_issue(
                "INVALID_OHLC",
                (
                    f"Invalid OHLC/volume relationship for "
                    f"{bar.symbol} on {bar.trading_date}."
                ),
                ValidationStatus.REJECT,
            )
        )

    return issues


def _validate_identity(
    bar: PriceBar,
    symbol: str,
    start_date: date,
    end_date: date,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not bar.symbol.strip():
        issues.append(
            _make_issue(
                "INVALID_SYMBOL",
                "PriceBar contains a blank symbol.",
                ValidationStatus.REJECT,
            )
        )
        return issues

    if bar.symbol.strip().upper() != symbol:
        issues.append(
            _make_issue(
                "SYMBOL_MISMATCH",
                (
                    f"Expected symbol {symbol}, "
                    f"received {bar.symbol}."
                ),
                ValidationStatus.REJECT,
            )
        )

    if (
        bar.trading_date < start_date
        or bar.trading_date > end_date
    ):
        issues.append(
            _make_issue(
                "DATE_OUT_OF_RANGE",
                (
                    f"{bar.symbol} on {bar.trading_date} "
                    f"is outside requested range "
                    f"{start_date} to {end_date}."
                ),
                ValidationStatus.REJECT,
            )
        )

    return issues


def _duplicate_keys(
    bars: list[PriceBar],
) -> set[tuple[str, date]]:
    counts: dict[tuple[str, date], int] = {}

    for bar in bars:
        key = (
            bar.symbol.strip().upper(),
            bar.trading_date,
        )

        counts[key] = counts.get(key, 0) + 1

    return {
        key
        for key, count in counts.items()
        if count > 1
    }


def _validate_duplicates(
    duplicate_keys: set[tuple[str, date]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for symbol, trading_date in sorted(duplicate_keys):
        issues.append(
            _make_issue(
                "DUPLICATE_SYMBOL_DATE",
                (
                    f"Duplicate symbol/date record for "
                    f"{symbol} on {trading_date}."
                ),
                ValidationStatus.REJECT,
            )
        )

    return issues


def _large_price_move_issue(
    previous: PriceBar,
    current: PriceBar,
    *,
    warning_pct: Decimal,
    critical_pct: Decimal,
) -> ValidationIssue | None:
    if previous.close <= 0:
        return None

    move_pct = (
        abs(
            (current.close - previous.close)
            / previous.close
        )
        * Decimal("100")
    )

    if move_pct >= critical_pct:
        return _make_issue(
            "EXTREME_PRICE_MOVE",
            (
                f"{current.symbol} on {current.trading_date} "
                f"moved {move_pct:.2f}% from the previous close."
            ),
            ValidationStatus.NEEDS_REVIEW,
        )

    if move_pct >= warning_pct:
        return _make_issue(
            "LARGE_PRICE_MOVE",
            (
                f"{current.symbol} on {current.trading_date} "
                f"moved {move_pct:.2f}% from the previous close."
            ),
            ValidationStatus.NEEDS_REVIEW,
        )

    return None


def _volume_spike_issue(
    previous: PriceBar,
    current: PriceBar,
    *,
    spike_multiple: Decimal,
) -> ValidationIssue | None:
    if previous.volume <= 0:
        return None

    multiple = (
        Decimal(current.volume)
        / Decimal(previous.volume)
    )

    if multiple >= spike_multiple:
        return _make_issue(
            "VOLUME_SPIKE",
            (
                f"{current.symbol} on {current.trading_date} "
                f"volume is {multiple:.2f}x the previous "
                f"observation."
            ),
            ValidationStatus.NEEDS_REVIEW,
        )

    return None


def _run_anomaly_checks(
    accepted: list[PriceBar],
    *,
    price_jump_warning_pct: Decimal,
    price_jump_critical_pct: Decimal,
    volume_spike_multiple: Decimal,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    ordered = sorted(
        accepted,
        key=lambda bar: bar.trading_date,
    )

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        price_issue = _large_price_move_issue(
            previous,
            current,
            warning_pct=price_jump_warning_pct,
            critical_pct=price_jump_critical_pct,
        )

        if price_issue is not None:
            issues.append(price_issue)

        volume_issue = _volume_spike_issue(
            previous,
            current,
            spike_multiple=volume_spike_multiple,
        )

        if volume_issue is not None:
            issues.append(volume_issue)

    return issues


def validate_price_bars(
    bars: Iterable[PriceBar],
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    price_jump_warning_pct: Decimal | float | None = None,
    price_jump_critical_pct: Decimal | float | None = None,
    volume_spike_multiple: Decimal | float | None = None,
) -> IngestionResult:
    """
    Validate normalized daily market-price observations.

    Structural/data-integrity problems are rejected.

    Potentially legitimate market behaviour such as large price
    movements and unusual volume is marked NEEDS_REVIEW.

    Invalid records are excluded from anomaly analysis.
    """

    result = IngestionResult()

    if start_date > end_date:
        result.issues.append(
            _make_issue(
                "INVALID_DATE_RANGE",
                (
                    f"start_date {start_date} is after "
                    f"end_date {end_date}."
                ),
                ValidationStatus.REJECT,
            )
        )

        result.rejected.extend(list(bars))
        return result

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        result.issues.append(
            _make_issue(
                "INVALID_SYMBOL",
                "Requested symbol cannot be blank.",
                ValidationStatus.REJECT,
            )
        )

        result.rejected.extend(list(bars))
        return result

    warning_pct = _decimal_threshold(
        price_jump_warning_pct,
        default=Decimal("10"),
    )

    critical_pct = _decimal_threshold(
        price_jump_critical_pct,
        default=Decimal("20"),
    )

    volume_multiple = _decimal_threshold(
        volume_spike_multiple,
        default=Decimal("5"),
    )

    if critical_pct < warning_pct:
        raise ValueError(
            "price_jump_critical_pct must be greater than "
            "or equal to price_jump_warning_pct."
        )

    records = list(bars)

    input_dates = [
        bar.trading_date
        for bar in records
    ]

    if input_dates != sorted(input_dates):
        result.issues.append(
            _make_issue(
                "OUT_OF_ORDER",
                "Input price bars are not in chronological order.",
                ValidationStatus.NEEDS_REVIEW,
            )
        )

    duplicate_keys = _duplicate_keys(records)

    result.issues.extend(
        _validate_duplicates(duplicate_keys)
    )

    valid_records: list[PriceBar] = []

    for bar in records:
        bar_issues = _validate_identity(
            bar=bar,
            symbol=normalized_symbol,
            start_date=start_date,
            end_date=end_date,
        )

        bar_issues.extend(
            _validate_ohlc(bar)
        )

        key = (
            bar.symbol.strip().upper(),
            bar.trading_date,
        )

        if key in duplicate_keys:
            bar_issues.append(
                _make_issue(
                    "DUPLICATE_SYMBOL_DATE",
                    (
                        f"Duplicate symbol/date record for "
                        f"{bar.symbol} on {bar.trading_date}."
                    ),
                    ValidationStatus.REJECT,
                )
            )

        result.issues.extend(bar_issues)

        has_rejection = any(
            issue.status == ValidationStatus.REJECT
            for issue in bar_issues
        )

        if has_rejection:
            result.rejected.append(bar)
        else:
            valid_records.append(bar)

    result.accepted.extend(
        sorted(
            valid_records,
            key=lambda bar: bar.trading_date,
        )
    )

    result.issues.extend(
        _run_anomaly_checks(
            result.accepted,
            price_jump_warning_pct=warning_pct,
            price_jump_critical_pct=critical_pct,
            volume_spike_multiple=volume_multiple,
        )
    )

    return result
