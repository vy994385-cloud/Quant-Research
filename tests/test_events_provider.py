from datetime import datetime, timezone

import pytest

from src.events.provider import ProviderRequest, RawEvent


def test_provider_request_normalizes_symbols():
    request = ProviderRequest(
        symbols=(" aapl ", "msft"),
        start=datetime(
            2026, 1, 1, tzinfo=timezone.utc
        ),
        end=datetime(
            2026, 1, 2, tzinfo=timezone.utc
        ),
    )

    assert request.symbols == ("AAPL", "MSFT")


def test_provider_request_rejects_empty_symbols():
    with pytest.raises(ValueError):
        ProviderRequest(
            symbols=(),
            start=datetime(
                2026, 1, 1, tzinfo=timezone.utc
            ),
            end=datetime(
                2026, 1, 2, tzinfo=timezone.utc
            ),
        )


def test_provider_request_rejects_invalid_period():
    with pytest.raises(ValueError):
        ProviderRequest(
            symbols=("AAPL",),
            start=datetime(
                2026, 1, 2, tzinfo=timezone.utc
            ),
            end=datetime(
                2026, 1, 1, tzinfo=timezone.utc
            ),
        )


def test_raw_event_preserves_provenance():
    event = RawEvent(
        event_id="news-1",
        source="Example News",
        source_url="https://example.com/news/1",
        title="Example event",
        published_at=datetime(
            2026, 1, 1, 10, tzinfo=timezone.utc
        ),
        available_at=datetime(
            2026, 1, 1, 10, tzinfo=timezone.utc
        ),
        symbols=("AAPL",),
    )

    assert event.source == "Example News"
    assert event.source_url == "https://example.com/news/1"
