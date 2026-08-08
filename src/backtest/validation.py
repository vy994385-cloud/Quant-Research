from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from src.backtest.models import BacktestBar, BacktestSignal


ValidationStatus = str


@dataclass(frozen=True)
class BacktestValidation:
    """
    Deterministic validation result for a historical backtest.

    ACCEPT:
        No material validation problems were found.

    NEEDS_REVIEW:
        The data can technically be evaluated, but warnings make
        the resulting backtest less reliable.

    REJECT:
        The backtest contains an invalid condition and should not run.
    """

    status: ValidationStatus
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_accepted(self) -> bool:
        return self.status == "ACCEPT"

    @property
    def is_rejected(self) -> bool:
        return self.status == "REJECT"

    @property
    def needs_review(self) -> bool:
        return self.status == "NEEDS_REVIEW"


def _duplicate_dates(
    dates: Sequence[date],
) -> bool:
    return len(set(dates)) != len(dates)


def _is_strictly_ordered(
    dates: Sequence[date],
) -> bool:
    return all(
        current > previous
        for previous, current in zip(
            dates,
            dates[1:],
        )
    )


def validate_backtest_inputs(
    bars: Sequence[BacktestBar],
    signals: Sequence[BacktestSignal],
    *,
    minimum_bars: int = 30,
    minimum_trades: int = 10,
) -> BacktestValidation:
    """
    Validate the historical inputs before a backtest is executed.

    The validator is intentionally conservative.

    It does not attempt to decide whether a strategy is profitable.
    It only checks whether the supplied historical experiment is
    structurally valid and whether important limitations should be
    surfaced to the researcher.
    """

    errors: list[str] = []
    warnings: list[str] = []

    ordered_bars = list(bars)
    ordered_signals = list(signals)

    # ---------------------------------------------------------
    # Basic data requirements
    # ---------------------------------------------------------

    if not ordered_bars:
        errors.append("bars cannot be empty")

    if minimum_bars <= 0:
        raise ValueError(
            "minimum_bars must be greater than zero"
        )

    if minimum_trades < 0:
        raise ValueError(
            "minimum_trades cannot be negative"
        )

    # ---------------------------------------------------------
    # Bar validation
    # ---------------------------------------------------------

    if ordered_bars:
        bar_dates = [
            bar.trading_date
            for bar in ordered_bars
        ]

        if _duplicate_dates(bar_dates):
            errors.append(
                "bars contain duplicate trading dates"
            )

        if not _is_strictly_ordered(bar_dates):
            errors.append(
                "bars must be strictly ordered by trading_date"
            )

        if len(ordered_bars) < minimum_bars:
            warnings.append(
                f"Only {len(ordered_bars)} historical bars are "
                f"available; minimum recommended sample is "
                f"{minimum_bars}."
            )

        symbols = {
            bar.symbol
            for bar in ordered_bars
        }

        if len(symbols) > 1:
            errors.append(
                "bars must contain one symbol per backtest"
            )

    # ---------------------------------------------------------
    # Signal validation
    # ---------------------------------------------------------

    if ordered_signals:
        signal_dates = [
            signal.trading_date
            for signal in ordered_signals
        ]

        if _duplicate_dates(signal_dates):
            errors.append(
                "signals contain duplicate trading dates"
            )

        if not _is_strictly_ordered(signal_dates):
            errors.append(
                "signals must be strictly ordered by trading_date"
            )

        signal_symbols = {
            signal.symbol
            for signal in ordered_signals
        }

        if len(signal_symbols) > 1:
            errors.append(
                "signals must contain one symbol per backtest"
            )

        bar_keys = {
            (
                bar.symbol,
                bar.trading_date,
            )
            for bar in ordered_bars
        }

        for signal in ordered_signals:
            key = (
                signal.symbol,
                signal.trading_date,
            )

            if key not in bar_keys:
                errors.append(
                    "signal has no matching historical price bar: "
                    f"{signal.symbol} {signal.trading_date}"
                )

    # ---------------------------------------------------------
    # Look-ahead protection
    # ---------------------------------------------------------

    if ordered_bars and ordered_signals:
        first_bar_date = ordered_bars[0].trading_date
        last_bar_date = ordered_bars[-1].trading_date

        for signal in ordered_signals:
            if signal.trading_date < first_bar_date:
                errors.append(
                    "signal occurs before the available "
                    "historical data: "
                    f"{signal.symbol} {signal.trading_date}"
                )

            if signal.trading_date > last_bar_date:
                errors.append(
                    "signal occurs after the available "
                    "historical data: "
                    f"{signal.symbol} {signal.trading_date}"
                )

    # ---------------------------------------------------------
    # Sample-size warning
    # ---------------------------------------------------------

    buy_count = sum(
        signal.action == "BUY"
        for signal in ordered_signals
    )

    sell_count = sum(
        signal.action == "SELL"
        for signal in ordered_signals
    )

    completed_trade_estimate = min(
        buy_count,
        sell_count,
    )

    if completed_trade_estimate < minimum_trades:
        warnings.append(
            f"Only {completed_trade_estimate} completed trade "
            f"pair(s) are represented by the supplied signals; "
            f"minimum recommended sample is {minimum_trades}."
        )

    # ---------------------------------------------------------
    # Determine final status
    # ---------------------------------------------------------

    if errors:
        status = "REJECT"
    elif warnings:
        status = "NEEDS_REVIEW"
    else:
        status = "ACCEPT"

    return BacktestValidation(
        status=status,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
