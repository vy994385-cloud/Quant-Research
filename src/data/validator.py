from collections.abc import Iterable

from .models import PriceBar


def validate_price_bars(
    bars: Iterable[PriceBar],
) -> list[str]:
    errors: list[str] = []

    seen: set[tuple[str, object]] = set()

    for index, bar in enumerate(bars):
        key = (bar.symbol, bar.trading_date)

        if key in seen:
            errors.append(
                f"Duplicate price bar at index {index}: "
                f"{bar.symbol} {bar.trading_date}"
            )

        seen.add(key)

        if not bar.is_valid_ohlc:
            errors.append(
                f"Invalid OHLC at index {index}: "
                f"{bar.symbol} {bar.trading_date}"
            )

        if bar.volume < 0:
            errors.append(
                f"Negative volume at index {index}: "
                f"{bar.symbol} {bar.trading_date}"
            )

    return errors
