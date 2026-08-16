from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.research.company_intel import item_checksum
from src.research.company_intel.models import (
    CorporateIntelItem,
    SourceRef,
)
from src.research.company_intel.semantics import (
    EvidenceStance,
    IntelDirection,
    IntelKind,
    SemanticCategory,
    VerificationStatus,
)

AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def ts(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        tzinfo=timezone.utc,
    )


def make_item(
    *,
    item_id: str,
    symbol: str = "TCS",
    kind: IntelKind = IntelKind.OTHER,
    semantic_category: SemanticCategory | None = None,
    verification_status: VerificationStatus = (
        VerificationStatus.REPORTED
    ),
    topic: str | None = None,
    title: str | None = None,
    description: str = "",
    stance: EvidenceStance = EvidenceStance.NEUTRAL,
    direction: IntelDirection = IntelDirection.UNKNOWN,
    available_at: datetime = AS_OF,
    published_at: datetime | None = None,
    source_name: str = "test-source",
    source_type: str = "TEST",
    source_url: str | None = None,
    reliability_tier: int = 2,
    related_entities: tuple[str, ...] = (),
    conflicts_with: tuple[str, ...] = (),
    supports: tuple[str, ...] = (),
    provenance_id: str | None = None,
) -> CorporateIntelItem:
    kwargs: dict = {
        "item_id": item_id,
        "symbol": symbol,
        "kind": kind,
        "verification_status": verification_status,
        "topic": topic,
        "title": title or f"Title for {item_id}",
        "description": description,
        "stance": stance,
        "direction": direction,
        "available_at": available_at,
        "published_at": published_at or available_at,
        "source": SourceRef(
            source_name=source_name,
            source_type=source_type,
            source_url=source_url,
            reliability_tier=reliability_tier,
            provenance_id=provenance_id,
        ),
        "related_entities": related_entities,
        "conflicts_with": conflicts_with,
        "supports": supports,
        "provenance_id": provenance_id,
    }

    if semantic_category is not None:
        kwargs["semantic_category"] = semantic_category

    item = CorporateIntelItem(**kwargs)

    return item.model_copy(
        update={"checksum": item_checksum(item)}
    )


@pytest.fixture
def as_of() -> datetime:
    return AS_OF
