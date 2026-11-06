from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from src.data.providers.yahoo_provider import YahooFinanceMarketDataProvider

from .market_contracts import (
    MarketBreadthContract,
    MarketCoverageContract,
    MarketIndexContract,
    MarketOverviewContract,
    MarketSectorContract,
    MarketSecurityContract,
)
from .universe.provider import UniverseProvider


class V2MarketService:
    """
    Observable market state for QRQuant V2.

    V2 deliberately bypasses the legacy research engine.

    Equity membership and identity are owned by UniverseProvider.
    Equity prices and metadata come from Yahoo Chart through that
    provider. Index prices are fetched directly because indices are
    not members of the configured equity universe.

    No scores, rankings, signals, recommendations, research readiness,
    or legacy profile/research models are used here.
    """

    _cache_lock = Lock()
    _overview_cache: tuple[float, MarketOverviewContract] | None = None

    OVERVIEW_TTL_SECONDS = 60

    INDEXES = (
        ("^NSEI", "NIFTY 50"),
        ("^BSESN", "SENSEX"),
        ("^NSEBANK", "NIFTY BANK"),
        ("^CNXIT", "NIFTY IT"),
    )

    # Only indexes with verified daily-history coverage are exposed
    # through the V2 Sector Context contract. Unsupported symbols are
    # deliberately not presented as sector performance.
    SECTOR_INDEXES = (
        ("^CNXIT", "NIFTY IT"),
        ("^NSEBANK", "NIFTY BANK"),
        ("^CNXPHARMA", "NIFTY PHARMA"),
    )

    def __init__(self) -> None:
        self.universe_provider = UniverseProvider()
        self.market_provider = YahooFinanceMarketDataProvider()

    @staticmethod
    def _pct(
        current: float,
        previous: float,
    ) -> float | None:
        if previous == 0:
            return None

        return ((current / previous) - 1.0) * 100.0

    def _security(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> MarketSecurityContract | None:
        try:
            bars, security = self.universe_provider.get_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            return None

        if len(bars) < 2:
            return None

        bars = sorted(
            bars,
            key=lambda item: item.trading_date,
        )

        latest = bars[-1]
        previous = bars[-2]

        latest_close = float(latest.close)
        previous_close = float(previous.close)

        change_pct = self._pct(
            latest_close,
            previous_close,
        )

        if change_pct is None:
            return None

        recent = bars[-21:-1]

        average_volume = None

        if recent:
            average_volume = (
                sum(int(bar.volume) for bar in recent)
                / len(recent)
            )

        volume_ratio = None

        if average_volume and average_volume > 0:
            volume_ratio = (
                int(latest.volume)
                / average_volume
            )

        return MarketSecurityContract(
            symbol=security.symbol,
            name=security.company_name or security.symbol,
            sector=security.sector,
            price=latest_close,
            change_pct=change_pct,
            volume=int(latest.volume),
            average_volume_20d=average_volume,
            volume_ratio=volume_ratio,
            trading_date=latest.trading_date,
        )

    def _index(
        self,
        symbol: str,
        name: str,
        start_date: date,
        end_date: date,
    ) -> MarketIndexContract | None:
        try:
            bars = self.market_provider.get_daily_prices(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            return None

        if not bars:
            return None

        bars = sorted(
            bars,
            key=lambda item: item.trading_date,
        )

        latest = bars[-1]
        previous = (
            bars[-2]
            if len(bars) >= 2
            else None
        )

        change = None
        change_pct = None

        if previous is not None:
            change = float(
                latest.close - previous.close
            )
            change_pct = self._pct(
                float(latest.close),
                float(previous.close),
            )

        return MarketIndexContract(
            symbol=symbol,
            name=name,
            price=float(latest.close),
            change=change,
            change_pct=change_pct,
            trading_date=latest.trading_date,
        )

    @staticmethod
    def _build_breadth(
        securities: list[MarketSecurityContract],
    ) -> MarketBreadthContract:
        advancing = sum(
            1
            for item in securities
            if item.change_pct is not None
            and item.change_pct > 0
        )

        declining = sum(
            1
            for item in securities
            if item.change_pct is not None
            and item.change_pct < 0
        )

        unchanged = sum(
            1
            for item in securities
            if item.change_pct is not None
            and item.change_pct == 0
        )

        return MarketBreadthContract(
            advancing=advancing,
            declining=declining,
            unchanged=unchanged,
            total=len(securities),
        )

    @staticmethod
    def _build_sectors(
        securities: list[MarketSecurityContract],
    ) -> list[MarketSectorContract]:
        """
        Build sector aggregates only when sector metadata actually
        exists.

        V2 never guesses sector membership. If the configured
        universe does not currently provide sectors, the result is
        simply an empty sector collection.
        """

        grouped: dict[
            str,
            list[MarketSecurityContract],
        ] = {}

        for security in securities:
            if not security.sector:
                continue

            grouped.setdefault(
                security.sector,
                [],
            ).append(security)

        sectors: list[MarketSectorContract] = []

        for name, members in grouped.items():
            advancing = sum(
                1
                for item in members
                if item.change_pct is not None
                and item.change_pct > 0
            )

            declining = sum(
                1
                for item in members
                if item.change_pct is not None
                and item.change_pct < 0
            )

            unchanged = sum(
                1
                for item in members
                if item.change_pct is not None
                and item.change_pct == 0
            )

            changes = [
                item.change_pct
                for item in members
                if item.change_pct is not None
            ]

            average_change_pct = (
                sum(changes) / len(changes)
                if changes
                else None
            )

            sectors.append(
                MarketSectorContract(
                    name=name,
                    securities=len(members),
                    advancing=advancing,
                    declining=declining,
                    unchanged=unchanged,
                    average_change_pct=average_change_pct,
                )
            )

        sectors.sort(
            key=lambda item: (
                item.average_change_pct
                if item.average_change_pct is not None
                else 0
            ),
            reverse=True,
        )

        return sectors

    def overview(self) -> MarketOverviewContract:
        now = monotonic()

        with self._cache_lock:
            cached = self._overview_cache

        if (
            cached is not None
            and now - cached[0] < self.OVERVIEW_TTL_SECONDS
        ):
            return cached[1]

        universe = [
            security.symbol
            for security in self.universe_provider.securities()
        ]

        end_date = date.today()
        start_date = end_date - timedelta(days=45)

        securities: list[MarketSecurityContract] = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    self._security,
                    symbol,
                    start_date,
                    end_date,
                ): symbol
                for symbol in universe
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception:
                    result = None

                if result is not None:
                    securities.append(result)

        securities.sort(
            key=lambda item: (
                item.change_pct
                if item.change_pct is not None
                else 0
            ),
            reverse=True,
        )

        gainers = [
            item
            for item in securities
            if item.change_pct is not None
            and item.change_pct > 0
        ][:10]

        losers = sorted(
            [
                item
                for item in securities
                if item.change_pct is not None
                and item.change_pct < 0
            ],
            key=lambda item: item.change_pct or 0,
        )[:10]

        active = sorted(
            securities,
            key=lambda item: item.volume or 0,
            reverse=True,
        )[:10]

        breadth = self._build_breadth(securities)
        sectors = self._build_sectors(securities)

        # Fetch each unique index symbol once. Some symbols appear in both
        # the broad-index and sector-index collections (for example ^CNXIT).
        index_names = dict(self.INDEXES)
        for symbol, name in self.SECTOR_INDEXES:
            index_names.setdefault(symbol, name)

        unique_index_results: dict[str, MarketIndexContract] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    self._index,
                    symbol,
                    name,
                    start_date,
                    end_date,
                ): symbol
                for symbol, name in index_names.items()
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                except Exception:
                    result = None

                if result is not None:
                    unique_index_results[symbol] = result

        indices = [
            unique_index_results[symbol]
            for symbol, _name in self.INDEXES
            if symbol in unique_index_results
        ]

        sector_indices = [
            unique_index_results[symbol].model_copy(
                update={"name": name}
            )
            for symbol, name in self.SECTOR_INDEXES
            if symbol in unique_index_results
        ]

        available_symbols = {
            security.symbol
            for security in securities
        }

        sectors_with_data = sum(
            1
            for security in securities
            if security.sector
        )

        if len(available_symbols) == len(universe):
            coverage_status = "complete"
        elif available_symbols:
            coverage_status = "partial"
        else:
            coverage_status = "limited"

        price_dates = [
            security.trading_date
            for security in securities
            if security.trading_date is not None
        ]

        price_date = (
            max(price_dates)
            if price_dates
            else None
        )

        result = MarketOverviewContract(
            as_of=datetime.now(timezone.utc),
            price_date=price_date,
            indices=indices,
            sector_indices=sector_indices,
            breadth=breadth,
            gainers=gainers,
            losers=losers,
            active=active,
            sectors=sectors,
            coverage=MarketCoverageContract(
                universe=(
                    "NSE equity universe configured "
                    "in QRQuant"
                ),
                securities_available=len(universe),
                securities_with_prices=len(
                    available_symbols
                ),
                securities_with_sector=sectors_with_data,
                coverage_status=coverage_status,
            ),
        )

        with self._cache_lock:
            self._overview_cache = (
                monotonic(),
                result,
            )

        return result
