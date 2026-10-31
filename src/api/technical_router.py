"""
Technical research API routes.

Exposes deep technical research data through typed contracts.
All indicators, observations, signals, and provenance are
returned via a single endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query

from src.api.query_utils import company_identity

from src.api.contracts import (
    CompanyDeepTechnicalContract,
    ContractDeepTechnicalResult,
    ContractTechnicalIndicatorSet,
    ContractTechnicalObservation,
    ContractTechnicalObservationSet,
)


def _d(val: Decimal | None) -> str | None:
    return str(val) if val is not None else None


def _serialize_indicators(indicators) -> ContractTechnicalIndicatorSet:
    """Convert TechnicalIndicatorResult to API contract."""
    return ContractTechnicalIndicatorSet(
        # Returns
        return_1d=_d(indicators.return_1d),
        return_5d=_d(indicators.return_5d),
        return_10d=_d(indicators.return_10d),
        return_20d=_d(indicators.return_20d),
        return_50d=_d(indicators.return_50d),
        return_100d=_d(indicators.return_100d),
        return_200d=_d(indicators.return_200d),
        # SMAs
        sma_5=_d(indicators.sma.sma_5),
        sma_10=_d(indicators.sma.sma_10),
        sma_20=_d(indicators.sma.sma_20),
        sma_50=_d(indicators.sma.sma_50),
        sma_100=_d(indicators.sma.sma_100),
        sma_200=_d(indicators.sma.sma_200),
        # EMAs
        ema_9=_d(indicators.ema.ema_9),
        ema_12=_d(indicators.ema.ema_12),
        ema_20=_d(indicators.ema.ema_20),
        ema_26=_d(indicators.ema.ema_26),
        ema_50=_d(indicators.ema.ema_50),
        ema_200=_d(indicators.ema.ema_200),
        # Price vs MAs
        price_vs_sma_5_pct=_d(indicators.price_vs_sma.price_vs_sma_5_pct),
        price_vs_sma_20_pct=_d(indicators.price_vs_sma.price_vs_sma_20_pct),
        price_vs_sma_50_pct=_d(indicators.price_vs_sma.price_vs_sma_50_pct),
        price_vs_ema_9_pct=_d(indicators.price_vs_ema.price_vs_ema_9_pct),
        price_vs_ema_20_pct=_d(indicators.price_vs_ema.price_vs_ema_20_pct),
        price_vs_ema_50_pct=_d(indicators.price_vs_ema.price_vs_ema_50_pct),
        # RSI
        rsi_14=_d(indicators.rsi.rsi_14),
        rsi_signal=indicators.rsi.signal,
        # MACD
        macd_line=_d(indicators.macd.macd_line),
        macd_signal_line=_d(indicators.macd.signal_line),
        macd_histogram=_d(indicators.macd.histogram),
        macd_crossover=indicators.macd.macd_crossover,
        # Stochastic
        stochastic_k=_d(indicators.stochastic.percent_k),
        stochastic_d=_d(indicators.stochastic.percent_d),
        stochastic_signal=indicators.stochastic.signal,
        # Williams %R
        williams_r_14=_d(indicators.williams_r.williams_r_14),
        williams_r_signal=indicators.williams_r.signal,
        # ATR
        atr_14=_d(indicators.atr.atr_14),
        atr_pct=_d(indicators.atr.atr_pct),
        # Bollinger
        bollinger_upper=_d(indicators.bollinger.upper),
        bollinger_middle=_d(indicators.bollinger.middle),
        bollinger_lower=_d(indicators.bollinger.lower),
        bollinger_bandwidth=_d(indicators.bollinger.bandwidth),
        bollinger_pct_b=_d(indicators.bollinger.pct_b),
        bollinger_signal=indicators.bollinger.signal,
        # ADX
        adx_14=_d(indicators.adx.adx_14),
        adx_plus_di=_d(indicators.adx.plus_di),
        adx_minus_di=_d(indicators.adx.minus_di),
        adx_signal=indicators.adx.signal,
        # CCI
        cci_20=_d(indicators.cci.cci_20),
        cci_signal=indicators.cci.signal,
        # Volume
        obv=indicators.volume_indicators.obv,
        ad_line=_d(indicators.volume_indicators.accumulation_distribution),
        mfi_14=_d(indicators.volume_indicators.mfi_14),
        mfi_signal=indicators.volume_indicators.mfi_signal,
        price_volume_divergence=indicators.volume_indicators.price_volume_divergence,
        # Pivots
        pivot=_d(indicators.pivots.pivot),
        r1=_d(indicators.pivots.r1),
        r2=_d(indicators.pivots.r2),
        r3=_d(indicators.pivots.r3),
        s1=_d(indicators.pivots.s1),
        s2=_d(indicators.pivots.s2),
        s3=_d(indicators.pivots.s3),
        # Breakout
        breakout_signal=indicators.breakout.signal,
        # Gaps
        gap_type=indicators.gaps.gap_type,
        gap_pct=_d(indicators.gaps.gap_pct),
        # 52-week
        high_52w=_d(indicators.high_low.high_52w),
        low_52w=_d(indicators.high_low.low_52w),
        pct_from_52w_high=_d(indicators.high_low.pct_from_high),
        pct_from_52w_low=_d(indicators.high_low.pct_from_low),
        high_low_signal=indicators.high_low.signal,
        # Drawdowns
        current_drawdown=_d(indicators.drawdowns.current_drawdown),
        max_drawdown_20d=_d(indicators.drawdowns.max_drawdown_20d),
        recovery_pct=_d(indicators.drawdowns.recovery_pct),
        # Trend
        regime=indicators.trend_structure.regime,
        trend_strength=_d(indicators.trend_structure.trend_strength),
        sma_alignment=indicators.trend_structure.sma_alignment,
        ema_alignment=indicators.trend_structure.ema_alignment,
    )


def _serialize_observation(obs) -> ContractTechnicalObservation:
    """Convert TechnicalObservation to API contract."""
    return ContractTechnicalObservation(
        observation_id=obs.observation_id,
        symbol=obs.symbol,
        category=obs.category,
        observation_type=obs.observation_type,
        indicator=obs.indicator,
        period=obs.period,
        value=obs.value if obs.value is not None else None,
        signal=obs.signal,
        direction=obs.direction,
        severity=obs.severity,
        explanation=obs.explanation,
        source=obs.source,
        available_at=obs.available_at,
        as_of=obs.as_of,
        status=obs.status,
        supporting_data={
            k: v for k, v in obs.supporting_data.items()
            if v is not None
        },
    )


def _serialize_observation_set(obs_set) -> ContractTechnicalObservationSet:
    """Convert TechnicalObservationSet to API contract."""
    return ContractTechnicalObservationSet(
        symbol=obs_set.symbol,
        as_of=obs_set.as_of,
        trading_date=obs_set.trading_date,
        indicator_observations=[
            _serialize_observation(o) for o in obs_set.indicator_observations
        ],
        signal_observations=[
            _serialize_observation(o) for o in obs_set.signal_observations
        ],
        total_count=obs_set.total_count,
        positive_count=obs_set.positive_count,
        negative_count=obs_set.negative_count,
        neutral_count=obs_set.neutral_count,
        available_indicators=list(obs_set.available_indicators),
        missing_indicators=list(obs_set.missing_indicators),
    )


def create_technical_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["technical"],
    )

    @router.get(
        "/{symbol}/deep-technicals",
        response_model=CompanyDeepTechnicalContract,
    )
    async def get_deep_technicals(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> CompanyDeepTechnicalContract:
        """
        Deep technical research for a company.

        Returns all computed indicators, observations with
        provenance, and signal-level assessments.
        """
        from src.analysis.deep_technical import analyze_deep_technicals
        from src.data.providers.yahoo_provider import (
            YahooFinanceMarketDataProvider,
        )

        provider = YahooFinanceMarketDataProvider()

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )

        end_date = as_of_dt.date()
        from datetime import timedelta

        start_date = end_date - timedelta(days=800)

        bars = provider.get_daily_prices(symbol, start_date, end_date)

        result = analyze_deep_technicals(
            bars=bars,
            benchmark_bars=None,
            symbol=symbol,
            as_of=as_of_dt,
        )

        # Build company dict
        company_info = company_identity(symbol, as_of=as_of_dt)

        # Serialize indicators
        indicators_contract = None
        if result.indicators is not None:
            indicators_contract = _serialize_indicators(result.indicators)

        # Serialize observations
        obs_contract = None
        if result.observation_set is not None:
            obs_contract = _serialize_observation_set(result.observation_set)

        return CompanyDeepTechnicalContract(
            company=company_info,
            deep_technicals=ContractDeepTechnicalResult(
                symbol=result.symbol,
                as_of=result.as_of,
                trading_date=result.trading_date,
                bars_used=result.bars_used,
                indicators=indicators_contract,
                observation_set=obs_contract,
                available_indicators=list(result.available_indicators),
                missing_indicators=list(result.missing_indicators),
                notes=list(result.notes),
            ),
        )


    @router.get("/{symbol}/price-history")
    async def get_price_history(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> dict:
        """Return point-in-time daily OHLCV bars for price-chart rendering."""
        from datetime import timedelta
        from src.data.providers.yahoo_provider import YahooFinanceMarketDataProvider

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )
        end_date = as_of_dt.date()
        start_date = end_date - timedelta(days=800)
        provider = YahooFinanceMarketDataProvider()
        bars = provider.get_daily_prices(symbol, start_date, end_date)
        pit_bars = [bar for bar in bars if bar.trading_date <= end_date]

        return {
            "symbol": symbol.upper(),
            "as_of": as_of_dt.isoformat(),
            "bars": [
                {
                    "trading_date": bar.trading_date.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                    "volume": bar.volume,
                    "adjusted_close": str(bar.adjusted_close) if bar.adjusted_close is not None else None,
                }
                for bar in pit_bars
            ],
            "bars_returned": len(pit_bars),
            "history_start": pit_bars[0].trading_date.isoformat() if pit_bars else None,
            "history_end": pit_bars[-1].trading_date.isoformat() if pit_bars else None,
            "price_basis": "provider OHLC; adjusted_close supplied separately when available",
        }

    return router
