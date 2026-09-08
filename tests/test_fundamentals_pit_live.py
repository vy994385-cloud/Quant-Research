"""Router-level PIT behaviour for the live fundamentals endpoints.

The Yahoo provider returns financial snapshots without an archival
timestamp (``available_at=None``). The router stamps the request's
capture time at the API boundary so that a default (now) query uses
the current snapshot set, while an explicit historical ``as_of``
query continues to honestly reject live data captured later.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.api.fundamentals_router import (
    create_fundamentals_router,
    _stamp_live_snapshots,
)
from src.data.company.financials import FinancialSnapshot

HISTORICAL_AS_OF = datetime(
    2026, 1, 1, 12, 0, tzinfo=timezone.utc
)


def make_snapshot(period_end: date) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        revenue=Decimal("1000"),
        net_profit=Decimal("100"),
        operating_profit=Decimal("150"),
        total_assets=Decimal("2000"),
        total_debt=Decimal("500"),
        shareholders_equity=Decimal("800"),
        current_assets=Decimal("600"),
        current_liabilities=Decimal("300"),
        inventory=Decimal("100"),
        operating_cash_flow=Decimal("120"),
        free_cash_flow=Decimal("80"),
        cash_and_equivalents=Decimal("200"),
        receivables=Decimal("150"),
        payables=Decimal("100"),
        source_name="test-provider",
        source_type="ANALYTICAL",
    )


class StubFinancialProvider:
    """Returns live-style snapshots without any available_at."""

    def __init__(self, snapshots: list[FinancialSnapshot]) -> None:
        self.snapshots = list(snapshots)

    def get_annual_financials(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[FinancialSnapshot]:
        _ = symbol, start_date, end_date
        return [
            s.model_copy()
            for s in self.snapshots
            if start_date <= s.period_end <= end_date
        ]


@pytest.fixture()
def live_snapshots() -> list[FinancialSnapshot]:
    return [
        make_snapshot(date(2024, 3, 31)),
        make_snapshot(date(2025, 3, 31)),
        make_snapshot(date(2026, 3, 31)),
    ]


@pytest.fixture()
def client(live_snapshots):
    router = create_fundamentals_router(
        provider=StubFinancialProvider(live_snapshots)
    )
    app = router  # APIRouter has no lifespan; wrap
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_stamp_live_snapshots_sets_capture_time(live_snapshots):
    captured_at = datetime(2026, 8, 10, tzinfo=timezone.utc)
    stamped = _stamp_live_snapshots(
        live_snapshots, captured_at
    )
    assert len(stamped) == len(live_snapshots)
    for snapshot in stamped:
        assert snapshot.available_at == captured_at
    # Underlying provider snapshots are untouched.
    for snapshot in live_snapshots:
        assert snapshot.available_at is None


def test_stamp_preserves_existing_provenance():
    captured_at = datetime(2026, 8, 10, tzinfo=timezone.utc)
    original = make_snapshot(date(2025, 3, 31))
    original.available_at = datetime(
        2025, 5, 1, tzinfo=timezone.utc
    )
    stamped = _stamp_live_snapshots([original], captured_at)
    assert stamped[0].available_at == original.available_at


def test_deep_fundamentals_default_as_of_uses_live_data(client):
    resp = client.get(
        "/api/v1/companies/TEST/deep-fundamentals"
    )
    assert resp.status_code == 200
    payload = resp.json()
    df = payload["deep_fundamentals"]
    assert df["symbol"] == "TEST"
    # Live snapshots are stamped with the capture time, so the
    # PIT filter admits them for a default (now) query.
    assert df["period_count"] >= 1


def test_deep_fundamentals_historical_as_of_rejects_live(client):
    resp = client.get(
        "/api/v1/companies/TEST/deep-fundamentals",
        params={"as_of": "2026-01-01T12:00:00Z"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    df = payload["deep_fundamentals"]
    assert df["symbol"] == "TEST"
    # Live data captured "now" is not knowable at an earlier
    # point in time; the result must honestly report no data.
    assert df["period_count"] == 0
    notes = "\n".join(df["notes"]).lower()
    assert "pit" in notes


def test_financial_history_default_stamps_available_at(client):
    resp = client.get(
        "/api/v1/companies/TEST/financial-history"
    )
    assert resp.status_code == 200
    fh = resp.json()["financial_history"]
    assert fh["period_count"] == 3
    for period in fh["periods"]:
        assert period["available_at"] is not None