"""
Canonical presentation layer for user-facing research output.

Single source of truth for rendering numeric quantities inside
readable research narratives:

- INR amounts use the house "Rs … crore" convention (with lakh /
  plain-rupee fallbacks for smaller magnitudes) and Indian digit
  grouping;
- ratios that represent fractions of one are rendered as signed or
  unsigned percentages with deterministic rounding;
- internal identifiers (feature IDs) are converted to readable labels
  before they reach a narrative string.

Formatters here never fabricate data: they only re-render values that
already exist. Exact raw values remain available in structured fields
and derivation metadata; this layer is for presentation only.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CRORE = Decimal("10000000")
_LAKH = Decimal("100000")

_TWO_PLACES = Decimal("0.01")


def _to_decimal(value) -> Decimal | None:
    """Convert a numeric input to Decimal; return None if unusable."""
    if isinstance(value, Decimal):
        try:
            if value.is_nan() or value.is_infinite():
                return None
        except InvalidOperation:
            return None
        return value

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        try:
            candidate = Decimal(str(value))
        except InvalidOperation:
            return None
        if candidate.is_nan() or candidate.is_infinite():
            return None
        return candidate

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            candidate = Decimal(text)
        except InvalidOperation:
            return None
        if candidate.is_nan() or candidate.is_infinite():
            return None
        return candidate

    return None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _format_number_indian(value: Decimal) -> str:
    """
    Format a decimal amount with Indian digit grouping.

    The integer part is grouped 2-2-2 after the first three digits
    (1,20,53,750); up to two fractional digits are kept with trailing
    zeros removed.
    """

    sign = "-" if value < 0 else ""
    quantized = _quantize(abs(value))

    integer_part = int(quantized)
    fraction = quantized - integer_part

    digits = str(integer_part)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        grouped = ",".join([*groups, tail])
    else:
        grouped = digits

    if fraction > 0:
        fraction_text = f"{fraction:.2f}"[1:].rstrip("0")
        return f"{sign}{grouped}{fraction_text}"

    return f"{sign}{grouped}"


def format_inr_amount(value) -> str:
    """
    Render a rupee-denominated amount using the house convention.

    Amounts of one crore or more are shown as "Rs …crore", amounts of
    one lakh or more as "Rs …lakh", smaller amounts as plain rupees.
    Returns "" when the input cannot be interpreted as a number.
    """

    amount = _to_decimal(value)
    if amount is None:
        return ""

    if abs(amount) >= _CRORE:
        crores = amount / _CRORE
        return f"Rs {_format_number_indian(crores)} crore"

    if abs(amount) >= _LAKH:
        lakhs = amount / _LAKH
        return f"Rs {_format_number_indian(lakhs)} lakh"

    return f"Rs {_format_number_indian(amount)}"


def _ratio_to_percent_text(ratio: Decimal, *, signed: bool) -> str:
    percent = ratio * Decimal("100")
    rounded = _quantize(percent)

    text = _format_number_indian(rounded)
    if signed and not text.startswith("-"):
        text = f"+{text}"

    return f"{text}%"


def format_ratio_as_percent(value, *, signed: bool = False) -> str:
    """
    Render a fraction-of-one ratio as a percentage.

    0.1456 -> "14.56%"; signed=True renders "+14.56%" / "-3.2%".
    Returns "" when the input cannot be interpreted as a number.
    """

    ratio = _to_decimal(value)
    if ratio is None:
        return ""

    return _ratio_to_percent_text(ratio, signed=signed)


def format_change_pair(first, second, *, labels: tuple[str, str]) -> str:
    """
    Render two ratios as a signed percentage comparison sentence part.

    Example output: "revenue changed +14.56% but receivables changed
    +29.32%". Returns "" when either input is unusable.
    """

    first_ratio = _to_decimal(first)
    second_ratio = _to_decimal(second)
    if first_ratio is None or second_ratio is None:
        return ""

    first_text = _ratio_to_percent_text(first_ratio, signed=True)
    second_text = _ratio_to_percent_text(second_ratio, signed=True)

    return (
        f"{labels[0]} changed {first_text} but "
        f"{labels[1]} changed {second_text}"
    )


_WORD_SPLIT = re.compile(r"[\s_-]+|(?<=[a-z0-9])(?=[A-Z])")


def humanize_identifier(identifier: str) -> str:
    """
    Convert an internal identifier into a readable label.

    "revenue_growth" -> "Revenue growth";
    "operatingCashFlow" -> "Operating cash flow".
    """

    if not identifier or not identifier.strip():
        return ""

    words = [word for word in _WORD_SPLIT.split(identifier.strip()) if word]
    if not words:
        return ""

    lowered = [word.lower() for word in words]
    return lowered[0].capitalize() + " " + " ".join(lowered[1:])


__all__ = [
    "format_change_pair",
    "format_inr_amount",
    "format_ratio_as_percent",
    "humanize_identifier",
]
