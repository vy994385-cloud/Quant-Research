"""
L6 backtest / validation API contracts.

Pydantic response models for deterministic backtest results,
ranking validation quality, and historical strategy comparison.

All values describe historical observations only. They do not
predict future returns or generate trading instructions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContractBenchmarkComparison(BaseModel):
    """Historical buy-and-hold benchmark comparison."""

    model_config = ConfigDict(extra="forbid")

    benchmark_symbol: str

    benchmark_return: str
    strategy_return: str
    excess_return: str

    benchmark_max_drawdown: str
    benchmark_max_drawdown_percent: str

    outperforming: bool


class ContractBacktestReport(BaseModel):
    """Research summary of a completed historical backtest."""

    model_config = ConfigDict(extra="forbid")

    initial_capital: str
    final_equity: str
    profit_loss: str
    total_return: str

    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: str

    max_drawdown: str
    max_drawdown_percent: str

    exposure_percent: str
    cagr: str | None = None

    sample_size_warning: str | None = None
    research_signal: str
    limitations: list[str] = []

    benchmark: ContractBenchmarkComparison | None = None


class ContractValidationReport(BaseModel):
    """Auditable validation report with strengths/weaknesses."""

    model_config = ConfigDict(extra="forbid")

    horizon: str
    window_count: int
    observation_count: int

    average_forward_return: str
    median_forward_return: str
    positive_return_rate: str

    average_excess_return: str | None = None
    positive_excess_return_rate: str | None = None
    average_score_return_correlation: str | None = None

    successful_window_rate: str
    weak_window_count: int

    robust: bool

    strengths: list[str] = []
    weaknesses: list[str] = []
    unknowns: list[str] = []

    minimum_window_count: int
    minimum_successful_window_rate: str


class ContractValidationQuality(BaseModel):
    """Descriptive quality assessment of ranking validation."""

    model_config = ConfigDict(extra="forbid")

    quality: str
    score: str
    confidence: str
    observation_count: int

    average_forward_return: str
    median_forward_return: str
    positive_return_rate: str

    average_excess_return: str | None = None
    positive_excess_return_rate: str | None = None
    score_return_correlation: str | None = None

    reasons: list[str] = []

    is_actionable: bool = False
    is_strong: bool = False
    is_insufficient: bool = False


class ContractBacktestValidation(BaseModel):
    """Input validation result for a backtest run."""

    model_config = ConfigDict(extra="forbid")

    status: str
    errors: list[str] = []
    warnings: list[str] = []


class ContractValidationWindow(BaseModel):
    """One walk-forward validation window."""

    model_config = ConfigDict(extra="forbid")

    window_index: int
    train_start: str | None = None
    train_end: str | None = None
    validation_start: str | None = None
    validation_end: str | None = None
    observation_count: int
    average_forward_return: str
    positive_return_rate: str
    score_return_correlation: str | None = None


class CompanyBacktestContract(BaseModel):
    """Complete backtest + validation response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    horizon: str
    as_of: str

    backtest: ContractBacktestReport | None = None
    backtest_validation: ContractBacktestValidation | None = None
    validation_quality: ContractValidationQuality | None = None
    validation_report: ContractValidationReport | None = None

    windows: list[ContractValidationWindow] = []

    strategy_description: str = ""
    data_coverage: dict[str, int] = {}
    notes: list[str] = []


class UniverseValidationContract(BaseModel):
    """Cross-company validation comparison for one horizon."""

    model_config = ConfigDict(extra="forbid")

    # None when no universe results exist yet — missing data is null,
    # never an empty string.
    as_of: str | None
    horizon: str
    count: int
    results: list[CompanyBacktestContract]


__all__ = [
    "CompanyBacktestContract",
    "ContractBacktestReport",
    "ContractBacktestValidation",
    "ContractBenchmarkComparison",
    "ContractValidationQuality",
    "ContractValidationReport",
    "ContractValidationWindow",
    "UniverseValidationContract",
]
