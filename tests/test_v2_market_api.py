from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.v2.market_contracts import (
    MarketBreadthContract,
    MarketCoverageContract,
    MarketOverviewContract,
)
from src.api.v2.market_service import V2MarketService
from src.api.v2.universe.models import UniverseSecurity


def sample_overview():
    return MarketOverviewContract(
        as_of=datetime(2026, 8, 4, tzinfo=timezone.utc),
        price_date=date(2026, 8, 4),
        indices=[],
        sector_indices=[],
        breadth=MarketBreadthContract(
            advancing=1,
            declining=0,
            unchanged=0,
            total=1,
        ),
        gainers=[],
        losers=[],
        active=[],
        sectors=[],
        coverage=MarketCoverageContract(
            universe="NSE equity universe configured in QRQuant",
            securities_available=75,
            securities_with_prices=75,
            securities_with_sector=0,
            coverage_status="complete",
        ),
    )


def test_v2_market_overview_route_is_registered(monkeypatch):
    monkeypatch.setattr(
        V2MarketService,
        "overview",
        lambda self: sample_overview(),
    )

    client = TestClient(app)
    response = client.get("/api/v2/markets/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["coverage"]["securities_available"] == 75
    assert data["coverage"]["coverage_status"] == "complete"
    assert data["breadth"]["advancing"] == 1


def test_v1_health_route_remains_available():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_v2_index_symbols_are_fetched_once(monkeypatch):
    service = V2MarketService()
    service.OVERVIEW_TTL_SECONDS = 0
    V2MarketService._overview_cache = None

    service.universe_provider.securities = lambda: (
        UniverseSecurity(symbol="TCS"),
        UniverseSecurity(symbol="INFY"),
    )

    from src.api.v2.market_contracts import (
        MarketIndexContract,
        MarketSecurityContract,
    )

    def fake_security(symbol, start_date, end_date):
        return MarketSecurityContract(
            symbol=symbol,
            name=symbol,
            sector=None,
            price=100.0,
            change_pct=1.0,
            volume=1000,
            average_volume_20d=900.0,
            volume_ratio=1.11,
            trading_date=date(2026, 8, 4),
        )

    calls = []

    def fake_index(symbol, name, start_date, end_date):
        calls.append(symbol)
        return MarketIndexContract(
            symbol=symbol,
            name=name,
            price=100.0,
            change=1.0,
            change_pct=1.0,
            trading_date=date(2026, 8, 4),
        )

    monkeypatch.setattr(service, "_security", fake_security)
    monkeypatch.setattr(service, "_index", fake_index)

    result = service.overview()

    assert len(calls) == len(set(calls))
    assert len(calls) == 5
    assert len(result.indices) == 4
    assert len(result.sector_indices) == 3

    V2MarketService._overview_cache = None
