from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import CompanyResearchSnapshot
from src.features.market_snapshot import MarketFeatureSnapshot
from src.analysis.stock_analysis import (
    StockAnalysisReport,
    build_stock_analysis,
)


@dataclass(frozen=True)
class StockAnalysisInput:
    symbol: str
    as_of_date: date
    company_intelligence: CompanyResearchSnapshot
    market_snapshot: MarketFeatureSnapshot

    fundamentals: Decimal
    financial_trends: Decimal
    cash_flow: Decimal
    balance_sheet: Decimal
    risk: Decimal
    management: Decimal
    market_behavior: Decimal
    evidence_quality: Decimal

    liquidity: Decimal
    relative_strength: Decimal
    catalyst_strength: Decimal
    valuation: Decimal

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        object.__setattr__(self, "symbol", symbol)


class StockAnalysisEngine:
    """
    Main entry point for deterministic stock research analysis.

    Data acquisition is deliberately outside this class.
    """

    def run(
        self,
        data: StockAnalysisInput,
    ) -> StockAnalysisReport:
        return build_stock_analysis(
            symbol=data.symbol,
            as_of_date=data.as_of_date,
            company_intelligence=data.company_intelligence,
            market_snapshot=data.market_snapshot,
            fundamentals=data.fundamentals,
            financial_trends=data.financial_trends,
            cash_flow=data.cash_flow,
            balance_sheet=data.balance_sheet,
            risk=data.risk,
            management=data.management,
            market_behavior=data.market_behavior,
            evidence_quality=data.evidence_quality,
            liquidity=data.liquidity,
            relative_strength=data.relative_strength,
            catalyst_strength=data.catalyst_strength,
            valuation=data.valuation,
        )


def run_stock_analysis(
    data: StockAnalysisInput,
) -> StockAnalysisReport:
    return StockAnalysisEngine().run(data)
