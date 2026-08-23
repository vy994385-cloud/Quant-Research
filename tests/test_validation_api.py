"""Tests for the L6 backtest / validation API endpoints.

Verifies the contract serialization, horizon handling, error paths,
and beta launch gate requirement that backtest results carry explicit
disclaimers.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_api_error_handlers
from src.api.recorded_research import RecordedCompanyResearchService
from src.api.recorded_validation import RecordedValidationService
from src.api.validation_contracts import (
    CompanyBacktestContract,
    UniverseValidationContract,
)
from src.api.validation_router import create_validation_router

VERIFIED_COMPANIES = (
    "TCS",
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "M&M",
)

HORIZONS = ("INTRADAY", "SWING", "LONG_TERM")


@pytest.fixture(scope="module")
def research_service(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp(
        "validation-api-archive"
    )
    return RecordedCompanyResearchService(
        archive_root=archive_root,
    )


@pytest.fixture(scope="module")
def validation_service(research_service):
    return RecordedValidationService(
        research_service=research_service,
    )


@pytest.fixture(scope="module")
def client(research_service, validation_service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(
        create_validation_router(
            research_service=research_service,
            validation_service=validation_service,
        )
    )
    return TestClient(app)


# ── Company backtest endpoint ────────────────────────────────────


def test_backtest_route_exposed(client):
    resp = client.get("/api/v1/companies/TCS/backtest")
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_backtest_has_required_fields(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    assert payload["company"]["symbol"] == "TCS"
    assert payload["horizon"] == "LONG_TERM"
    assert payload["as_of"]

    bt = payload["backtest"]
    assert bt is not None
    assert "total_return" in bt
    assert "trade_count" in bt
    assert "win_rate" in bt
    assert "max_drawdown" in bt
    assert "max_drawdown_percent" in bt
    assert "sample_size_warning" in bt
    assert "research_signal" in bt
    assert "limitations" in bt

    assert bt["research_signal"] in {
        "HISTORICALLY_POSITIVE",
        "HISTORICALLY_NEGATIVE",
        "HIGH_DRAWDOWN",
        "INSUFFICIENT_SAMPLE",
        "INSUFFICIENT_DATA",
        "NEUTRAL",
    }


def test_tcs_backtest_has_disclaimer_notes(client):
    """Launch gate: backtest results must not be presented as guaranteed returns."""
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    notes = payload["notes"]
    assert len(notes) >= 2

    notes_text = " ".join(notes).lower()
    assert "historical" in notes_text
    assert "guarantee" in notes_text or "do not guarantee" in notes_text


def test_tcs_backtest_has_validation_quality(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    quality = payload["validation_quality"]
    assert quality is not None
    assert "quality" in quality
    assert "score" in quality
    assert "confidence" in quality
    assert "observation_count" in quality
    assert "positive_return_rate" in quality
    assert "reasons" in quality
    assert "is_actionable" in quality

    report = payload["validation_report"]
    assert report is not None
    assert "robust" in report
    assert "strengths" in report
    assert "weaknesses" in report


def test_tcs_backtest_has_walk_forward_windows(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    windows = payload["windows"]
    assert isinstance(windows, list)
    assert len(windows) >= 1

    for window in windows:
        assert "window_index" in window
        assert "observation_count" in window
        assert "average_forward_return" in window
        assert "positive_return_rate" in window


def test_tcs_backtest_has_strategy_description(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    assert payload["strategy_description"]
    assert "threshold" in payload["strategy_description"].lower()
    assert "buy" in payload["strategy_description"].lower()
    assert "sell" in payload["strategy_description"].lower()


def test_tcs_backtest_has_data_coverage(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    payload = resp.json()

    coverage = payload["data_coverage"]
    assert "stock_bars" in coverage
    assert coverage["stock_bars"] > 0
    assert "ranking_observations" in coverage
    assert "validation_windows" in coverage


def test_backtest_has_benchmark_comparison(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    bt = resp.json()["backtest"]
    assert bt is not None

    benchmark = bt.get("benchmark")
    if benchmark is not None:
        assert "benchmark_symbol" in benchmark
        assert "excess_return" in benchmark
        assert "outperforming" in benchmark


# ── Pydantic contract validation ─────────────────────────────────


def test_backtest_response_validates_pydantic_contract(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    contract = CompanyBacktestContract(**resp.json())
    assert contract.company["symbol"] == "TCS"
    assert contract.horizon == "LONG_TERM"
    assert contract.backtest is not None
    assert contract.validation_quality is not None


# ── All verified companies ───────────────────────────────────────


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_backtest_for_every_verified_company(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/backtest?horizon=LONG_TERM"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["company"]["symbol"] == symbol
    assert payload["backtest"] is not None
    assert payload["validation_quality"] is not None

    contract = CompanyBacktestContract(**payload)
    assert contract.company["symbol"] == symbol


# ── All horizons ─────────────────────────────────────────────────


@pytest.mark.parametrize("horizon", HORIZONS)
def test_backtest_for_every_horizon(client, horizon):
    resp = client.get(
        f"/api/v1/companies/TCS/backtest?horizon={horizon}"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["horizon"] == horizon
    assert payload["backtest"] is not None


# ── Determinism ──────────────────────────────────────────────────


def test_repeated_backtest_requests_are_deterministic(client):
    first = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    ).json()
    second = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    ).json()

    assert first == second


# ── Universe validation endpoint ─────────────────────────────────


def test_universe_validation_route_exposed(client):
    resp = client.get("/api/v1/validation/LONG_TERM")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == len(VERIFIED_COMPANIES)
    assert payload["horizon"] == "LONG_TERM"


def test_universe_validation_has_required_fields(client):
    resp = client.get("/api/v1/validation/LONG_TERM")
    payload = resp.json()

    assert "as_of" in payload
    assert "horizon" in payload
    assert "count" in payload
    assert "results" in payload

    assert payload["count"] == len(VERIFIED_COMPANIES)
    assert len(payload["results"]) == len(VERIFIED_COMPANIES)


def test_universe_validation_results_have_backtest(client):
    resp = client.get("/api/v1/validation/LONG_TERM")
    results = resp.json()["results"]

    for result in results:
        assert result["backtest"] is not None
        assert result["validation_quality"] is not None
        assert result["company"]["symbol"]
        assert result["notes"]

        notes_text = " ".join(result["notes"]).lower()
        assert "historical" in notes_text


def test_universe_validation_pydantic_contract(client):
    resp = client.get("/api/v1/validation/LONG_TERM")
    contract = UniverseValidationContract(**resp.json())
    assert contract.count == len(VERIFIED_COMPANIES)
    assert contract.horizon == "LONG_TERM"


@pytest.mark.parametrize("horizon", HORIZONS)
def test_universe_validation_for_every_horizon(client, horizon):
    resp = client.get(f"/api/v1/validation/{horizon}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["horizon"] == horizon
    assert payload["count"] == len(VERIFIED_COMPANIES)


def test_universe_validation_subset_filter(client):
    resp = client.get(
        "/api/v1/validation/LONG_TERM?symbols=TCS,INFY"
    )
    payload = resp.json()
    assert payload["count"] == 2
    symbols = {r["company"]["symbol"] for r in payload["results"]}
    assert symbols == {"TCS", "INFY"}


def test_universe_validation_deterministic(client):
    first = client.get(
        "/api/v1/validation/LONG_TERM"
    ).json()
    second = client.get(
        "/api/v1/validation/LONG_TERM"
    ).json()
    assert first == second


# ── Error paths ──────────────────────────────────────────────────


def test_unknown_company_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/backtest?horizon=LONG_TERM"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "unknown_company"


def test_invalid_horizon_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=INVALID"
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_horizon"


def test_invalid_horizon_in_universe_returns_400(client):
    resp = client.get("/api/v1/validation/INVALID")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_horizon"


def test_unknown_symbol_in_subset_returns_404(client):
    resp = client.get(
        "/api/v1/validation/LONG_TERM?symbols=TCS,BOGUS"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "unknown_company"


# ── Beta launch gate: no trade signal claim ──────────────────────


def test_backtest_explicitly_not_trade_signal(client):
    """The backtest signal must be descriptive only, never a trading instruction."""
    resp = client.get(
        "/api/v1/companies/TCS/backtest?horizon=LONG_TERM"
    )
    bt = resp.json()["backtest"]

    assert bt["research_signal"] in {
        "HISTORICALLY_POSITIVE",
        "HISTORICALLY_NEGATIVE",
        "HIGH_DRAWDOWN",
        "INSUFFICIENT_SAMPLE",
        "INSUFFICIENT_DATA",
        "NEUTRAL",
    }

    for note in resp.json()["notes"]:
        note_lower = note.lower()
        assert "trade signal" not in note_lower or "not" in note_lower
