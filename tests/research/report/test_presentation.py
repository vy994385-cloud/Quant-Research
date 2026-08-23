"""
Tests for the canonical presentation layer.

The presentation layer renders numeric quantities for user-facing
research narratives: INR amounts in the house crore/lakh convention,
ratios as percentages, and internal identifiers as readable labels.
"""

from decimal import Decimal

from src.research.report.presentation import (
    format_change_pair,
    format_inr_amount,
    format_ratio_as_percent,
    humanize_identifier,
)


class TestFormatInrAmount:
    def test_crore_scaling(self):
        assert (
            format_inr_amount(Decimal("1205375000000.0"))
            == "Rs 1,20,537.5 crore"
        )

    def test_crore_rounding_is_deterministic(self):
        assert (
            format_inr_amount(Decimal("495446900000"))
            == "Rs 49,544.69 crore"
        )

    def test_lakh_scaling(self):
        assert format_inr_amount(Decimal("2500000")) == "Rs 25 lakh"

    def test_plain_rupees_below_lakh(self):
        assert format_inr_amount(45000) == "Rs 45,000"

    def test_negative_amount(self):
        assert (
            format_inr_amount(Decimal("-194533400000"))
            == "Rs -19,453.34 crore"
        )

    def test_invalid_input_returns_empty(self):
        assert format_inr_amount(None) == ""
        assert format_inr_amount("not-a-number") == ""

    def test_repeated_calls_are_identical(self):
        first = format_inr_amount(Decimal("1604968500000.0"))
        second = format_inr_amount(Decimal("1604968500000.0"))
        assert first == second


class TestFormatRatioAsPercent:
    def test_basic_ratio(self):
        assert (
            format_ratio_as_percent(Decimal("0.1455932624222843002837750398"))
            == "14.56%"
        )

    def test_signed_positive(self):
        assert (
            format_ratio_as_percent(Decimal("0.2932"), signed=True)
            == "+29.32%"
        )

    def test_signed_negative(self):
        assert format_ratio_as_percent(-0.05, signed=True) == "-5%"

    def test_zero(self):
        assert format_ratio_as_percent(0) == "0%"

    def test_invalid_input_returns_empty(self):
        assert format_ratio_as_percent(None) == ""
        assert format_ratio_as_percent("x") == ""


class TestFormatChangePair:
    def test_pair_sentence(self):
        text = format_change_pair(
            Decimal("0.1456"),
            Decimal("0.2932"),
            labels=("revenue", "receivables"),
        )
        assert text == (
            "revenue changed +14.56% but receivables changed +29.32%"
        )

    def test_invalid_input_returns_empty(self):
        assert (
            format_change_pair(None, 1, labels=("a", "b")) == ""
        )


class TestHumanizeIdentifier:
    def test_snake_case(self):
        assert humanize_identifier("revenue_growth") == "Revenue growth"

    def test_camel_case(self):
        assert (
            humanize_identifier("operatingCashFlow")
            == "Operating cash flow"
        )

    def test_numbered_suffix_preserved(self):
        assert (
            humanize_identifier("market_return_1d")
            == "Market return 1d"
        )

    def test_empty_input(self):
        assert humanize_identifier("") == ""
        assert humanize_identifier("   ") == ""

    def test_no_raw_underscores_in_output(self):
        label = humanize_identifier("operating_cash_flow_margin")
        assert "_" not in label
