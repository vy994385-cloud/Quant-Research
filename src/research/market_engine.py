from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.data.providers.base import MarketDataProvider
from src.data.universe import load_symbols
from src.analysis.stock_engine import StockEngineResult


@dataclass(frozen=True)
class MarketResearchResult:
    as_of: date
    results: tuple[StockEngineResult, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(result.symbol for result in self.results)

    @property
    def successful_count(self) -> int:
        return len(self.results)


def run_market_research(
    *,
    provider: MarketDataProvider,
    universe_file: str,
    start_date: date,
    end_date: date,
) -> MarketResearchResult:
    symbols = load_symbols(universe_file)

    results: list[StockEngineResult] = []

    engine = None

    for symbol in symbols:
        prices = provider.get_daily_prices(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if not prices:
            continue

        if engine is None:
            engine = StockEngineResult

        # Provider-to-engine integration is intentionally
        # completed by the market adapter layer.
        #
        # For now, verify that the provider successfully
        # produced normalized market data.
        results.append(
            StockEngineResult(
                symbol=symbol,
                price_count=len(prices),
            )
        )

    return MarketResearchResult(
        as_of=end_date,
        results=tuple(results),
    )
