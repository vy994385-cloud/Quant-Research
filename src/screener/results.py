"""
Structured screen-execution output.

Turns a deterministic ScreenExecutionResult into an explicit,
evidence-aware output contract:

- echoes the exact filters that were run;
- echoes the requested output columns;
- one row per matched company with per-column availability
  (a null value is always reported as unavailable, never omitted);
- company name and sector where recorded metadata provides them;
- row-level research context is expressed through registered
  coverage / freshness / PIT / gap / evidence columns — the same
  real-data-backed vocabulary as filtering;
- no score, ranking, winner, or recommendation fields exist.

Saved-screen persistence does not exist in the backend yet; this is
reported as an explicit capability note instead of being faked.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.screener.engine import (
    InvalidScreenError,
    ScreenDefinition,
    ScreenExecutionResult,
)
from src.screener.fields import (
    AVAILABLE_FIELDS,
    FIELD_REGISTRY,
)


class ScreenRowColumn(BaseModel):
    """One requested column for one matched company."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    label: str = Field(min_length=1)
    category: str = Field(min_length=1)
    unit: str | None = None
    value: str | None = None
    available: bool


class ScreenResultRow(BaseModel):
    """One matched company with its requested columns."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    sector: str | None = None
    columns: tuple[ScreenRowColumn, ...] = ()


class ScreenExecutionOutput(BaseModel):
    """Canonical, self-describing screen result."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    definition_hash: str = Field(min_length=1)

    # Exact filters executed (canonical serialization of the
    # definition) so results are reproducible.
    selected_filters: dict

    # Columns echoed back to the caller.
    selected_columns: tuple[str, ...] = ()

    rows: tuple[ScreenResultRow, ...] = ()
    matched_count: int = Field(ge=0)
    universe_size: int = Field(ge=0)

    notes: tuple[str, ...] = ()


def _column_for(field_name: str, value) -> ScreenRowColumn:
    definition = FIELD_REGISTRY[field_name]

    if value is None:
        return ScreenRowColumn(
            field=field_name,
            label=definition.label,
            category=definition.category.value,
            unit=definition.unit,
            value=None,
            available=False,
        )

    serialized = (
        "true"
        if value is True
        else "false"
        if value is False
        else str(value)
    )

    return ScreenRowColumn(
        field=field_name,
        label=definition.label,
        category=definition.category.value,
        unit=definition.unit,
        value=serialized,
        available=True,
    )


def _resolve_columns(requested_columns) -> tuple[str, ...]:
    if not requested_columns:
        return tuple(sorted(AVAILABLE_FIELDS))

    resolved: list[str] = []
    for raw in requested_columns:
        name = str(raw).strip()
        definition = FIELD_REGISTRY.get(name)
        if definition is None or not definition.available:
            raise InvalidScreenError(
                f"unsupported output column '{name}'",
                details={
                    "field": name,
                    "known_fields": sorted(AVAILABLE_FIELDS),
                },
            )
        resolved.append(name)

    # Deterministic de-duplication preserving first-request order.
    seen: dict[str, None] = {}
    for name in resolved:
        seen.setdefault(name, None)
    return tuple(seen)


def build_screen_output(
    definition: ScreenDefinition,
    execution: ScreenExecutionResult,
    field_rows: dict[str, dict[str, object]],
    *,
    requested_columns=None,
    company_names: dict[str, str] | None = None,
    sectors: dict[str, str] | None = None,
) -> ScreenExecutionOutput:
    """
    Build the canonical screen output.

    field_rows is the full pre-execution universe mapping (symbol ->
    extracted values); it supplies values for every row and the
    universe size.
    """

    columns = _resolve_columns(requested_columns)

    # Canonical row order: symbol ascending, independent of the
    # caller's universe iteration order.
    matched = sorted(execution.matched_symbols)

    rows: list[ScreenResultRow] = []
    for symbol in matched:
        values = execution.matched_field_values.get(symbol, {})
        rows.append(
            ScreenResultRow(
                symbol=symbol,
                company_name=(
                    company_names.get(symbol)
                    if company_names
                    else None
                ),
                sector=sectors.get(symbol) if sectors else None,
                columns=tuple(
                    _column_for(name, values.get(name))
                    for name in columns
                ),
            )
        )

    notes: list[str] = [
        "Results are descriptive only: matching reflects the "
        "recorded data satisfying the explicit filters. No score, "
        "ranking, or recommendation is expressed."
    ]
    notes.append(
        "Saved-screen storage is not supported by the backend yet; "
        "screen definitions are content-hashed but not persisted."
    )
    unavailable_count = len(FIELD_REGISTRY) - len(AVAILABLE_FIELDS)
    if unavailable_count:
        notes.append(
            f"{unavailable_count} registered field(s) have no real "
            "data source yet and cannot be filtered on."
        )

    return ScreenExecutionOutput(
        name=definition.name,
        description=definition.description,
        definition_hash=execution.definition_hash,
        selected_filters=definition.to_dict(),
        selected_columns=columns,
        rows=tuple(rows),
        matched_count=len(rows),
        universe_size=len(field_rows),
        notes=tuple(notes),
    )


__all__ = [
    "ScreenExecutionOutput",
    "ScreenResultRow",
    "ScreenRowColumn",
    "build_screen_output",
]
