from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api import main
from src.api.real_company_research import RealCompanyResearchService
from src.data.company.financials import FinancialSnapshot
from src.data.models import PriceBar
from src.data.providers.base import MarketDataProvider


class FixtureMarketProvider(MarketDataProvider):
    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        normalized = symbol.strip().upper()
        bars: list[PriceBar] = []

        for offset in range(30):
            trading_date = start_date + timedelta(days=offset)
            close = Decimal("100") + Decimal(offset)
            bars.append(
                PriceBar(
                    symbol=normalized,
                    trading_date=trading_date,
                    open=close - Decimal("1"),
                    high=close + Decimal("1"),
                    low=close - Decimal("2"),
                    close=close,
                    volume=100_000 + offset,
                )
            )

        return bars


class FixtureFinancialProvider:
    def get_annual_financials(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[FinancialSnapshot]:
        return [
            FinancialSnapshot(
                symbol=symbol,
                period_end=date(2024, 3, 31),
                revenue=Decimal("1000"),
                net_profit=Decimal("100"),
                operating_cash_flow=Decimal("120"),
                free_cash_flow=Decimal("90"),
                total_debt=Decimal("300"),
                receivables=Decimal("80"),
            ),
            FinancialSnapshot(
                symbol=symbol,
                period_end=date(2025, 3, 31),
                revenue=Decimal("1200"),
                net_profit=Decimal("140"),
                operating_cash_flow=Decimal("160"),
                free_cash_flow=Decimal("110"),
                total_debt=Decimal("250"),
                receivables=Decimal("95"),
            ),
        ]


def _result(tmp_path):
    service = RealCompanyResearchService(
        market_provider=FixtureMarketProvider(),
        financial_provider=FixtureFinancialProvider(),
        archive_root=tmp_path / "archive",
    )
    return service.run(
        "test",
        retrieved_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )


def test_real_company_service_runs_validated_pit_report_path(tmp_path):
    result = _result(tmp_path)

    assert result.analysis.symbol == "TEST"
    assert result.market_ingestion.accepted
    assert result.market_ingestion.rejected == []
    assert result.context_result.accepted_count == 2
    assert result.context_result.rejected_count == 0
    assert result.report.as_of == result.retrieved_at
    assert result.report.evidence_synthesis is not None
    assert result.report.evidence_narrative is not None
    assert any(
        evidence.provenance_ids
        for evidence in result.report.positive_evidence
    )
    assert result.analysis.company_intelligence.is_trade_signal is False
    assert (tmp_path / "archive").exists()


def test_real_company_research_route_exposes_report_provenance_and_quality(
    tmp_path,
    monkeypatch,
):
    result = _result(tmp_path)
    monkeypatch.setattr(
        main,
        "_run_real_company_research",
        lambda symbol: result,
    )

    response = TestClient(main.app).get(
        "/api/stocks/TEST/research"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == "TEST"
    assert payload["research_report"]["symbol"] == "TEST"
    assert payload["research_report"]["evidence_narrative"]
    assert payload["provenance"]["market"]["archived_records"] == 30
    assert payload["data_quality"]["context"]["rejected_observations"] == 0
    assert payload["data_quality"]["financial_data_missing"] is False
    assert payload["data_quality"]["feature_statuses"]["market_close"] == "VALID"
    assert payload["is_trade_signal"] is False
