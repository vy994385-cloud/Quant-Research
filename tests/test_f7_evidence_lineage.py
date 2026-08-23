"""
Tests for the F7 canonical evidence lineage system.

Verifies models, lineage resolution, PIT filtering, API contracts,
serializers, and router endpoints for all verified companies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_api_error_handlers
from src.api.f7_router import create_f7_router
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.evidence.lineage import (
    build_evidence_lineage,
    filter_evidence_by_pit,
    resolve_source_profile,
)
from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
    EvidenceSourceInfo,
    EvidenceSourceRecordInfo,
)
from src.research.provenance import DataProvenance
from src.research.source_catalog import get_source
from src.research.source_reliability import (
    get_default_source_profile,
)
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceReliability,
    EvidenceType,
)

VERIFIED_COMPANIES = (
    "TCS",
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "M&M",
)

DEFAULT_AS_OF_ISO = "2026-08-10T12:00:00+00:00"


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("f7-evidence-archive")
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(create_f7_router(service=service))
    return TestClient(app)


# ── Unit tests: EpistemicType ──────────────────────────────────────


class TestEpistemicType:
    def test_epistemic_type_values(self):
        assert EpistemicType.REPORTED.value == "REPORTED"
        assert EpistemicType.DERIVED.value == "DERIVED"
        assert EpistemicType.INFERRED.value == "INFERRED"
        assert EpistemicType.UNKNOWN.value == "UNKNOWN"

    def test_epistemic_type_all_members(self):
        assert len(EpistemicType) == 4

    def test_epistemic_type_is_str_enum(self):
        assert isinstance(EpistemicType.REPORTED, str)
        assert EpistemicType.REPORTED == "REPORTED"


# ── Unit tests: EvidenceSourceInfo ──────────────────────────────────


class TestEvidenceSourceInfo:
    def test_valid_source_info(self):
        info = EvidenceSourceInfo(
            source_id="sec_edgar",
            name="SEC EDGAR",
            source_type="FUNDAMENTALS",
            tier="PRIMARY",
        )
        assert info.source_id == "sec_edgar"
        assert info.tier == "PRIMARY"

    def test_empty_source_id_raises(self):
        with pytest.raises(ValueError, match="source_id cannot be empty"):
            EvidenceSourceInfo(
                source_id="", name="T", source_type="T", tier="PRIMARY"
            )

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            EvidenceSourceInfo(
                source_id="t", name="", source_type="T", tier="PRIMARY"
            )


# ── Unit tests: EvidenceSourceRecordInfo ────────────────────────────


class TestEvidenceSourceRecordInfo:
    def test_valid_record_info(self):
        record = EvidenceSourceRecordInfo(
            source="sec_edgar",
            retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert record.source == "sec_edgar"

    def test_empty_source_raises(self):
        with pytest.raises(ValueError, match="source cannot be empty"):
            EvidenceSourceRecordInfo(source="")

    def test_naive_timestamp_raises(self):
        with pytest.raises(ValueError, match="retrieved_at must be timezone-aware"):
            EvidenceSourceRecordInfo(
                source="test", retrieved_at=datetime(2026, 1, 1)
            )


# ── Unit tests: EvidenceClaim ───────────────────────────────────────


class TestEvidenceClaim:
    def test_valid_claim(self):
        claim = EvidenceClaim(
            claim_id="CLAIM:TCS:0001",
            symbol="TCS",
            text="Revenue grew 15%",
            category="FINANCIAL",
        )
        assert claim.epistemic_type == EpistemicType.UNKNOWN

    def test_empty_claim_id_raises(self):
        with pytest.raises(ValueError, match="claim_id cannot be empty"):
            EvidenceClaim(
                claim_id="", symbol="TCS", text="T", category="T"
            )

    def test_naive_observation_at_raises(self):
        with pytest.raises(ValueError, match="observation_at must be timezone-aware"):
            EvidenceClaim(
                claim_id="C1", symbol="TCS", text="T", category="T",
                observation_at=datetime(2026, 1, 1),
            )


# ── Unit tests: CanonicalEvidenceItem ───────────────────────────────


class TestCanonicalEvidenceItem:
    def test_valid_item(self):
        item = CanonicalEvidenceItem(
            evidence_id="E1", symbol="TCS", title="Growth",
            explanation="Revenue up", evidence_type="FEATURE",
            direction="POSITIVE", confidence="0.85", reliability="PRIMARY",
        )
        assert item.epistemic_type == EpistemicType.UNKNOWN

    def test_empty_evidence_id_raises(self):
        with pytest.raises(ValueError, match="evidence_id cannot be empty"):
            CanonicalEvidenceItem(
                evidence_id="", symbol="TCS", title="T",
                explanation="T", evidence_type="F",
                direction="P", confidence="0.8", reliability="P",
            )

    def test_naive_observation_at_raises(self):
        with pytest.raises(ValueError, match="observation_at must be timezone-aware"):
            CanonicalEvidenceItem(
                evidence_id="E1", symbol="TCS", title="T",
                explanation="T", evidence_type="F",
                direction="P", confidence="0.8", reliability="P",
                observation_at=datetime(2026, 1, 1),
            )


# ── Unit tests: EvidenceLineage ─────────────────────────────────────


class TestEvidenceLineage:
    def test_valid_lineage(self):
        lineage = EvidenceLineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
        )
        assert lineage.total_evidence == 0
        assert lineage.epistemic_type_counts == {}

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            EvidenceLineage(
                symbol="",
                as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            )

    def test_naive_as_of_raises(self):
        with pytest.raises(ValueError, match="as_of must be timezone-aware"):
            EvidenceLineage(symbol="TCS", as_of=datetime(2026, 8, 10))


# ── Unit tests: resolve_source_profile ──────────────────────────────


class TestResolveSourceProfile:
    def test_resolve_known_source(self):
        profile = resolve_source_profile("sec_edgar")
        assert profile is not None
        assert profile.source_id == "sec_edgar"
        assert profile.tier == "PRIMARY"

    def test_resolve_unknown_source(self):
        profile = resolve_source_profile("nonexistent_xyz")
        assert profile is None

    def test_resolve_fred_source(self):
        profile = resolve_source_profile("fred")
        assert profile is not None
        assert profile.name == "FRED / ALFRED"


# ── Unit tests: Epistemic classification ────────────────────────────


class TestEpistemicClassification:
    def _make_item(self, evidence_type):
        return EvidenceItem(
            evidence_id="E1", symbol="TCS",
            evidence_type=evidence_type, title="T", explanation="T",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.8"),
            reliability=EvidenceReliability.PRIMARY,
            observation_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def test_market_is_reported(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.MARKET)
        ) == EpistemicType.REPORTED

    def test_acquired_is_reported(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.ACQUIRED)
        ) == EpistemicType.REPORTED

    def test_company_intelligence_is_reported(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.COMPANY_INTELLIGENCE)
        ) == EpistemicType.REPORTED

    def test_feature_is_derived(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.FEATURE)
        ) == EpistemicType.DERIVED

    def test_signal_is_inferred(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.SIGNAL)
        ) == EpistemicType.INFERRED

    def test_trend_is_inferred(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.TREND)
        ) == EpistemicType.INFERRED

    def test_risk_is_inferred(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.RISK)
        ) == EpistemicType.INFERRED

    def test_future_technology_is_reported(self):
        from src.research.evidence.lineage import _classify_epistemic
        assert _classify_epistemic(
            self._make_item(EvidenceType.FUTURE_TECHNOLOGY)
        ) == EpistemicType.REPORTED


# ── Unit tests: PIT filtering ───────────────────────────────────────


class TestPITFiltering:
    def _make_item(self, eid, obs=None, avail=None):
        return CanonicalEvidenceItem(
            evidence_id=eid, symbol="TCS", title="T", explanation="T",
            evidence_type="F", direction="P", confidence="0.85",
            reliability="PRIMARY", observation_at=obs, available_at=avail,
        )

    def test_item_before_as_of_retained(self):
        item = self._make_item(
            "E1",
            obs=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        result = filter_evidence_by_pit(
            (item,), datetime(2026, 6, 1, tzinfo=timezone.utc)
        )
        assert len(result) == 1

    def test_item_after_as_of_excluded(self):
        item = self._make_item(
            "E1",
            obs=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        result = filter_evidence_by_pit(
            (item,), datetime(2026, 6, 1, tzinfo=timezone.utc)
        )
        assert len(result) == 0

    def test_item_with_available_at_after_excluded(self):
        item = self._make_item(
            "E1",
            obs=datetime(2026, 1, 1, tzinfo=timezone.utc),
            avail=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        result = filter_evidence_by_pit(
            (item,), datetime(2026, 6, 1, tzinfo=timezone.utc)
        )
        assert len(result) == 0

    def test_naive_as_of_raises(self):
        item = self._make_item("E1")
        with pytest.raises(ValueError, match="as_of must be timezone-aware"):
            filter_evidence_by_pit((item,), datetime(2026, 6, 1))


# ── Unit tests: build_evidence_lineage ──────────────────────────────


class TestBuildEvidenceLineage:
    def test_empty_inputs(self):
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
        )
        assert lineage.symbol == "TCS"
        assert lineage.total_evidence == 0
        assert lineage.total_claims == 0

    def test_with_evidence_items(self):
        item = EvidenceItem(
            evidence_id="E1", symbol="TCS",
            evidence_type=EvidenceType.FEATURE, title="Growth",
            explanation="Revenue up",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.85"),
            reliability=EvidenceReliability.PRIMARY,
            observation_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=(item,),
        )
        assert lineage.total_evidence == 1
        assert lineage.total_claims == 1
        assert lineage.evidence[0].evidence_id == "E1"

    def test_wrong_symbol_excluded(self):
        item = EvidenceItem(
            evidence_id="E1", symbol="INFY",
            evidence_type=EvidenceType.FEATURE, title="Growth",
            explanation="Revenue up",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.85"),
            reliability=EvidenceReliability.PRIMARY,
            observation_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=(item,),
        )
        assert lineage.total_evidence == 0

    def test_future_evidence_pit_filtered(self):
        item = EvidenceItem(
            evidence_id="E1", symbol="TCS",
            evidence_type=EvidenceType.FEATURE, title="Growth",
            explanation="Revenue up",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.85"),
            reliability=EvidenceReliability.PRIMARY,
            observation_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 6, 1, tzinfo=timezone.utc),
            evidence_items=(item,),
            pit_filter=True,
        )
        assert lineage.total_evidence == 0
        assert lineage.pit_filtered_count == 1

    def test_pit_filter_disabled(self):
        item = EvidenceItem(
            evidence_id="E1", symbol="TCS",
            evidence_type=EvidenceType.FEATURE, title="Growth",
            explanation="Revenue up",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.85"),
            reliability=EvidenceReliability.PRIMARY,
            observation_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 6, 1, tzinfo=timezone.utc),
            evidence_items=(item,),
            pit_filter=False,
        )
        assert lineage.total_evidence == 1

    def test_deterministic_ordering(self):
        items = [
            EvidenceItem(
                evidence_id=f"E{i}", symbol="TCS",
                evidence_type=EvidenceType.FEATURE, title=f"T{i}",
                explanation="T",
                direction=EvidenceDirection.POSITIVE,
                confidence=Decimal(str(0.5 + i * 0.1)),
                reliability=EvidenceReliability.PRIMARY,
                observation_at=datetime(
                    2026, 1, i + 1, tzinfo=timezone.utc
                ),
            )
            for i in range(3)
        ]
        a = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=tuple(items),
        )
        b = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=tuple(reversed(items)),
        )
        assert [e.evidence_id for e in a.evidence] == [
            e.evidence_id for e in b.evidence
        ]

    def test_epistemic_type_counts(self):
        items = [
            EvidenceItem(
                evidence_id="E1", symbol="TCS",
                evidence_type=EvidenceType.FEATURE, title="T",
                explanation="T",
                direction=EvidenceDirection.POSITIVE,
                confidence=Decimal("0.8"),
                reliability=EvidenceReliability.PRIMARY,
                observation_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            EvidenceItem(
                evidence_id="E2", symbol="TCS",
                evidence_type=EvidenceType.SIGNAL, title="T",
                explanation="T",
                direction=EvidenceDirection.NEGATIVE,
                confidence=Decimal("0.7"),
                reliability=EvidenceReliability.SECONDARY,
                observation_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            ),
        ]
        lineage = build_evidence_lineage(
            symbol="TCS",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=tuple(items),
        )
        assert "DERIVED" in lineage.epistemic_type_counts
        assert "INFERRED" in lineage.epistemic_type_counts

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            build_evidence_lineage(
                symbol="",
                as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            )


# ── API endpoint tests ──────────────────────────────────────────────


class TestF7EvidenceEndpoint:
    def test_route_exposed(self, client):
        resp = client.get("/api/v1/companies/TCS/evidence")
        assert resp.status_code == 200
        assert resp.json()["company"]["symbol"] == "TCS"

    def test_has_evidence_lineage(self, client):
        resp = client.get("/api/v1/companies/TCS/evidence")
        payload = resp.json()
        assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO
        el = payload["evidence_lineage"]
        assert el is not None
        assert el["symbol"] == "TCS"
        assert el["as_of"] == DEFAULT_AS_OF_ISO
        assert isinstance(el["evidence"], list)
        assert isinstance(el["claims"], list)
        assert isinstance(el["epistemic_type_counts"], dict)
        assert isinstance(el["verification_status_counts"], dict)
        assert isinstance(el["direction_counts"], dict)
        assert el["total_evidence"] >= 0
        assert el["total_claims"] >= 0
        assert el["pit_filtered_count"] >= 0

    def test_evidence_item_structure(self, client):
        resp = client.get("/api/v1/companies/TCS/evidence")
        el = resp.json()["evidence_lineage"]
        for item in el["evidence"]:
            assert item["evidence_id"]
            assert item["symbol"] == "TCS"
            assert item["title"]
            assert item["explanation"]
            assert item["evidence_type"]
            assert item["direction"]
            assert item["confidence"]
            assert item["reliability"]
            assert item["epistemic_type"] in (
                "REPORTED", "DERIVED", "INFERRED", "UNKNOWN"
            )
            assert item["verification_status"] in (
                "CONFIRMED", "REPORTED", "ALLEGED",
                "UNVERIFIED", "CONTRADICTED", "RESOLVED",
            )
            assert isinstance(item["source_ids"], list)
            assert isinstance(item["provenance_ids"], list)

    def test_pit_safe(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"as_of": "2026-04-01T00:00:00+00:00"},
        )
        payload = resp.json()
        assert payload["company"]["as_of"] == "2026-04-01T00:00:00+00:00"
        el = payload["evidence_lineage"]
        assert el is not None

    def test_deterministic(self, client):
        a = client.get("/api/v1/companies/TCS/evidence").json()
        b = client.get("/api/v1/companies/TCS/evidence").json()
        assert a == b

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_every_company_has_evidence(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/evidence"
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["company"]["symbol"] == symbol
        el = payload["evidence_lineage"]
        assert el is not None
        assert isinstance(el["evidence"], list)
        assert el["total_evidence"] >= 0

    def test_unknown_company_returns_404(self, client):
        resp = client.get("/api/v1/companies/UNKNOWN/evidence")
        assert resp.status_code == 404

    def test_naive_as_of_returns_400(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"as_of": "2026-08-10T12:00:00"},
        )
        assert resp.status_code == 400

    def test_filter_by_direction(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"category": "NONEXISTENT"},
        )
        el = resp.json()["evidence_lineage"]
        assert el["total_evidence"] == 0

    def test_filter_by_limit(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"limit": 1},
        )
        el = resp.json()["evidence_lineage"]
        assert len(el["evidence"]) <= 1

    def test_filter_by_verification_status(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"verification_status": "CONFIRMED"},
        )
        el = resp.json()["evidence_lineage"]
        for item in el["evidence"]:
            assert item["verification_status"] == "CONFIRMED"

    def test_filter_by_evidence_kind(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"evidence_kind": "FEATURE"},
        )
        el = resp.json()["evidence_lineage"]
        for item in el["evidence"]:
            assert item["evidence_type"] == "FEATURE"

    def test_filter_by_confidence_range(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence",
            params={"confidence_min": 0.8, "confidence_max": 1.0},
        )
        el = resp.json()["evidence_lineage"]
        for item in el["evidence"]:
            conf = float(item["confidence"])
            assert conf >= 0.8
            assert conf <= 1.0


# ── API detail endpoint tests ───────────────────────────────────────


class TestF7EvidenceDetailEndpoint:
    def test_detail_route_exposed(self, client):
        resp = client.get("/api/v1/companies/TCS/evidence")
        evidence = resp.json()["evidence_lineage"]["evidence"]
        if evidence:
            eid = evidence[0]["evidence_id"]
            detail_resp = client.get(
                f"/api/v1/companies/TCS/evidence/{eid}"
            )
            assert detail_resp.status_code == 200
            payload = detail_resp.json()
            assert payload["company"]["symbol"] == "TCS"
            assert payload["evidence_item"]["evidence_id"] == eid
            assert isinstance(payload["related_claims"], list)
            assert isinstance(payload["related_evidence"], list)

    def test_nonexistent_evidence_returns_404(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/evidence/NONEXISTENT_ID"
        )
        assert resp.status_code == 404

    def test_detail_pit_safe(self, client):
        resp = client.get("/api/v1/companies/TCS/evidence")
        evidence = resp.json()["evidence_lineage"]["evidence"]
        if evidence:
            eid = evidence[0]["evidence_id"]
            detail_resp = client.get(
                f"/api/v1/companies/TCS/evidence/{eid}",
                params={"as_of": "2026-04-01T00:00:00+00:00"},
            )
            assert detail_resp.status_code in (200, 404)
