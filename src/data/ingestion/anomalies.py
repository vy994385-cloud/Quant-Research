from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from src.data.models import PriceBar


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MarketAnomaly(BaseModel):
    symbol: str
    trading_date: object
    code: str
    message: str
    severity: AnomalySeverity
    value: Decimal | None = None


def detect_market_anomalies(
    bars: list[PriceBar],
    price_jump_warning_pct: Decimal = Decimal("10"),
    price_jump_critical_pct: Decimal = Decimal("20"),
    volume_spike_multiple: Decimal = Decimal("5"),
) -> list[MarketAnomaly]:
    """
    Detect potentially unusual market observations.

    These are research flags, not automatic trading decisions.

    The function deliberately does not assume that an unusual
    observation is bad data. Corporate actions, earnings,
    acquisitions, news and other legitimate events can create
    extreme observations.
    """

    if not bars:
        return []

    ordered = sorted(
        bars,
        key=lambda bar: bar.trading_date,
    )

    anomalies: list[MarketAnomaly] = []

    previous_close: Decimal | None = None

    historical_volumes: list[int] = []

    for bar in ordered:

        if previous_close is not None and previous_close > 0:

            price_change_pct = (
                (bar.close - previous_close)
                / previous_close
            ) * Decimal("100")

            absolute_change_pct = abs(price_change_pct)

            if absolute_change_pct >= price_jump_critical_pct:

                anomalies.append(
                    MarketAnomaly(
                        symbol=bar.symbol,
                        trading_date=bar.trading_date,
                        code="EXTREME_PRICE_MOVE",
                        message=(
                            f"Close changed by "
                            f"{price_change_pct:.2f}% "
                            f"from the previous observation."
                        ),
                        severity=AnomalySeverity.CRITICAL,
                        value=price_change_pct,
                    )
                )

            elif absolute_change_pct >= price_jump_warning_pct:

                anomalies.append(
                    MarketAnomaly(
                        symbol=bar.symbol,
                        trading_date=bar.trading_date,
                        code="LARGE_PRICE_MOVE",
                        message=(
                            f"Close changed by "
                            f"{price_change_pct:.2f}% "
                            f"from the previous observation."
                        ),
                        severity=AnomalySeverity.WARNING,
                        value=price_change_pct,
                    )
                )

        if historical_volumes:

            average_volume = (
                Decimal(sum(historical_volumes))
                / Decimal(len(historical_volumes))
            )

            if (
                average_volume > 0
                and Decimal(bar.volume)
                >= average_volume * volume_spike_multiple
            ):

                anomalies.append(
                    MarketAnomaly(
                        symbol=bar.symbol,
                        trading_date=bar.trading_date,
                        code="VOLUME_SPIKE",
                        message=(
                            f"Volume is {Decimal(bar.volume) / average_volume:.2f}x "
                            "the historical average."
                        ),
                        severity=AnomalySeverity.WARNING,
                        value=Decimal(bar.volume),
                    )
                )

        previous_close = bar.close
        historical_volumes.append(bar.volume)

    return anomalies
