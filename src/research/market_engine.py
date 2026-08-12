from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
)

from src.analysis.company_financial_intelligence import (
    build_financial_company_intelligence,
)
from src.analysis.financial_scoring import (
    score_financial_snapshot,
)
from src.analysis.financial_risk_scoring import (
    financial_risk_score,
)
from src.analysis.stock_analysis import (
    StockAnalysisReport,
    build_stock_analysis,
)
from src.data.company.financials import FinancialSnapshot
from src.data.providers.base import MarketDataProvider
from src.data.universe import load_symbols
from src.features.market_adapter import (
    build_market_feature_snapshot_from_provider,
)


@dataclass(frozen=True)
class MarketResearchResult:
    """
    Complete market research result for a universe.
    """

    as_of: date
    results: tuple[StockAnalysisReport, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(result.symbol for result in self.results)

    @property
    def successful_count(self) -> int:
        return len(self.results)


def _market_scores(
    report_snapshot,
) -> dict[str, Decimal]:
    """
    Convert available market observations into normalized
    research inputs.
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

    volatility = technical.volatility_20d

    if volatility is None:
        volatility_score = Decimal("50")
    elif volatility <= Decimal("1"):
        volatility_score = Decimal("90")
    elif volatility <= Decimal("2"):
        volatility_score = Decimal("80")
    elif volatility <= Decimal("3"):
        volatility_score = Decimal("70")
    elif volatility <= Decimal("5"):
        volatility_score = Decimal("55")
    elif volatility <= Decimal("8"):
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

    relative = (
        report_snapshot
        .relative_strength
        .relative_return_20d
    )

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


def _financial_scores(
    snapshots: list[FinancialSnapshot],
) -> dict[str, Decimal]:
    """
    Convert the latest available annual financial statements
    into normalized research inputs.

    The previous annual period is used for growth/trend analysis.

    No missing financial information is fabricated.
    """

    if not snapshots:
        return {
            "fundamentals": Decimal("50"),
            "financial_trends": Decimal("50"),
            "cash_flow": Decimal("50"),
            "balance_sheet": Decimal("50"),
        }

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    current = ordered[-1]

    previous = (
        ordered[-2]
        if len(ordered) >= 2
        else None
    )

    return score_financial_snapshot(
        previous=previous,
        current=current,
    )


def run_market_research(
    *,
    provider: MarketDataProvider,
    universe_file: str,
    benchmark_symbol: str,
    start_date: date,
    end_date: date,
    financial_provider=None,
) -> MarketResearchResult:
    """
    Run the provider -> financial -> market-feature ->
    analysis pipeline.

    Financial company-intelligence is populated from available
    normalized financial history. Other company-intelligence
    domains remain explicitly neutral until their providers
    are connected.
    """

    if start_date > end_date:
        raise ValueError(
            "start_date must not be after end_date"
        )

    symbols = load_symbols(universe_file)

    results: list[StockAnalysisReport] = []

    for symbol in symbols:
        try:
            snapshot = (
                build_market_feature_snapshot_from_provider(
                    provider=provider,
                    symbol=symbol,
                    benchmark_symbol=benchmark_symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        except ValueError:
            continue

        financial_snapshots: list[FinancialSnapshot] = []

        if financial_provider is not None:
            try:
                financial_snapshots = (
                    financial_provider.get_annual_financials(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )
            except (RuntimeError, ValueError):
                financial_snapshots = []

        financial_scores = _financial_scores(
            financial_snapshots
        )

        risk_score = financial_risk_score(
            financial_snapshots
        )

        market_scores = _market_scores(snapshot)

        company_snapshot = (
            build_financial_company_intelligence(
                symbol=symbol,
                as_of_date=snapshot.trading_date,
                snapshots=financial_snapshots,
            )
        )

        report = build_stock_analysis(
            symbol=symbol,
            as_of_date=snapshot.trading_date,
            company_intelligence=company_snapshot,
            market_snapshot=snapshot,

            fundamentals=financial_scores[
                "fundamentals"
            ],
            financial_trends=financial_scores[
                "financial_trends"
            ],
            cash_flow=financial_scores[
                "cash_flow"
            ],
            balance_sheet=financial_scores[
                "balance_sheet"
            ],

            risk=risk_score,
            management=Decimal("50"),
            market_behavior=Decimal("50"),
            evidence_quality=Decimal("50"),

            liquidity=Decimal("50"),
            relative_strength=market_scores[
                "relative_strength"
            ],
            catalyst_strength=Decimal("50"),
            valuation=Decimal("50"),
        )

        results.append(report)

    return MarketResearchResult(
        as_of=end_date,
        results=tuple(results),
    )
