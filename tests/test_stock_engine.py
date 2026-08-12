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
