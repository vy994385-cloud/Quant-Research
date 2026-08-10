from __future__ import annotations

from enum import Enum


class EventCategory(str, Enum):
    """
    Canonical categories for information that can affect an asset.

    These categories describe what happened, not whether the event
    is bullish or bearish.
    """

    NEWS = "NEWS"
    EARNINGS = "EARNINGS"
    GUIDANCE = "GUIDANCE"
    REGULATORY = "REGULATORY"
    LEGAL = "LEGAL"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    MANAGEMENT = "MANAGEMENT"
    ANALYST = "ANALYST"
    MACRO = "MACRO"
    CENTRAL_BANK = "CENTRAL_BANK"
    ECONOMIC_DATA = "ECONOMIC_DATA"
    SECTOR = "SECTOR"
    COMMODITY = "COMMODITY"
    GEOPOLITICAL = "GEOPOLITICAL"
    MARKET = "MARKET"
    TECHNOLOGY = "TECHNOLOGY"
    CYBER = "CYBER"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    PRODUCT = "PRODUCT"
    CAPITAL_ALLOCATION = "CAPITAL_ALLOCATION"


class EventImpactScope(str, Enum):
    """
    Describes the potential scope of an event.
    """

    ASSET = "ASSET"
    SECTOR = "SECTOR"
    MARKET = "MARKET"
    MACRO = "MACRO"
    GLOBAL = "GLOBAL"


class EventUrgency(str, Enum):
    """
    Describes how quickly an event may matter to the market.

    This is not a prediction of price direction.
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"


class SourceType(str, Enum):
    """
    Classification of the original information source.
    """

    PRIMARY = "PRIMARY"
    REGULATORY = "REGULATORY"
    COMPANY = "COMPANY"
    NEWSWIRE = "NEWSWIRE"
    FINANCIAL_MEDIA = "FINANCIAL_MEDIA"
    GOVERNMENT = "GOVERNMENT"
    CENTRAL_BANK = "CENTRAL_BANK"
    EXCHANGE = "EXCHANGE"
    ANALYST = "ANALYST"
    AGGREGATOR = "AGGREGATOR"
    SOCIAL = "SOCIAL"
    UNKNOWN = "UNKNOWN"


EVENT_CATEGORY_DESCRIPTIONS: dict[EventCategory, str] = {
    EventCategory.NEWS: "General company or market news.",
    EventCategory.EARNINGS: "Reported financial results or earnings-related information.",
    EventCategory.GUIDANCE: "Company guidance, outlook, or forecast changes.",
    EventCategory.REGULATORY: "Regulatory approvals, investigations, rulings, or actions.",
    EventCategory.LEGAL: "Lawsuits, litigation, settlements, or legal developments.",
    EventCategory.CORPORATE_ACTION: "Mergers, acquisitions, splits, dividends, and similar actions.",
    EventCategory.MANAGEMENT: "Executive or board changes.",
    EventCategory.ANALYST: "Analyst ratings, estimates, or target-price changes.",
    EventCategory.MACRO: "Broad economic or financial conditions.",
    EventCategory.CENTRAL_BANK: "Central-bank decisions, statements, or policy signals.",
    EventCategory.ECONOMIC_DATA: "Inflation, employment, GDP, rates, and other economic releases.",
    EventCategory.SECTOR: "Industry-wide developments affecting related companies.",
    EventCategory.COMMODITY: "Commodity-price or commodity-supply developments.",
    EventCategory.GEOPOLITICAL: "Wars, sanctions, elections, diplomatic or geopolitical developments.",
    EventCategory.MARKET: "Broad market structure, liquidity, volatility, or trading events.",
    EventCategory.TECHNOLOGY: "Technology developments materially affecting a company or sector.",
    EventCategory.CYBER: "Cybersecurity incidents, breaches, or attacks.",
    EventCategory.SUPPLY_CHAIN: "Supply, logistics, manufacturing, or distribution disruptions.",
    EventCategory.PRODUCT: "Product launches, recalls, approvals, or material product developments.",
    EventCategory.CAPITAL_ALLOCATION: "Buybacks, financing, debt issuance, or other capital-allocation decisions.",
}


def is_valid_event_category(value: str) -> bool:
    """
    Return whether value is a supported canonical event category.
    """

    try:
        EventCategory(value.upper())
    except ValueError:
        return False

    return True