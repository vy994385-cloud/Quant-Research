from datetime import datetime, timezone
from decimal import Decimal

from src.research.data_quality import (
    MarketBarLike,
    validate_market_bars,
)


def make_bar(
    *,
    timestamp: datetime,
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume: str = "1000",
) -> MarketBarLike:
    return MarketBarLike(
        timestamp=timestamp,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def test_valid_bars_pass() -> None:
    bars = [
        make_bar(
            timestamp=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            )
        ),
        make_bar(
            timestamp=datetime(
                2026,
                1,
                2,
                tzinfo=timezone.utc,
            )
        ),
    ]

    report = validate_market_bars(bars)

    assert report.is_valid is True
    assert report.issue_count == 0


def test_duplicate_timestamp_is_detected() -> None:
    timestamp = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    report = validate_market_bars(
        [
            make_bar(timestamp=timestamp),
            make_bar(timestamp=timestamp),
        ]
    )

    assert any(
        issue.code == "DUPLICATE_TIMESTAMP"
        for issue in report.issues
    )


def test_non_chronological_data_is_detected() -> None:
    report = validate_market_bars(
        [
            make_bar(
                timestamp=datetime(
                    2026,
                    1,
                    2,
                    tzinfo=timezone.utc,
                )
            ),
            make_bar(
                timestamp=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                )
            ),
        ]
    )

    assert any(
        issue.code == "NON_CHRONOLOGICAL"
        for issue in report.issues
    )


def test_invalid_ohlc_is_detected() -> None:
    report = validate_market_bars(
        [
            make_bar(
                timestamp=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
                open_price="120",
                high="110",
                low="90",
                close="105",
            )
        ]
    )

    assert any(
        issue.code == "OPEN_OUTSIDE_RANGE"
        for issue in report.issues
    )


def test_negative_volume_is_detected() -> None:
    report = validate_market_bars(
        [
            make_bar(
                timestamp=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
                volume="-1",
            )
        ]
    )

    assert any(
        issue.code == "NEGATIVE_VOLUME"
        for issue in report.issues
    )


def test_naive_timestamp_is_detected() -> None:
    report = validate_market_bars(
        [
            make_bar(
                timestamp=datetime(2026, 1, 1),
            )
        ]
    )

    assert any(
        issue.code == "NAIVE_TIMESTAMP"
        for issue in report.issues
    )
