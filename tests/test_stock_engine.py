from datetime import date
from decimal import Decimal

import pytest

from src.analysis.stock_engine import (
    StockAnalysisEngine,
    StockAnalysisInput,
)


def test_stock_analysis_input_normalizes_symbol():
    with pytest.raises(Exception):
        StockAnalysisInput(
            symbol=" ",
            as_of_date=date(2026, 8, 12),
            company_intelligence=None,
            market_snapshot=None,
            fundamentals=Decimal("80"),
            financial_trends=Decimal("80"),
            cash_flow=Decimal("80"),
            balance_sheet=Decimal("80"),
            risk=Decimal("70"),
            management=Decimal("80"),
            market_behavior=Decimal("80"),
            evidence_quality=Decimal("90"),
            liquidity=Decimal("80"),
            relative_strength=Decimal("80"),
            catalyst_strength=Decimal("70"),
            valuation=Decimal("70"),
        )


def test_engine_exists():
    assert StockAnalysisEngine() is not None


def test_engine_requires_matching_company_symbol():
    from src.analysis.company_intelligence import (
        build_company_research_snapshot,
    )
    from src.features.market_snapshot import (
        MarketFeatureSnapshot,
    )

    intelligence = build_company_research_snapshot(
        "OTHER",
        date(2026, 8, 12),
    )

    market = MarketFeatureSnapshot(
        symbol="TEST",
        trading_date=date(2026, 8, 12),
        technical=None,
        structure=None,
        relative_strength=None,
        benchmark_symbol="NIFTY50",
    )

    data = StockAnalysisInput(
        symbol="TEST",
        as_of_date=date(2026, 8, 12),
        company_intelligence=intelligence,
        market_snapshot=market,
        fundamentals=Decimal("80"),
        financial_trends=Decimal("80"),
        cash_flow=Decimal("80"),
        balance_sheet=Decimal("80"),
        risk=Decimal("70"),
        management=Decimal("80"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("90"),
        liquidity=Decimal("80"),
        relative_strength=Decimal("80"),
        catalyst_strength=Decimal("70"),
        valuation=Decimal("70"),
    )

    with pytest.raises(ValueError, match="company intelligence symbol"):
        StockAnalysisEngine().run(data)


def test_engine_produces_all_three_horizon_rankings():
    from src.analysis.company_intelligence import (
        build_company_research_snapshot,
    )
    from src.features.market_snapshot import (
        MarketFeatureSnapshot,
    )

    symbol = "TEST"
    trading_date = date(2026, 8, 12)

    intelligence = build_company_research_snapshot(
        symbol,
        trading_date,
    )

    market = MarketFeatureSnapshot(
        symbol=symbol,
        trading_date=trading_date,
        technical=None,
        structure=None,
        relative_strength=None,
        benchmark_symbol="NIFTY50",
    )

    data = StockAnalysisInput(
        symbol=symbol,
        as_of_date=trading_date,
        company_intelligence=intelligence,
        market_snapshot=market,
        fundamentals=Decimal("80"),
        financial_trends=Decimal("80"),
        cash_flow=Decimal("80"),
        balance_sheet=Decimal("80"),
        risk=Decimal("70"),
        management=Decimal("80"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("90"),
        liquidity=Decimal("80"),
        relative_strength=Decimal("80"),
        catalyst_strength=Decimal("70"),
        valuation=Decimal("70"),
    )

    result = StockAnalysisEngine().run(data)

    assert result.symbol == symbol
    assert result.intraday.horizon == "INTRADAY"
    assert result.swing.horizon == "SWING"
    assert result.long_term.horizon == "LONG_TERM"

    assert result.intraday.score >= Decimal("0")
    assert result.swing.score >= Decimal("0")
    assert result.long_term.score >= Decimal("0")

    assert result.intraday.coverage < Decimal("100")
    assert result.swing.coverage < Decimal("100")
    assert result.long_term.coverage < Decimal("100")

    assert "future_readiness" in result.long_term.missing_components
    assert "ai_participation" in result.long_term.missing_components
    assert "sector_fit" in result.long_term.missing_components


def test_missing_future_intelligence_does_not_become_neutral_evidence():
    from src.analysis.company_intelligence import (
        build_company_research_snapshot,
    )
    from src.features.market_snapshot import (
        MarketFeatureSnapshot,
    )

    symbol = "TEST"
    trading_date = date(2026, 8, 12)

    intelligence = build_company_research_snapshot(
        symbol,
        trading_date,
    )

    market = MarketFeatureSnapshot(
        symbol=symbol,
        trading_date=trading_date,
        technical=None,
        structure=None,
        relative_strength=None,
        benchmark_symbol="NIFTY50",
    )

    data = StockAnalysisInput(
        symbol=symbol,
        as_of_date=trading_date,
        company_intelligence=intelligence,
        market_snapshot=market,
        fundamentals=Decimal("80"),
        financial_trends=Decimal("80"),
        cash_flow=Decimal("80"),
        balance_sheet=Decimal("80"),
        risk=Decimal("80"),
        management=Decimal("80"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("80"),
        liquidity=Decimal("80"),
        relative_strength=Decimal("80"),
        catalyst_strength=Decimal("80"),
        valuation=Decimal("80"),
    )

    result = StockAnalysisEngine().run(data)

    assert result.future_intelligence_available is False
    assert result.future_intelligence_completeness == Decimal("0")

    # Missing future dimensions are excluded rather than treated
    # as genuine 50/100 evidence.
    assert "future_readiness" in result.long_term.missing_components
    assert "ai_participation" in result.long_term.missing_components
    assert "innovation_execution" in result.long_term.missing_components
    assert "technology_diversification" in result.long_term.missing_components
