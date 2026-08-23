"""
O-TRACK Phase 3 — financial output contract regression tests.

Pins the production-grade financial output semantics:

- deterministic quantization: division results (ratios, margins,
  period-over-period changes) never carry long decimal tails;
- human-readable derivations: no formula syntax and no raw
  internal identifiers (period IDs / feature IDs) in any
  user-facing derivation string;
- explicit units: ratios stay ratios (FRACTION), currency stays
  currency (INR) — never mixed, never implicit;
- missing values stay null and are never fabricated as zero;
- reported values pass through untouched (no re-scaling);
- chart data declares its currency and rounds deterministically
  with ROUND_HALF_UP;
- PIT metadata (published_at / available_at) is preserved end to end.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.analysis.chart_data import (
    ChartUnit,
    build_chart_data,
)
from src.api.contracts import ContractDeepFinancialInsights
from src.api.serializers import _deep_financial_insights
from src.data.company.financials import FinancialSnapshot
from src.research.company_intel import (
    build_financial_intelligence,
    derived_metric_items,
    financial_periods_from_snapshots,
)
from src.research.company_intel.deep_financial import (
    build_deep_financial_insights,
)
from src.research.company_intel.derived import (
    _revenue_receivables_divergence,
    build_hidden_information,
)
from src.research.company_intel.models import (
    DeepMetricObservation,
    FinancialPeriod,
)
from src.research.company_intel.semantics import (
    ConsolidationScope,
    ReportingPeriodType,
)

TZ = timezone.utc

AS_OF = datetime(2026, 8, 10, tzinfo=TZ)


def ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=TZ)


def _snapshot(
    period_end: date,
    *,
    revenue: str | None = None,
    operating_profit: str | None = None,
    net_profit: str | None = None,
    total_assets: str | None = None,
    total_debt: str | None = None,
    cash: str | None = None,
    operating_cash_flow: str | None = None,
    available_at: datetime | None = AS_OF,
    published_at: datetime | None = None,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TCS",
        period_end=period_end,
        revenue=revenue,
        operating_profit=operating_profit,
        net_profit=net_profit,
        total_assets=total_assets,
        total_debt=total_debt,
        cash_and_equivalents=cash,
        operating_cash_flow=operating_cash_flow,
        available_at=available_at,
        published_at=published_at,
    )


def _insights(snapshots):
    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )
    fi = build_financial_intelligence(
        "TCS",
        periods,
        as_of=AS_OF,
    )
    return build_deep_financial_insights(fi, as_of=AS_OF)


def _obs_by_metric(insights) -> dict:
    """Latest observation per metric."""
    latest: dict = {}
    for obs in insights.observations:
        current = latest.get(obs.metric)
        if current is None or obs.period_end > current.period_end:
            latest[obs.metric] = obs
    return latest


# ---------------------------------------------------------------------------
# Deterministic quantization — no long decimal tails
# ---------------------------------------------------------------------------


class TestDeterministicQuantization:
    def test_delta_pct_has_no_long_tail(self):
        # 60 -> 70 produces the repeating fraction 10/60; the stored
        # delta_pct must be the six-decimal rounded value.
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="60"),
                _snapshot(date(2026, 3, 31), revenue="70"),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.delta_pct == Decimal("0.166667")

    def test_derived_ratio_value_has_no_long_tail(self):
        # 20/60 is a repeating decimal; the derived margin must be
        # quantized at build time, not serialized with 28+ digits.
        insights = _insights(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="60",
                    operating_profit="20",
                    total_assets="500",
                ),
            ]
        )
        obs = _obs_by_metric(insights)["operating_margin"]

        assert obs.value == Decimal("0.333333")
        assert len(str(obs.value)) <= len("0.333333") + 2

    def test_derived_previous_value_is_quantized(self):
        insights = _insights(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="60",
                    operating_profit="20",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue="80",
                    operating_profit="30",
                ),
            ]
        )

        margins = [
            obs
            for obs in insights.observations
            if obs.metric == "operating_margin"
            and obs.observation_type.value == "DERIVED"
        ]

        by_period_end = {
            obs.period_end: obs for obs in margins
        }

        assert (
            by_period_end[date(2025, 3, 31)].value
            == Decimal("0.333333")
        )
        assert (
            by_period_end[date(2026, 3, 31)].previous_value
            == Decimal("0.333333")
        )
        assert (
            by_period_end[date(2026, 3, 31)].value
            == Decimal("0.375000")
        )

    def test_reported_values_pass_through_unscaled(self):
        insights = _insights(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="1234567890000",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue="1334567890000",
                ),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.value == Decimal("1334567890000")
        assert obs.observation_type.value == "REPORTED"

    def test_serialized_delta_pct_string_is_short(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="60"),
                _snapshot(date(2026, 3, 31), revenue="70"),
            ]
        )
        payload = _deep_financial_insights(insights)

        revenue_obs = next(
            o
            for o in payload["observations"]
            if o["metric"] == "revenue"
            and o["delta_pct"] is not None
        )

        assert revenue_obs["delta_pct"] == "0.166667"
        assert len(revenue_obs["delta_pct"]) <= 8


# ---------------------------------------------------------------------------
# Human-readable derivations — no formulas, no raw IDs
# ---------------------------------------------------------------------------

_FORBIDDEN_DERIVATION_MARKERS = (
    "/",      # formula syntax
    "[",      # index notation
    "]",      # index notation
    "(",      # function-call syntax
    ")",      # function-call syntax
    "_",      # raw feature/metric identifiers
    "%",      # bare percent signs in threshold formulas
    ":",      # raw internal ID separators
)


def assert_clean_derivation(text: str) -> None:
    assert text, "derivation must be present"
    for marker in _FORBIDDEN_DERIVATION_MARKERS:
        assert marker not in text, (
            f"derivation contains {marker!r}: {text!r}"
        )


class TestHumanReadableDerivations:
    def test_every_deep_observation_derivation_is_clean(self):
        insights = _insights(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="100",
                    operating_profit="25",
                    net_profit="20",
                    total_assets="500",
                    total_debt="200",
                    cash="50",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue=None,
                    operating_profit=None,
                    net_profit="22",
                    total_assets="520",
                ),
                _snapshot(
                    date(2026, 6, 30),
                    available_at=ts(2026, 7, 15),
                    revenue="40",
                    net_profit="5",
                ),
            ]
        )

        assert insights.observations

        for obs in insights.observations:
            assert_clean_derivation(obs.derivation)

    def test_all_derivation_types_are_covered_and_clean(self):
        insights = _insights(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="100",
                    operating_profit="25",
                    total_assets="500",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue=None,
                    net_profit=None,
                    total_assets=None,
                ),
            ]
        )

        derivations_by_type: dict = {}
        for obs in insights.observations:
            assert_clean_derivation(obs.derivation)
            derivations_by_type.setdefault(
                obs.observation_type.value, set()
            ).add(obs.derivation)

        # All three derivation families must be exercised and each
        # family must use stable, human-readable phrasing.
        assert {"REPORTED", "DERIVED", "UNAVAILABLE"} <= set(
            derivations_by_type
        )

        reported_phrasings = derivations_by_type["REPORTED"]
        for text in reported_phrasings:
            assert text.startswith("Reported value")

        derived_phrasings = derivations_by_type["DERIVED"]
        for text in derived_phrasings:
            assert text.startswith("Derived as ")

        unavailable_phrasings = derivations_by_type["UNAVAILABLE"]
        for text in unavailable_phrasings:
            assert (
                text.startswith("Not reported ")
                or text.startswith("Not derivable ")
            )

    def test_reported_derivation_states_period(self):
        insights = _insights(
            [
                _snapshot(date(2026, 3, 31), revenue="100"),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.derivation == (
            "Reported value for the period ending 2026-03-31."
        )

    def test_reported_comparison_derivation_states_both_periods(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="100"),
                _snapshot(date(2026, 3, 31), revenue="110"),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.derivation == (
            "Reported value for the period ending 2026-03-31, "
            "compared with the period ending 2025-03-31."
        )

    def test_derived_derivation_names_operation_in_words(self):
        insights = _insights(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="100",
                    operating_profit="25",
                ),
            ]
        )
        obs = _obs_by_metric(insights)["operating_margin"]

        assert obs.derivation == (
            "Derived as operating profit divided by revenue "
            "for the period ending 2026-03-31."
        )

    def test_unavailable_derivation_states_gap(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="100"),
                _snapshot(date(2026, 3, 31), revenue=None),
            ]
        )

        unavailable = [
            obs
            for obs in insights.observations
            if obs.metric == "revenue"
            and obs.period_end == date(2026, 3, 31)
        ]

        assert len(unavailable) == 1
        assert unavailable[0].observation_type.value == "UNAVAILABLE"
        assert unavailable[0].derivation == (
            "Not reported for the period ending 2026-03-31."
        )

    def test_underivable_derivation_explains_missing_input(self):
        insights = _insights(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="100",
                    operating_profit="25",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue=None,
                    operating_profit=None,
                ),
            ]
        )

        underivable = [
            obs
            for obs in insights.observations
            if obs.metric == "operating_margin"
            and obs.period_end == date(2026, 3, 31)
        ]

        assert len(underivable) == 1
        assert underivable[0].value is None
        assert underivable[0].derivation == (
            "Not derivable because required reported figures are "
            "missing for the period ending 2026-03-31."
        )

    def test_derived_metric_items_have_clean_derivations(self):
        periods = financial_periods_from_snapshots(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="100",
                    operating_profit="20",
                )
            ],
            as_of=AS_OF,
        )

        items = derived_metric_items(periods, as_of=AS_OF)

        assert items
        for item in items:
            assert_clean_derivation(item.derivation)

        margin_item = next(
            item
            for item in items
            if "margin" in item.item_id
        )
        assert margin_item.derivation.startswith("Derived as ")

    def test_divergence_derivations_are_human_readable(self):
        def fp(period_end, metrics):
            return FinancialPeriod(
                period_id=f"TCS:{period_end.isoformat()}",
                symbol="TCS",
                period_end=period_end,
                period_type=ReportingPeriodType.ANNUAL,
                consolidation=ConsolidationScope.CONSOLIDATED,
                metrics=metrics,
                available_at=AS_OF,
            )

        observations = _revenue_receivables_divergence(
            (
                fp(
                    date(2025, 3, 31),
                    {
                        "revenue": Decimal("100"),
                        "receivables": Decimal("20"),
                    },
                ),
                fp(
                    date(2026, 3, 31),
                    {
                        "revenue": Decimal("110"),
                        "receivables": Decimal("30"),
                    },
                ),
            ),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert len(observations) == 1
        derivation = observations[0].derivation
        assert derivation == (
            "Receivables percentage change exceeded twice the "
            "revenue percentage change."
        )

    def test_hidden_information_gap_derivation_is_clean(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="100"),
                _snapshot(date(2026, 3, 31), revenue=None),
            ]
        )

        result = build_hidden_information(
            (),
            symbol="TCS",
            as_of=AS_OF,
            deep_financial_insights=insights,
        )

        gap_observations = [
            obs
            for obs in result.observations
            if "not reported" in obs.label.lower()
        ]

        assert gap_observations
        for obs in gap_observations:
            assert_clean_derivation(obs.derivation)


# ---------------------------------------------------------------------------
# Explicit units — ratios are never currency
# ---------------------------------------------------------------------------


class TestObservationUnits:
    def test_currency_metrics_declare_inr(self):
        insights = _insights(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="100",
                    total_assets="500",
                    total_debt="200",
                    cash="50",
                ),
            ]
        )
        obs = _obs_by_metric(insights)

        assert obs["revenue"].unit == "INR"
        assert obs["total_assets"].unit == "INR"
        assert obs["net_debt"].unit == "INR"

    def test_ratio_metrics_declare_fraction(self):
        insights = _insights(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="100",
                    operating_profit="25",
                    net_profit="20",
                    operating_cash_flow="30",
                    total_assets="500",
                ),
            ]
        )
        obs = _obs_by_metric(insights)

        assert obs["operating_margin"].unit == "FRACTION"
        assert obs["net_margin"].unit == "FRACTION"
        assert obs["cash_conversion"].unit == "FRACTION"
        assert obs["return_on_assets"].unit == "FRACTION"

    def test_model_rejects_unknown_unit(self):
        with pytest.raises(ValidationError):
            DeepMetricObservation(
                observation_id="x",
                symbol="TCS",
                metric="revenue",
                period_id="p1",
                period_end=date(2026, 3, 31),
                period_type=ReportingPeriodType.ANNUAL,
                consolidation=ConsolidationScope.UNKNOWN,
                unit="PERCENT",
            )

    def test_serializer_emits_unit_and_contract_accepts_it(self):
        insights = _insights(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="100",
                    operating_profit="25",
                ),
            ]
        )
        payload = _deep_financial_insights(insights)

        for serialized in payload["observations"]:
            assert "unit" in serialized
            assert serialized["unit"] in {"INR", "FRACTION"}

        # The API response contract must accept the emitted shape.
        validated = ContractDeepFinancialInsights.model_validate(payload)
        assert validated.observations
        assert validated.observations[0].unit in {"INR", "FRACTION"}


# ---------------------------------------------------------------------------
# Missing values stay null — never fabricated zeros
# ---------------------------------------------------------------------------


class TestMissingValueSemantics:
    def test_unavailable_value_is_null_not_zero(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="100"),
                _snapshot(date(2026, 3, 31), revenue=None),
            ]
        )

        unavailable = [
            obs
            for obs in insights.observations
            if obs.metric == "revenue"
            and obs.period_end == date(2026, 3, 31)
        ]

        assert unavailable[0].value is None
        assert unavailable[0].delta_pct is None

    def test_delta_pct_is_null_when_previous_missing(self):
        insights = _insights(
            [
                _snapshot(date(2026, 3, 31), revenue="100"),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.previous_value is None
        assert obs.delta is None
        assert obs.delta_pct is None

    def test_zero_denominator_yields_null_delta_pct(self):
        insights = _insights(
            [
                _snapshot(date(2025, 3, 31), revenue="0"),
                _snapshot(date(2026, 3, 31), revenue="50"),
            ]
        )
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.previous_value == Decimal("0")
        assert obs.delta == Decimal("50")
        assert obs.delta_pct is None


# ---------------------------------------------------------------------------
# PIT preservation
# ---------------------------------------------------------------------------


class TestPitPreservation:
    def test_timestamps_carry_through_to_observations(self):
        snapshots = [
            _snapshot(
                date(2025, 3, 31),
                revenue="100",
                published_at=ts(2025, 4, 30),
                available_at=ts(2025, 5, 2),
            ),
            _snapshot(
                date(2026, 3, 31),
                revenue="110",
                published_at=ts(2026, 4, 30),
                available_at=ts(2026, 5, 2),
            ),
        ]

        insights = _insights(snapshots)
        obs = _obs_by_metric(insights)["revenue"]

        assert obs.published_at == ts(2026, 4, 30)
        assert obs.available_at == ts(2026, 5, 2)

    def test_future_periods_never_enter_output(self):
        snapshots = [
            _snapshot(
                date(2026, 3, 31),
                revenue="100",
                available_at=ts(2030, 1, 1),
            ),
        ]

        insights = build_deep_financial_insights(
            build_financial_intelligence(
                "TCS",
                financial_periods_from_snapshots(
                    snapshots, as_of=AS_OF
                ),
                as_of=AS_OF,
            ),
            as_of=AS_OF,
        )

        assert insights.observations == ()
        assert any(
            "knowable" in note for note in insights.comparability_notes
        )


# ---------------------------------------------------------------------------
# Chart data — declared currency + ROUND_HALF_UP rounding
# ---------------------------------------------------------------------------


class TestChartFinancialSemantics:
    def test_currency_series_declare_inr(self):
        ds = build_chart_data(
            [
                _snapshot(date(2025, 3, 31), revenue="100"),
                _snapshot(date(2026, 3, 31), revenue="110"),
            ],
            "TCS",
            AS_OF,
        )

        revenue_series = next(
            s for s in ds.series if s.metric == "revenue"
        )
        assert revenue_series.unit == ChartUnit.CURRENCY
        assert revenue_series.currency == "INR"

    def test_ratio_series_carry_no_currency(self):
        ds = build_chart_data(
            [
                _snapshot(
                    date(2025, 3, 31),
                    revenue="100",
                    net_profit="10",
                ),
                _snapshot(
                    date(2026, 3, 31),
                    revenue="120",
                    net_profit="14",
                ),
            ],
            "TCS",
            AS_OF,
        )

        margin_series = next(
            s
            for s in ds.series
            if s.metric == "net_profit_margin"
        )
        assert margin_series.unit == ChartUnit.PERCENTAGE
        assert margin_series.currency is None

    def test_ratio_rounding_is_round_half_up(self):
        # 1234565 / 10000000 * 100 = 12.345650 exactly halfway at the
        # fourth decimal place: HALF_UP must produce 12.3457 while the
        # previous context-default HALF_EVEN produced 12.3456.
        ds = build_chart_data(
            [
                _snapshot(
                    date(2026, 3, 31),
                    revenue="10000000",
                    net_profit="1234565",
                ),
            ],
            "TCS",
            AS_OF,
        )

        margin_series = next(
            s
            for s in ds.series
            if s.metric == "net_profit_margin"
        )

        point = margin_series.data_points[0]
        assert point.value == "12.3457"

    def test_missing_points_stay_null(self):
        ds = build_chart_data(
            [
                _snapshot(date(2025, 3, 31)),
                _snapshot(date(2026, 3, 31), revenue="110"),
            ],
            "TCS",
            AS_OF,
        )

        revenue_series = next(
            s for s in ds.series if s.metric == "revenue"
        )
        first_point = revenue_series.data_points[0]

        assert first_point.value is None
        assert first_point.available is False
        assert revenue_series.missing_count >= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestOutputDeterminism:
    def test_deep_financial_build_is_deterministic(self):
        snapshots = [
            _snapshot(
                date(2025, 3, 31),
                revenue="100",
                operating_profit="25",
                total_assets="500",
            ),
            _snapshot(
                date(2026, 3, 31),
                revenue="110",
                operating_profit="27",
                total_assets="520",
            ),
        ]

        first = _insights(list(snapshots)).model_dump(mode="json")
        second = _insights(list(snapshots)).model_dump(mode="json")

        assert first == second

    def test_chart_data_build_is_deterministic(self):
        snapshots = [
            _snapshot(date(2025, 3, 31), revenue="100"),
            _snapshot(date(2026, 3, 31), revenue="110"),
        ]

        first = build_chart_data(snapshots, "TCS", AS_OF)
        second = build_chart_data(snapshots, "TCS", AS_OF)

        assert first == second
