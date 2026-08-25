"""
Deterministic screen definitions and execution.

A screen is a named, serializable set of filters over the
real-data-backed field registry (src.screener.fields). Screens are
descriptive research tools: they select companies whose recorded
data satisfies explicit conditions. They never rank, score, or
recommend.

Supported operators:
    eq / ne            equality on numbers and strings
    gt / gte / lt / lte numeric comparison
    between            numeric inclusive range (value + second_value)
    in                 membership (list of strings)
    contains           substring match on strings
    is_true / is_false boolean state
    has / missing      data-presence checks (no value required):
                       'has' matches companies with a recorded,
                       parseable value; 'missing' matches companies
                       where the field is absent or not usable

Group logic supports AND/OR inside a group; groups combine with a
top-level AND/OR where safe. Unknown fields or operators raise an
InvalidScreenError that names the offending entry — unsupported
fields stay clearly unavailable.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.screener.fields import (
    FIELD_REGISTRY,
)


class ScreenLogic(str, Enum):
    AND = "AND"
    OR = "OR"


_SUPPORTED_OPERATORS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "in",
    "contains",
    "is_true",
    "is_false",
    "has",
    "missing",
}


class InvalidScreenError(Exception):
    """A screen definition references unknown fields or operators."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ScreenFilter(BaseModel):
    """One filter over a registered field."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    value: Any = None
    second_value: Any = None


class ScreenFilterGroup(BaseModel):
    """A group of filters combined with AND/OR."""

    model_config = ConfigDict(extra="forbid")

    logic: ScreenLogic = ScreenLogic.AND
    filters: tuple[ScreenFilter, ...] = ()


class ScreenDefinition(BaseModel):
    """
    A complete, deterministic, serializable screen definition.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    combine: ScreenLogic = ScreenLogic.AND
    groups: tuple[ScreenFilterGroup, ...] = ()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Canonical serialization (stable key order via sort_keys)."""

        return {
            "name": self.name,
            "description": self.description,
            "combine": self.combine.value,
            "groups": [
                {
                    "logic": group.logic.value,
                    "filters": [
                        {
                            "field": f.field,
                            "operator": f.operator,
                            "value": _json_safe(f.value),
                            "second_value": _json_safe(f.second_value),
                        }
                        for f in group.filters
                    ],
                }
                for group in self.groups
            ],
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def definition_hash(self) -> str:
        """Stable content hash for reproducible screen identity."""

        return hashlib.sha256(
            self.canonical_json().encode("utf-8")
        ).hexdigest()[:16]

    @classmethod
    def from_dict(cls, payload: dict) -> "ScreenDefinition":
        """
        Deserialize with strict validation against the real field
        registry. Raises InvalidScreenError for anything unknown.
        """

        if not isinstance(payload, dict):
            raise InvalidScreenError(
                "screen definition must be an object",
            )

        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InvalidScreenError(
                "screen definition requires a non-empty name",
            )

        description = payload.get("description", "")
        if not isinstance(description, str):
            raise InvalidScreenError(
                "screen description must be a string",
            )

        combine_raw = payload.get("combine", "AND")
        try:
            combine = ScreenLogic(str(combine_raw).upper())
        except ValueError:
            raise InvalidScreenError(
                "screen combine must be AND or OR",
                details={"combine": combine_raw},
            ) from None

        raw_groups = payload.get("groups", [])
        if not isinstance(raw_groups, list):
            raise InvalidScreenError(
                "screen groups must be a list",
            )

        groups: list[ScreenFilterGroup] = []

        for group_index, raw_group in enumerate(raw_groups):
            if not isinstance(raw_group, dict):
                raise InvalidScreenError(
                    f"screen group {group_index} must be an object",
                )

            logic_raw = raw_group.get("logic", "AND")
            try:
                logic = ScreenLogic(str(logic_raw).upper())
            except ValueError:
                raise InvalidScreenError(
                    f"screen group {group_index} logic must be AND or OR",
                    details={"logic": logic_raw},
                ) from None

            raw_filters = raw_group.get("filters", [])
            if not isinstance(raw_filters, list):
                raise InvalidScreenError(
                    f"screen group {group_index} filters must be a list",
                )

            filters: list[ScreenFilter] = []
            for filter_index, raw_filter in enumerate(raw_filters):
                filters.append(
                    _validate_filter(
                        raw_filter,
                        location=f"group {group_index} filter {filter_index}",
                    )
                )

            groups.append(
                ScreenFilterGroup(logic=logic, filters=tuple(filters))
            )

        return cls(
            name=name.strip(),
            description=description,
            combine=combine,
            groups=tuple(groups),
        )


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _coerce_number(raw: Any, location: str) -> Decimal:
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        raise InvalidScreenError(
            f"{location}: value must be a number",
            details={"value": str(raw)},
        ) from None


def _validate_filter(raw_filter: Any, *, location: str) -> ScreenFilter:
    if not isinstance(raw_filter, dict):
        raise InvalidScreenError(
            f"{location} must be an object",
        )

    unknown_keys = set(raw_filter) - {
        "field",
        "operator",
        "value",
        "second_value",
    }
    if unknown_keys:
        raise InvalidScreenError(
            f"{location} has unsupported keys: "
            f"{', '.join(sorted(unknown_keys))}",
        )

    field_name = raw_filter.get("field")
    if not isinstance(field_name, str) or not field_name.strip():
        raise InvalidScreenError(
            f"{location}: field is required",
        )

    field_name = field_name.strip()

    definition = FIELD_REGISTRY.get(field_name)
    if definition is None:
        raise InvalidScreenError(
            f"{location}: unknown screener field '{field_name}'",
            details={
                "field": field_name,
                "known_fields": sorted(FIELD_REGISTRY),
            },
        )

    if not definition.available:
        raise InvalidScreenError(
            f"{location}: field '{field_name}' is not available yet",
            details={
                "field": field_name,
                "reason": definition.availability_note,
            },
        )

    operator = raw_filter.get("operator")
    if not isinstance(operator, str) or operator.strip() not in _SUPPORTED_OPERATORS:
        raise InvalidScreenError(
            f"{location}: unsupported operator '{operator}'",
            details={
                "operator": str(operator),
                "supported": sorted(_SUPPORTED_OPERATORS),
            },
        )

    operator = operator.strip()
    value = raw_filter.get("value")
    second_value = raw_filter.get("second_value")

    if definition.value_type == "number" and operator not in {
        "is_true",
        "is_false",
        "in",
        "contains",
        "has",
        "missing",
    }:
        value = _coerce_number(value, location)
        if operator == "between":
            second_value = _coerce_number(second_value, location)

    if operator in {"has", "missing"} and value is not None:
        raise InvalidScreenError(
            f"{location}: '{operator}' takes no value",
        )

    if operator == "in":
        if not isinstance(value, list) or not all(
            isinstance(entry, str) for entry in value
        ):
            raise InvalidScreenError(
                f"{location}: 'in' requires a list of strings",
            )
        value = [entry for entry in value]

    if operator == "contains":
        if not isinstance(value, str):
            raise InvalidScreenError(
                f"{location}: 'contains' requires a string value",
            )

    if operator == "between" and second_value is None:
        raise InvalidScreenError(
            f"{location}: 'between' requires second_value",
        )

    return ScreenFilter(
        field=field_name,
        operator=operator,
        value=value,
        second_value=second_value,
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def evaluate_filter(filter_spec: ScreenFilter, values: dict[str, object]) -> bool:
    """Evaluate one filter against extracted field values."""

    actual = values.get(filter_spec.field)
    operator = filter_spec.operator

    if operator == "has":
        if actual is None:
            return False
        definition = FIELD_REGISTRY.get(filter_spec.field)
        if definition is not None and definition.value_type == "number":
            return _as_decimal(actual) is not None
        return True

    if operator == "missing":
        if actual is None:
            return True
        definition = FIELD_REGISTRY.get(filter_spec.field)
        if definition is not None and definition.value_type == "number":
            return _as_decimal(actual) is None
        return False

    if operator == "is_true":
        return actual is True

    if operator == "is_false":
        return actual is False or actual is None

    if actual is None:
        # Missing data never satisfies a positive condition.
        return False

    if operator == "eq":
        if isinstance(actual, str):
            return actual.strip().lower() == str(filter_spec.value).strip().lower()
        expected = _as_decimal(filter_spec.value)
        actual_number = _as_decimal(actual)
        return (
            expected is not None
            and actual_number is not None
            and actual_number == expected
        )

    if operator == "ne":
        if isinstance(actual, str):
            return actual.strip().lower() != str(filter_spec.value).strip().lower()
        expected = _as_decimal(filter_spec.value)
        actual_number = _as_decimal(actual)
        return (
            expected is None
            or actual_number is None
            or actual_number != expected
        )

    if operator == "in":
        candidates = [str(entry).strip().lower() for entry in filter_spec.value]
        return str(actual).strip().lower() in candidates

    if operator == "contains":
        return str(filter_spec.value).strip().lower() in str(actual).lower()

    # Numeric comparisons below.
    actual_number = _as_decimal(actual)
    threshold = _as_decimal(filter_spec.value)

    if actual_number is None or threshold is None:
        return False

    if operator == "gt":
        return actual_number > threshold
    if operator == "gte":
        return actual_number >= threshold
    if operator == "lt":
        return actual_number < threshold
    if operator == "lte":
        return actual_number <= threshold
    if operator == "between":
        upper = _as_decimal(filter_spec.second_value)
        if upper is None:
            return False
        low, high = sorted((threshold, upper))
        return low <= actual_number <= high

    return False


def evaluate_group(group: ScreenFilterGroup, values: dict[str, object]) -> bool:
    results = [evaluate_filter(f, values) for f in group.filters]

    if not results:
        return True

    if group.logic == ScreenLogic.OR:
        return any(results)

    return all(results)


def execute_screen(
    definition: ScreenDefinition,
    field_rows: dict[str, dict[str, object]],
) -> "ScreenExecutionResult":
    """
    Execute one screen definition over pre-extracted per-symbol field
    rows. Row iteration follows the insertion order of field_rows so
    output ordering is fully determined by the caller's universe order.
    """

    matched: list[tuple[str, dict[str, object]]] = []

    for symbol, values in field_rows.items():
        group_results = [
            evaluate_group(group, values) for group in definition.groups
        ]

        if not group_results:
            passed = True
        elif definition.combine == ScreenLogic.OR:
            passed = any(group_results)
        else:
            passed = all(group_results)

        if passed:
            matched.append((symbol, values))

    return ScreenExecutionResult(
        definition_hash=definition.definition_hash(),
        matched_symbols=tuple(symbol for symbol, _ in matched),
        matched_field_values={
            symbol: values for symbol, values in matched
        },
    )


class ScreenExecutionResult:
    """Result of executing one screen over the universe."""

    __slots__ = (
        "definition_hash",
        "matched_symbols",
        "matched_field_values",
    )

    def __init__(
        self,
        *,
        definition_hash: str,
        matched_symbols: tuple[str, ...],
        matched_field_values: dict[str, dict[str, object]],
    ) -> None:
        self.definition_hash = definition_hash
        self.matched_symbols = matched_symbols
        self.matched_field_values = matched_field_values


__all__ = [
    "InvalidScreenError",
    "ScreenDefinition",
    "ScreenExecutionResult",
    "ScreenFilter",
    "ScreenFilterGroup",
    "ScreenLogic",
    "evaluate_filter",
    "evaluate_group",
    "execute_screen",
]
