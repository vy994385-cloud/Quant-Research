"""
Backend screener capability.

Provides a real-data-backed field registry, deterministic screen
definitions, serialization, validation, and re-execution.

Every exposed field is computed from existing recorded research
data. Fields without a real data source are explicitly marked
unavailable and are never exposed as executable filters.

This module produces descriptive research output only. It does not
rank companies, score them, or generate recommendations.
"""

from src.screener.engine import (
    InvalidScreenError,
    ScreenDefinition,
    ScreenExecutionResult,
    ScreenFilter,
    ScreenFilterGroup,
    execute_screen,
)
from src.screener.fields import (
    FIELD_REGISTRY,
    ScreenerFieldCategory,
    FieldDefinition,
    extract_company_fields,
    field_values_contract_dict,
)

__all__ = [
    "FIELD_REGISTRY",
    "FieldDefinition",
    "InvalidScreenError",
    "ScreenDefinition",
    "ScreenExecutionResult",
    "ScreenFilter",
    "ScreenFilterGroup",
    "ScreenerFieldCategory",
    "execute_screen",
    "extract_company_fields",
    "field_values_contract_dict",
]
