from datetime import date
from decimal import Decimal

from src.data.ingestion.anomalies import (
    AnomalySeverity,
    detect_market_anomalies,
)
from src.data.models import PriceBar


def make_bar(
    trading_date,
    close,
    volume=100,
):
    close = Decimal(str(close))

    return PriceBar(
        symbol="TEST",
        trading_date=trading_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=volume,
    )


def test_no_anomaly_for_normal_price_change():

    bars = [
        make_bar(date(2026, 8, 3), "100"),
        make_bar(date(2026, 8, 4), "105"),
    ]

    anomalies = detect_market_anomalies(bars)

    assert anomalies == []


def test_large_price_move_is_flagged():

    bars = [
        make_bar(date(2026, 8, 3), "100"),
        make_bar(date(2026, 8, 4), "115"),
    ]

    anomalies = detect_market_anomalies(bars)

    assert len(anomalies) == 1
    assert anomalies[0].code == "LARGE_PRICE_MOVE"
    assert anomalies[0].severity == AnomalySeverity.WARNING


def test_extreme_price_move_is_critical():

    bars = [
        make_bar(date(2026, 8, 3), "100"),
        make_bar(date(2026, 8, 4), "125"),
    ]

    anomalies = detect_market_anomalies(bars)

    assert len(anomalies) == 1
    assert anomalies[0].code == "EXTREME_PRICE_MOVE"
    assert anomalies[0].severity == AnomalySeverity.CRITICAL


def test_volume_spike_is_flagged():

    bars = [
        make_bar(date(2026, 8, 1), "100", 100),
        make_bar(date(2026, 8, 2), "101", 100),
        make_bar(date(2026, 8, 3), "102", 100),
        make_bar(date(2026, 8, 4), "103", 100),
        make_bar(date(2026, 8, 5), "104", 600),
    ]

    anomalies = detect_market_anomalies(bars)

    assert any(
        anomaly.code == "VOLUME_SPIKE"
        for anomaly in anomalies
    )


def test_bars_are_processed_chronologically():

    bars = [
        make_bar(date(2026, 8, 4), "115"),
        make_bar(date(2026, 8, 3), "100"),
    ]

    anomalies = detect_market_anomalies(bars)

    assert anomalies[0].trading_date == date(2026, 8, 4)
