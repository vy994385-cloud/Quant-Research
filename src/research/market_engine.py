from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    build_company_research_snapshot,
)
from src.analysis.stock_analysis import (
    StockAnalysisReport,
    build_stock_analysis,
)
from src.data.providers.base import MarketDataProvider
from src.data.universe import load_symbols
from src.features.market_adapter import (
    build_market_feature_snapshot_from_provider,
)


@dataclass(frozen=True)
class MarketResearchResult:
    """
    Complete market research result for a universe.

    Each successful security contains the real market-feature
    snapshot and the deterministic stock-analysis report.
    """

    as_of: date
    results: tuple[StockAnalysisReport, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(result.symbol for result in self.results)

    @property
    def successful_count(self) -> int:
        return len(self.results)


def _build_neutral_company_snapshot(
    symbol: str,
    as_of_date: date,
) -> CompanyResearchSnapshot:
    """
    Explicit placeholder for company-intelligence data.

    Market-only research must not invent fundamentals, management,
    AI participation, or other company-quality evidence.

    Neutral values are supplied only until the company-data provider
    is connected.
    """

    return build_company_research_snapshot(
        symbol=symbol,
        as_of_date=as_of_date,
    )


def _market_scores(
    report_snapshot,
) -> dict[str, Decimal]:
    """
    Convert available market observations into provisional
    research inputs.

    Company-quality fields remain neutral until their actual
    data providers are connected.
    """

    technical = report_snapshot.technical

    momentum = technical.momentum
    if momentum is None:
        momentum_score = Decimal("50")
    elif momentum <= Decimal("-20"):
        momentum_score = Decimal("0")
    elif momentum >= Decimal("20"):
        momentum_score = Decimal("100")
    else:
        momentum_score = (
            (momentum + Decimal("20"))
            / Decimal("40")
        ) * Decimal("100")

    if technical.volatility_20d is None:
        volatility_score = Decimal("50")
    elif technical.volatility_20d <= Decimal("1"):
        volatility_score = Decimal("90")
    elif technical.volatility_20d <= Decimal("2"):
        volatility_score = Decimal("80")
    elif technical.volatility_20d <= Decimal("3"):
        volatility_score = Decimal("70")
    elif technical.volatility_20d <= Decimal("5"):
        volatility_score = Decimal("55")
    elif technical.volatility_20d <= Decimal("8"):
        volatility_score = Decimal("40")
    else:
        volatility_score = Decimal("25")

    close = technical.latest_close

    if (
        close is None
        or technical.sma_5 is None
        or technical.sma_20 is None
    ):
        trend_strength = Decimal("50")
    else:
        trend_strength = Decimal("50")

        if close > technical.sma_5:
            trend_strength += Decimal("15")
        elif close < technical.sma_5:
            trend_strength -= Decimal("15")

        if close > technical.sma_20:
            trend_strength += Decimal("20")
        elif close < technical.sma_20:
            trend_strength -= Decimal("20")

        if technical.sma_5 > technical.sma_20:
            trend_strength += Decimal("10")
        elif technical.sma_5 < technical.sma_20:
            trend_strength -= Decimal("10")

        trend_strength = max(
            Decimal("0"),
            min(Decimal("100"), trend_strength),
        )

    relative = report_snapshot.relative_strength.relative_return_20d

    if relative is None:
        relative_strength = Decimal("50")
    elif relative <= Decimal("-20"):
        relative_strength = Decimal("0")
    elif relative >= Decimal("20"):
        relative_strength = Decimal("100")
    else:
        relative_strength = (
            (relative + Decimal("20"))
            / Decimal("40")
        ) * Decimal("100")

    return {
        "momentum": momentum_score,
        "trend_strength": trend_strength,
        "volatility": volatility_score,
        "relative_strength": relative_strength,
    }


def run_market_research(
    *,
    provider: MarketDataProvider,
    universe_file: str,
    benchmark_symbol: str,
    start_date: date,
    end_date: date,
) -> MarketResearchResult:
    """
    Run the real provider -> feature -> analysis pipeline.

    Pipeline:

        universe
          -> provider
          -> market feature snapshot
          -> stock analysis
          -> horizon rankings

    Company-quality inputs remain explicitly neutral until their
    dedicated data providers are connected.
    """

    if start_date > end_date:
        raise ValueError(
            "start_date must not be after end_date"
        )

    symbols = load_symbols(universe_file)

    results: list[StockAnalysisReport] = []

    for symbol in symbols:
        try:
            snapshot = build_market_feature_snapshot_from_provider(
                provider=provider,
                symbol=symbol,
                benchmark_symbol=benchmark_symbol,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError:
            continue

        market_scores = _market_scores(snapshot)

        company_snapshot = _build_neutral_company_snapshot(
            symbol=symbol,
            as_of_date=snapshot.trading_date,
        )

        report = build_stock_analysis(
            symbol=symbol,
            as_of_date=snapshot.trading_date,
            company_intelligence=company_snapshot,
            market_snapshot=snapshot,

            fundamentals=Decimal("50"),
            financial_trends=Decimal("50"),
            cash_flow=Decimal("50"),
            balance_sheet=Decimal("50"),
            risk=Decimal("50"),
            management=Decimal("50"),
            market_behavior=Decimal("50"),
            evidence_quality=Decimal("50"),

            liquidity=Decimal("50"),
            relative_strength=market_scores["relative_strength"],
            catalyst_strength=Decimal("50"),
            valuation=Decimal("50"),
        )

        results.append(report)

    return MarketResearchResult(
        as_of=end_date,
        results=tuple(results),
    )
