from src.research.event_taxonomy import (
    EventCategory,
    EventImpactScope,
    EventUrgency,
    SourceType,
    is_valid_event_category,
)


def test_all_core_event_categories_exist() -> None:
    assert EventCategory.EARNINGS.value == "EARNINGS"
    assert EventCategory.GUIDANCE.value == "GUIDANCE"
    assert EventCategory.REGULATORY.value == "REGULATORY"
    assert EventCategory.GEOPOLITICAL.value == "GEOPOLITICAL"
    assert EventCategory.CYBER.value == "CYBER"


def test_event_scope_values_exist() -> None:
    assert EventImpactScope.ASSET.value == "ASSET"
    assert EventImpactScope.SECTOR.value == "SECTOR"
    assert EventImpactScope.MARKET.value == "MARKET"
    assert EventImpactScope.MACRO.value == "MACRO"


def test_event_urgency_values_exist() -> None:
    assert EventUrgency.IMMEDIATE.value == "IMMEDIATE"
    assert EventUrgency.NORMAL.value == "NORMAL"


def test_source_types_exist() -> None:
    assert SourceType.REGULATORY.value == "REGULATORY"
    assert SourceType.COMPANY.value == "COMPANY"
    assert SourceType.NEWSWIRE.value == "NEWSWIRE"
    assert SourceType.SOCIAL.value == "SOCIAL"


def test_valid_event_category() -> None:
    assert is_valid_event_category("earnings") is True
    assert is_valid_event_category("REGULATORY") is True


def test_invalid_event_category() -> None:
    assert is_valid_event_category("NOT_A_REAL_CATEGORY") is False
