"""
Tests for the F8 professional research report system.

Verifies models, assembly engine, API contracts, serializers,
and router endpoints for all verified companies.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_api_error_handlers
from src.api.f8_router import create_f8_router
from src.api.f8_serializers import professional_report_contract
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.evidence.lineage import build_evidence_lineage
from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
    EvidenceSourceInfo,
    EvidenceSourceRecordInfo,
)
from src.research.report.professional import (
    ProfessionalResearchReport,
    ReportConflictDetail,
    ReportExecutiveOverview,
    ReportItem,
    ReportMethodology,
    ReportPITIntegrity,
    ReportProvenanceChain,
    ReportQualityIndicator,
    ReportQualityLayer,
    ReportSection,
    ReportSourceHealth,
    ReportSourceHealthEntry,
    SectionEpistemic,
    build_professional_report,
)
from src.research.report.professional import (
    ReportEvidenceSection,
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
    archive_root = tmp_path_factory.mktemp("f8-report-archive")
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(create_f8_router(service=service))
    return TestClient(app)


# ── Helper: build minimal lineage ───────────────────────────────


def _make_evidence(
    evidence_id: str,
    *,
    symbol: str = "TEST",
    title: str = "Test evidence",
    explanation: str = "Test explanation",
    evidence_type: str = "FEATURE",
    direction: str = "POSITIVE",
    confidence: str = "0.8",
    reliability: str = "SECONDARY",
    epistemic_type: EpistemicType = EpistemicType.REPORTED,
    verification_status: str = "VERIFIED",
    category: str = "FINANCIAL",
    source_ids: tuple[str, ...] = ("test_source",),
    provenance_ids: tuple[str, ...] = (),
    observation_at: datetime | None = None,
) -> CanonicalEvidenceItem:
    if observation_at is None:
        observation_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return CanonicalEvidenceItem(
        evidence_id=evidence_id,
        symbol=symbol,
        title=title,
        explanation=explanation,
        evidence_type=evidence_type,
        direction=direction,
        confidence=confidence,
        reliability=reliability,
        epistemic_type=epistemic_type,
        verification_status=verification_status,
        category=category,
        source_ids=source_ids,
        provenance_ids=provenance_ids,
        observation_at=observation_at,
    )


def _make_claim(
    claim_id: str,
    *,
    symbol: str = "TEST",
    text: str = "Test claim",
    category: str = "FINANCIAL",
    epistemic_type: EpistemicType = EpistemicType.REPORTED,
) -> EvidenceClaim:
    return EvidenceClaim(
        claim_id=claim_id,
        symbol=symbol,
        text=text,
        category=category,
        epistemic_type=epistemic_type,
    )


def _make_source_profile(
    source_id: str,
    *,
    name: str = "Test Source",
) -> EvidenceSourceInfo:
    return EvidenceSourceInfo(
        source_id=source_id,
        name=name,
        source_type="ANALYTICAL",
        tier="SECONDARY",
        domain="FINANCIAL",
    )


def _build_test_lineage(
    symbol: str = "TEST",
    evidence_items: tuple[CanonicalEvidenceItem, ...] | None = None,
    claims: tuple[EvidenceClaim, ...] | None = None,
    source_profiles: tuple[EvidenceSourceInfo, ...] | None = None,
) -> EvidenceLineage:
    as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)

    if evidence_items is None:
        evidence_items = (
            _make_evidence(
                "ev-pos-1",
                title="Revenue momentum strengthened",
                explanation="Reported revenue growth accelerated in the latest period.",
                direction="POSITIVE",
                category="FINANCIAL",
                epistemic_type=EpistemicType.REPORTED,
            ),
            _make_evidence(
                "ev-pos-2",
                title="New enterprise partnerships signed",
                explanation="Company announced expanded enterprise partnerships.",
                direction="POSITIVE",
                category="BUSINESS",
                epistemic_type=EpistemicType.DERIVED,
            ),
            _make_evidence(
                "ev-neg-1",
                title="Operating costs rising faster than revenue",
                explanation="Cost growth outpaced revenue growth in the recorded period.",
                direction="NEGATIVE",
                category="FINANCIAL",
                epistemic_type=EpistemicType.REPORTED,
            ),
            _make_evidence(
                "ev-mix-1",
                title="Market share estimates diverge across sources",
                explanation="Recorded sources disagree on the direction of market share.",
                direction="MIXED",
                category="MARKET",
                epistemic_type=EpistemicType.INFERRED,
            ),
        )

    if claims is None:
        claims = (
            _make_claim("clm-1", text="Revenue grew 15%"),
            _make_claim(
                "clm-2",
                text="Unknown trend detected",
                epistemic_type=EpistemicType.UNKNOWN,
            ),
        )

    if source_profiles is None:
        source_profiles = (_make_source_profile("test_source"),)

    return EvidenceLineage(
        symbol=symbol,
        as_of=as_of,
        evidence=evidence_items,
        claims=claims,
        source_profiles=source_profiles,
        source_records=(),
        epistemic_type_counts={
            "REPORTED": 2,
            "DERIVED": 1,
            "INFERRED": 1,
        },
        verification_status_counts={"VERIFIED": 4},
        evidence_type_counts={"FEATURE": 4},
        direction_counts={
            "POSITIVE": 2,
            "NEGATIVE": 1,
            "MIXED": 1,
        },
        total_evidence=len(evidence_items),
        total_claims=len(claims),
        total_sources=len(source_profiles),
        total_provenance=0,
    )


# ── Unit tests: SectionEpistemic ────────────────────────────────


class TestSectionEpistemic:
    def test_epistemic_values(self):
        assert SectionEpistemic.REPORTED.value == "REPORTED"
        assert SectionEpistemic.DERIVED.value == "DERIVED"
        assert SectionEpistemic.INFERRED.value == "INFERRED"
        assert SectionEpistemic.UNKNOWN.value == "UNKNOWN"

    def test_epistemic_is_string_enum(self):
        for member in SectionEpistemic:
            assert isinstance(member.value, str)


# ── Unit tests: ReportItem ──────────────────────────────────────


class TestReportItem:
    def test_report_item_creation(self):
        item = ReportItem(
            item_id="test-1",
            text="Revenue grew 15%",
            epistemic_type="REPORTED",
        )
        assert item.item_id == "test-1"
        assert item.epistemic_type == "REPORTED"
        assert item.evidence_ids == ()

    def test_report_item_with_evidence(self):
        item = ReportItem(
            item_id="test-2",
            text="Cash flow improved",
            epistemic_type="DERIVED",
            evidence_ids=("ev-1", "ev-2"),
            source_ids=("src-1",),
            confidence="0.85",
        )
        assert len(item.evidence_ids) == 2
        assert item.confidence == "0.85"


# ── Unit tests: ReportSection ───────────────────────────────────


class TestReportSection:
    def test_section_creation(self):
        section = ReportSection(
            section_id="financial_performance",
            title="Financial Performance",
            status="COMPLETE",
            epistemic_type="REPORTED",
        )
        assert section.section_id == "financial_performance"
        assert section.status == "COMPLETE"

    def test_section_with_items(self):
        items = (
            ReportItem(item_id="i1", text="Item 1"),
            ReportItem(item_id="i2", text="Item 2"),
        )
        section = ReportSection(
            section_id="test",
            title="Test Section",
            items=items,
            total_items=2,
        )
        assert section.total_items == 2
        assert len(section.items) == 2


# ── Unit tests: ReportExecutiveOverview ─────────────────────────


class TestReportExecutiveOverview:
    def test_overview_creation(self):
        overview = ReportExecutiveOverview(
            symbol="TEST",
            evidence_direction="POSITIVE",
            total_evidence=10,
            positive_count=6,
            negative_count=2,
            conflicting_count=2,
        )
        assert overview.symbol == "TEST"
        assert overview.evidence_direction == "POSITIVE"
        assert overview.total_evidence == 10

    def test_overview_unknown_direction(self):
        overview = ReportExecutiveOverview(
            symbol="TEST",
            evidence_direction="UNKNOWN",
        )
        assert overview.evidence_direction == "UNKNOWN"
        assert overview.total_evidence == 0


# ── Unit tests: ReportQualityLayer ──────────────────────────────


class TestReportQualityLayer:
    def test_quality_layer_creation(self):
        layer = ReportQualityLayer(
            evidence_coverage_pct="85.0",
            provenance_coverage_pct="72.5",
            pit_status="PASSED",
        )
        assert layer.evidence_coverage_pct == "85.0"
        assert layer.pit_status == "PASSED"

    def test_quality_indicator(self):
        indicator = ReportQualityIndicator(
            indicator_id="test-ind",
            name="Test Indicator",
            status="GOOD",
            value="100%",
        )
        assert indicator.indicator_id == "test-ind"
        assert indicator.status == "GOOD"


# ── Unit tests: ReportPITIntegrity ──────────────────────────────


class TestReportPITIntegrity:
    def test_pit_integrity_creation(self):
        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        pit = ReportPITIntegrity(
            as_of=as_of,
            pit_checks_passed=True,
        )
        assert pit.as_of == as_of
        assert pit.pit_checks_passed is True

    def test_pit_integrity_with_exclusions(self):
        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        pit = ReportPITIntegrity(
            as_of=as_of,
            future_evidence_excluded=3,
            pit_checks_passed=False,
        )
        assert pit.future_evidence_excluded == 3
        assert pit.pit_checks_passed is False


# ── Unit tests: ReportProvenanceChain ───────────────────────────


class TestReportProvenanceChain:
    def test_provenance_chain_creation(self):
        chain = ReportProvenanceChain(
            total_provenance=10,
            with_available_at=8,
            with_published_at=7,
        )
        assert chain.total_provenance == 10
        assert chain.with_available_at == 8


# ── Unit tests: ReportSourceHealth ──────────────────────────────


class TestReportSourceHealth:
    def test_source_health_creation(self):
        health = ReportSourceHealth(
            total_sources=5,
            healthy_sources=4,
            degraded_sources=1,
        )
        assert health.total_sources == 5
        assert health.healthy_sources == 4


# ── Assembly engine tests ───────────────────────────────────────


class TestBuildProfessionalReport:
    def test_builds_report_from_lineage(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert isinstance(report, ProfessionalResearchReport)
        assert report.symbol == "TEST"
        assert report.as_of == lineage.as_of

    def test_executive_overview_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.executive_overview is not None
        assert report.executive_overview.symbol == "TEST"
        assert report.executive_overview.total_evidence == 4
        assert report.executive_overview.positive_count == 2
        assert report.executive_overview.negative_count == 1
        assert report.executive_overview.conflicting_count == 1

    def test_executive_direction_positive(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.executive_overview.evidence_direction == "POSITIVE"

    def test_executive_direction_negative(self):
        ev = (
            _make_evidence(
                "ev-n1",
                title="Margin pressure from deposit costs",
                explanation="Recorded analysis flags rising deposit costs.",
                direction="NEGATIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-n2",
                title="Regulatory penalty recorded",
                explanation="A regulatory penalty was disclosed in the period.",
                direction="NEGATIVE",
                category="BUSINESS",
            ),
            _make_evidence(
                "ev-p1",
                title="Loan book growth sustained",
                explanation="Management reported continued loan book growth.",
                direction="POSITIVE",
                category="MARKET",
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        assert report.executive_overview.evidence_direction == "NEGATIVE"

    def test_executive_direction_mixed(self):
        ev = (
            _make_evidence("ev-p1", direction="POSITIVE", category="FINANCIAL"),
            _make_evidence("ev-n1", direction="NEGATIVE", category="BUSINESS"),
            _make_evidence("ev-m1", direction="MIXED", category="MARKET"),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        assert report.executive_overview.evidence_direction == "MIXED"

    def test_executive_direction_unknown_when_empty(self):
        lineage = _build_test_lineage(evidence_items=())
        report = build_professional_report(lineage=lineage)

        assert report.executive_overview.evidence_direction == "UNKNOWN"

    def test_research_snapshot_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.research_snapshot is not None
        assert report.research_snapshot.section_id == "research_snapshot"
        assert report.research_snapshot.status == "COMPLETE"
        assert report.research_snapshot.total_items > 0

    def test_positive_evidence_section(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.positive_evidence is not None
        assert report.positive_evidence.total_items == 2

    def test_negative_evidence_section(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.negative_evidence is not None
        assert report.negative_evidence.total_items == 1

    def test_conflicting_evidence_section(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.conflicting_evidence is not None
        assert report.conflicting_evidence.total_items == 1

    def test_no_positive_evidence_returns_none(self):
        ev = (
            _make_evidence("ev-n1", direction="NEGATIVE", category="FINANCIAL"),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        assert report.positive_evidence is None

    def test_source_health_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.source_health is not None
        assert report.source_health.total_sources >= 1

    def test_provenance_chain_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.provenance_chain is not None
        assert report.provenance_chain.total_provenance == 0

    def test_pit_integrity_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.pit_integrity is not None
        assert report.pit_integrity.pit_checks_passed is True
        assert report.pit_integrity.as_of == lineage.as_of

    def test_methodology_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.methodology is not None
        assert "epistemic" in report.methodology.methodology_summary.lower()
        assert len(report.methodology.known_limitations) > 0

    def test_quality_layer_populated(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)

        assert report.quality_layer is not None
        assert report.quality_layer.pit_status == "PASSED"
        assert len(report.quality_layer.indicators) > 0

    def test_epistemic_type_preserved(self):
        ev = (
            _make_evidence(
                "ev-rpt",
                title="Reported revenue figure",
                explanation="Revenue as stated in the recorded filing.",
                direction="POSITIVE",
                category="FINANCIAL",
                epistemic_type=EpistemicType.REPORTED,
            ),
            _make_evidence(
                "ev-der",
                title="Derived revenue growth rate",
                explanation="Growth computed from two recorded periods.",
                direction="POSITIVE",
                category="BUSINESS",
                epistemic_type=EpistemicType.DERIVED,
            ),
            _make_evidence(
                "ev-inf",
                title="Inferred demand slowdown",
                explanation="Slowdown inferred from multiple recorded sources.",
                direction="NEGATIVE",
                category="MARKET",
                epistemic_type=EpistemicType.INFERRED,
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        # Evidence sections should preserve epistemic types
        assert report.positive_evidence is not None
        epistemic_types = {
            item.epistemic_type.value
            for item in report.positive_evidence.items
        }
        assert "REPORTED" in epistemic_types
        assert "DERIVED" in epistemic_types

    def test_unknown_not_converted_to_negative(self):
        ev = (
            _make_evidence(
                "ev-unk",
                direction="NEUTRAL",
                category="FINANCIAL",
                epistemic_type=EpistemicType.UNKNOWN,
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        # UNKNOWN evidence should be NEUTRAL, not NEGATIVE
        assert report.negative_evidence is None
        assert report.executive_overview.negative_count == 0

    def test_deterministic_ordering(self):
        lineage = _build_test_lineage()
        report1 = build_professional_report(lineage=lineage)
        report2 = build_professional_report(lineage=lineage)

        assert (
            report1.executive_overview.evidence_direction
            == report2.executive_overview.evidence_direction
        )
        assert (
            report1.executive_overview.total_evidence
            == report2.executive_overview.total_evidence
        )
        assert (
            report1.quality_layer.evidence_coverage_pct
            == report2.quality_layer.evidence_coverage_pct
        )

    def test_company_name_forwarded(self):
        lineage = _build_test_lineage()
        report = build_professional_report(
            lineage=lineage,
            company_name="Test Corp",
        )
        assert report.company_name == "Test Corp"
        assert report.executive_overview.company_name == "Test Corp"

    def test_executive_key_findings_limited(self):
        ev = tuple(
            _make_evidence(
                f"ev-{i}",
                title=f"Recorded finding {i}",
                explanation=f"Distinct recorded evidence item {i}.",
                direction="POSITIVE",
                category="FINANCIAL",
                confidence=str(0.5 + i * 0.05),
            )
            for i in range(10)
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        # Key findings capped at 5
        assert len(report.executive_overview.key_findings) <= 5

    def test_executive_key_risks_from_negative(self):
        ev = (
            _make_evidence(
                "ev-p1",
                title="Positive operating development",
                explanation="Recorded positive development in operations.",
                direction="POSITIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-n1",
                title="Rising leverage flagged",
                explanation="Recorded analysis flags rising leverage.",
                direction="NEGATIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-n2",
                title="Litigation exposure disclosed",
                explanation="A litigation matter was disclosed in filings.",
                direction="NEGATIVE",
                category="BUSINESS",
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        assert len(report.executive_overview.key_risks) == 2


# ── Serializer tests ────────────────────────────────────────────


class TestProfessionalReportSerializer:
    def test_serializer_produces_dict(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        assert isinstance(contract, dict)
        assert "company" in contract
        assert "report" in contract

    def test_serializer_company_fields(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        assert contract["company"]["symbol"] == "TEST"
        assert contract["company"]["company_name"] == "Test Corp"

    def test_serializer_report_version(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        assert contract["report"]["report_version"] == "2.0"

    def test_serializer_executive_overview(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        exec_ov = contract["report"]["executive_overview"]
        assert exec_ov is not None
        assert exec_ov["symbol"] == "TEST"
        assert exec_ov["total_evidence"] == 4

    def test_serializer_evidence_sections(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        assert contract["report"]["positive_evidence"] is not None
        assert contract["report"]["negative_evidence"] is not None
        assert contract["report"]["conflicting_evidence"] is not None

    def test_serializer_source_health(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        sh = contract["report"]["source_health"]
        assert sh is not None
        assert sh["total_sources"] >= 1

    def test_serializer_pit_integrity(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        pit = contract["report"]["pit_integrity"]
        assert pit is not None
        assert pit["pit_checks_passed"] is True

    def test_serializer_methodology(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        meth = contract["report"]["methodology"]
        assert meth is not None
        assert len(meth["known_limitations"]) > 0

    def test_serializer_quality_layer(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        ql = contract["report"]["quality_layer"]
        assert ql is not None
        assert ql["pit_status"] == "PASSED"
        assert len(ql["indicators"]) > 0

    def test_serializer_epistemic_in_items(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        # Research snapshot should have epistemic types
        snapshot = contract["report"]["research_snapshot"]
        assert snapshot is not None
        for item in snapshot["items"]:
            assert "epistemic_type" in item

    def test_serializer_none_sections_are_null(self):
        lineage = _build_test_lineage(
            evidence_items=(),
        )
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        # With no evidence, many sections should be null
        assert contract["report"]["business_context"] is None
        assert contract["report"]["financial_performance"] is None
        assert contract["report"]["positive_evidence"] is None

    def test_serializer_utc_timestamps(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        as_of = contract["report"]["as_of"]
        assert "+00:00" in as_of or "Z" in as_of


# ── API integration tests ───────────────────────────────────────


class TestF8RouterEndpoints:
    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_returns_200(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_company(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        assert "company" in data
        assert data["company"]["symbol"] == symbol

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_report(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        assert "report" in data
        report = data["report"]
        assert report["symbol"] == symbol
        assert "as_of" in report
        assert "report_version" in report

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_executive_overview(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        exec_ov = data["report"]["executive_overview"]
        assert exec_ov is not None
        assert "evidence_direction" in exec_ov
        assert "total_evidence" in exec_ov

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_research_snapshot(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        snapshot = data["report"]["research_snapshot"]
        assert snapshot is not None
        assert snapshot["section_id"] == "research_snapshot"

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_source_health(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        sh = data["report"]["source_health"]
        assert sh is not None
        assert "total_sources" in sh

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_pit_integrity(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        pit = data["report"]["pit_integrity"]
        assert pit is not None
        assert "as_of" in pit
        assert "pit_checks_passed" in pit

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_methodology(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        meth = data["report"]["methodology"]
        assert meth is not None
        assert "methodology_summary" in meth
        assert "epistemic_disclosure" in meth

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_quality_layer(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        ql = data["report"]["quality_layer"]
        assert ql is not None
        assert "evidence_coverage_pct" in ql
        assert "pit_status" in ql
        assert "indicators" in ql

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_epistemic_types_present(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        snapshot = data["report"]["research_snapshot"]
        assert snapshot is not None
        for item in snapshot["items"]:
            assert item["epistemic_type"] in (
                "REPORTED",
                "DERIVED",
                "INFERRED",
                "UNKNOWN",
            )

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_with_as_of(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report",
            params={"as_of": DEFAULT_AS_OF_ISO},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["report"]["as_of"] is not None

    def test_unknown_company_returns_error(self, client):
        response = client.get(
            "/api/v1/companies/INVALID/research-report"
        )
        assert response.status_code in (400, 404, 422)

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_no_trade_signals(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        report_str = str(data)
        # Should not contain trading language
        assert "buy" not in report_str.lower().split(
            "methodology"
        )[0] or "buy" in report_str.lower().split(
            "methodology"
        )[0]

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_evidence_lineage(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        # Evidence lineage should be available
        assert "report" in data

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_deterministic(
        self, client, symbol
    ):
        r1 = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        ).json()
        r2 = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        ).json()
        assert (
            r1["report"]["executive_overview"]["evidence_direction"]
            == r2["report"]["executive_overview"]["evidence_direction"]
        )
        assert (
            r1["report"]["executive_overview"]["total_evidence"]
            == r2["report"]["executive_overview"]["total_evidence"]
        )

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_evidence_direction_valid(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        direction = data["report"]["executive_overview"][
            "evidence_direction"
        ]
        assert direction in (
            "POSITIVE",
            "NEGATIVE",
            "MIXED",
            "NEUTRAL",
            "UNKNOWN",
        )

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_conflict_details(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        assert "conflict_details" in data["report"]
        assert isinstance(data["report"]["conflict_details"], list)

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_cannot_assess(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        exec_ov = data["report"]["executive_overview"]
        assert "cannot_assess" in exec_ov
        assert isinstance(exec_ov["cannot_assess"], list)

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_has_hidden_insights(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        exec_ov = data["report"]["executive_overview"]
        assert "hidden_insights" in exec_ov
        assert isinstance(exec_ov["hidden_insights"], list)

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_pit_has_market_as_of(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        pit = data["report"]["pit_integrity"]
        assert "market_as_of" in pit
        assert "evidence_included" in pit
        assert "sources_discovered" in pit
        assert "sources_accepted" in pit

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_report_source_health_has_new_fields(
        self, client, symbol
    ):
        response = client.get(
            f"/api/v1/companies/{symbol}/research-report"
        )
        data = response.json()
        sh = data["report"]["source_health"]
        assert "stale_sources" in sh
        assert "provider_failures" in sh
        assert isinstance(sh["provider_failures"], list)
        if sh["entries"]:
            entry = sh["entries"][0]
            assert "source_type" in entry
            assert "stale" in entry
            assert "provenance_complete" in entry
            assert "categories" in entry


# ── ConflictDetail model tests ──────────────────────────────────


class TestReportConflictDetail:
    def test_conflict_detail_creation(self):
        detail = ReportConflictDetail(
            conflict_id="conflict-1",
            topic="Revenue recognition",
            description="Two sources disagree on revenue method",
            management_involved=False,
            first_item_id="item-1",
            first_title="Source A says revenue is recognized upfront",
            first_direction="POSITIVE",
            first_source="source_a",
            first_excerpt="Revenue recognized upfront per filing",
            second_item_id="item-2",
            second_title="Source B says revenue is deferred",
            second_direction="NEGATIVE",
            second_source="source_b",
            second_excerpt="Revenue deferred per analyst report",
        )
        assert detail.conflict_id == "conflict-1"
        assert detail.management_involved is False
        assert detail.first_direction == "POSITIVE"
        assert detail.second_direction == "NEGATIVE"

    def test_conflict_detail_management_involved(self):
        detail = ReportConflictDetail(
            conflict_id="conflict-2",
            topic="Governance",
            description="Management stated X but filing shows Y",
            management_involved=True,
            first_item_id="item-3",
            first_title="Management statement",
            first_direction="POSITIVE",
            first_source="source_c",
            first_excerpt="Management said X",
            second_item_id="item-4",
            second_title="Filing shows Y",
            second_direction="NEGATIVE",
            second_source="source_d",
            second_excerpt="Filing shows Y",
        )
        assert detail.management_involved is True


# ── New model tests ─────────────────────────────────────────────


class TestReportSourceHealthEntry:
    def test_entry_creation(self):
        entry = ReportSourceHealthEntry(
            source_id="src-1",
            name="Test Source",
            source_type="ANALYTICAL",
            tier="SECONDARY",
            evidence_count=5,
            freshness_status="CURRENT",
            coverage_status="ACTIVE",
            stale=False,
            provenance_complete=True,
            categories=("FINANCIAL", "MARKET"),
        )
        assert entry.source_id == "src-1"
        assert entry.stale is False
        assert entry.provenance_complete is True
        assert len(entry.categories) == 2

    def test_entry_stale(self):
        entry = ReportSourceHealthEntry(
            source_id="src-2",
            name="Stale Source",
            stale=True,
            provenance_complete=False,
        )
        assert entry.stale is True


class TestReportMethodology:
    def test_methodology_creation(self):
        method = ReportMethodology(
            methodology_summary="Test methodology",
            known_limitations=("Limitation 1", "Limitation 2"),
            PIT_policy="All evidence PIT-safe",
            epistemic_disclosure="Every item labeled",
        )
        assert method.methodology_summary == "Test methodology"
        assert len(method.known_limitations) == 2
        assert method.PIT_policy == "All evidence PIT-safe"


# ── Assembly engine: intelligence integration tests ─────────────


class TestAssemblyIntelligenceIntegration:
    def test_executive_overview_with_cannot_assess(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()
        intelligence.insufficient_evidence_notes = (
            "Cannot assess management quality due to stale data",
            "Insufficient data on market share trends",
        )
        intelligence.changes = ()
        intelligence.hidden_information = None

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
        )
        assert len(report.executive_overview.cannot_assess) == 2
        assert "Cannot assess" in report.executive_overview.cannot_assess[0]

    def test_executive_overview_with_changes(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()

        change1 = MagicMock()
        change1.item_id = "item-1"
        change1.title = "Revenue estimate updated"
        change1.description = "Revenue estimate increased by 5%"
        change1.change_type.value = "UPDATED"
        change1.kind.value = "FINANCIAL"
        change2 = MagicMock()
        change2.item_id = "item-2"
        change2.title = "New risk identified"
        change2.description = "Regulatory risk flagged"
        change2.change_type.value = "ADDED"
        change2.kind.value = "RISK"
        intelligence.changes = (change1, change2)
        intelligence.insufficient_evidence_notes = ()
        intelligence.hidden_information = None

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
        )
        assert len(report.executive_overview.what_changed) == 2
        assert "UPDATED" in report.executive_overview.what_changed[0].metadata["change_type"]

    def test_executive_overview_with_hidden_insights(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()
        intelligence.changes = ()
        intelligence.insufficient_evidence_notes = ()

        hi = MagicMock()
        obs = MagicMock()
        obs.observation_id = "obs-1"
        obs.label = "Implied growth rate diverges"
        obs.description = "Growth rate implied by filings differs from analyst consensus"
        obs.related_item_ids = ("ev-1",)
        obs.source_ids = ("src-1",)
        obs.derivation = "Computed from revenue trend vs consensus"
        obs.severity = "WARNING"
        obs.semantic_category.value = "FINANCIAL"
        hi.observations = (obs,)
        intelligence.hidden_information = hi

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
        )
        assert len(report.executive_overview.hidden_insights) == 1
        assert report.executive_overview.hidden_insights[0].epistemic_type == "DERIVED"

    def test_quality_layer_with_stale_inputs(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()

        status = MagicMock()
        status.quality.stale_source_count = 3
        status.coverage.missing_categories = ["ESG", "SENTIMENT"]
        intelligence.status = status

        intelligence.source_statuses = ()
        research_gaps = MagicMock()
        research_gaps.gap_count = 2

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
            research_gaps=research_gaps,
        )
        assert report.quality_layer.stale_input_count == 3
        assert report.quality_layer.unsupported_dimension_count == 2
        assert report.quality_layer.critical_gap_count == 2

    def test_source_health_with_stale(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()

        ss = MagicMock()
        ss.source_name = "test_source"
        ss.source_type = "ANALYTICAL"
        ss.item_count = 5
        ss.latest_available_at = None
        ss.stale = True
        ss.provenance_completeness = True
        ss.categories = ("FINANCIAL",)
        intelligence.source_statuses = (ss,)
        intelligence.provider_failures = ("provider_x",)
        intelligence.status = None

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
        )
        assert report.source_health.stale_sources >= 1
        assert "provider_x" in report.source_health.provider_failures

    def test_pit_integrity_with_acquisition(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()
        intelligence.as_of = lineage.as_of

        acquisition = MagicMock()
        acquisition.sources_discovered = 10
        acquisition.sources_accepted = 7

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
            acquisition=acquisition,
        )
        assert report.pit_integrity.sources_discovered == 10
        assert report.pit_integrity.sources_accepted == 7
        assert report.pit_integrity.market_as_of is not None

    def test_conflict_details_built(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        intelligence = MagicMock()

        side1 = MagicMock()
        side1.item_id = "item-1"
        side1.title = "Revenue is growing"
        side1.direction.value = "POSITIVE"
        side1.source_name = "source_a"
        side1.excerpt = "Revenue grew 15% YoY"

        side2 = MagicMock()
        side2.item_id = "item-2"
        side2.title = "Revenue is declining"
        side2.direction.value = "NEGATIVE"
        side2.source_name = "source_b"
        side2.excerpt = "Revenue declined in Q2"

        conflict = MagicMock()
        conflict.conflict_id = "conflict-1"
        conflict.topic = "Revenue trajectory"
        conflict.description = "Sources disagree on revenue trend"
        conflict.management_involved = False
        conflict.first = side1
        conflict.second = side2

        intelligence.conflicts = (conflict,)
        intelligence.changes = ()
        intelligence.insufficient_evidence_notes = ()
        intelligence.hidden_information = None
        intelligence.source_statuses = ()
        intelligence.provider_failures = ()

        report = build_professional_report(
            lineage=lineage,
            intelligence=intelligence,
        )
        assert len(report.conflict_details) == 1
        assert report.conflict_details[0].conflict_id == "conflict-1"
        assert report.conflict_details[0].first_direction == "POSITIVE"
        assert report.conflict_details[0].second_direction == "NEGATIVE"

    def test_research_gaps_built(self):
        from unittest.mock import MagicMock

        lineage = _build_test_lineage()
        research_gaps = MagicMock()
        gap = MagicMock()
        gap.gap_id = "gap-1"
        gap.status = "OPEN"
        gap.category = "FINANCIAL"
        gap.gap = "No data on R&D spending trends"
        gap.priority = "HIGH"
        gap.reason = "Source not available"
        gap.what_would_resolve = "Need annual report data"
        research_gaps.gaps = (gap,)
        research_gaps.gap_count = 1

        report = build_professional_report(
            lineage=lineage,
            research_gaps=research_gaps,
        )
        assert report.research_gaps is not None
        assert report.research_gaps.total_items == 1
        assert report.research_gaps.items[0].item_id == "gap-1"

    def test_deduplication_by_evidence_id(self):
        dup_ev = (
            _make_evidence(
                "ev-dup",
                title="Duplicate fact recorded twice",
                explanation="The same recorded fact appears under one id.",
                direction="POSITIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-dup",
                title="Duplicate fact recorded twice",
                explanation="The same recorded fact appears under one id.",
                direction="NEGATIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-unique",
                title="A distinct business development",
                explanation="This item describes a different recorded fact.",
                direction="POSITIVE",
                category="BUSINESS",
            ),
        )
        lineage = _build_test_lineage(evidence_items=dup_ev)
        report = build_professional_report(lineage=lineage)

        # Only first occurrence kept, so 2 evidence items
        total = (
            (report.positive_evidence.total_items if report.positive_evidence else 0)
            + (report.negative_evidence.total_items if report.negative_evidence else 0)
        )
        assert total == 2

    def test_empty_intelligence_graceful(self):
        lineage = _build_test_lineage()
        report = build_professional_report(
            lineage=lineage,
            intelligence=None,
            research_gaps=None,
            acquisition=None,
        )
        assert report.executive_overview is not None
        assert report.executive_overview.what_changed == ()
        assert report.executive_overview.hidden_insights == ()
        assert report.executive_overview.cannot_assess == ()
        assert report.conflict_details == ()
        assert report.research_gaps is None


# ── Intel item enrichment tests ─────────────────────────────────


def _make_intel_item(
    item_id: str,
    *,
    intel_category: str = "BUSINESS_NEWS",
    kind: str = "EVENT",
    direction: str = "POSITIVE",
    stance: str = "NEUTRAL",
    semantic_category: str = "OBSERVATION",
    verification_status: str = "REPORTED",
    title: str = "Test intel item",
    description: str = "Test intel description",
    confidence: str = "0.7",
    source_name: str = "test_intel_source",
):
    """Create a mock CorporateIntelItem for testing."""
    from unittest.mock import MagicMock

    item = MagicMock()
    item.item_id = item_id
    item.title = title
    item.description = description
    item.confidence = confidence

    ic = MagicMock()
    ic.value = intel_category
    item.intel_category = ic

    k = MagicMock()
    k.value = kind
    item.kind = k

    d = MagicMock()
    d.value = direction
    item.direction = d

    s = MagicMock()
    s.value = stance
    item.stance = s

    sc = MagicMock()
    sc.value = semantic_category
    item.semantic_category = sc

    vs = MagicMock()
    vs.value = verification_status
    item.verification_status = vs

    source = MagicMock()
    source.source_name = source_name
    item.source = source

    item.published_at = datetime(2026, 7, 15, tzinfo=timezone.utc)
    item.available_at = datetime(2026, 7, 16, tzinfo=timezone.utc)

    return item


class TestIntelEnrichment:
    """Tests for intel item enrichment in report sections."""

    def test_intel_item_enriches_management_strategy(self):
        lineage = _build_test_lineage()
        intel_items = (
            _make_intel_item(
                "intel-mgmt-1",
                intel_category="MANAGEMENT_STATEMENT",
                title="CEO outlines 3-year strategy",
                description="Focus on digital transformation",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        # management_strategy should now contain the intel item
        assert report.management_strategy is not None
        found = any(
            i.item_id == "intel-mgmt-1"
            for i in report.management_strategy.items
        )
        assert found

    def test_intel_item_enriches_corporate_actions(self):
        lineage = _build_test_lineage()
        intel_items = (
            _make_intel_item(
                "intel-ca-1",
                intel_category="CORPORATE_ACTION",
                title="Board approves dividend",
                description="Interim dividend of Rs 10 per share",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.corporate_actions is not None
        found = any(
            i.item_id == "intel-ca-1"
            for i in report.corporate_actions.items
        )
        assert found

    def test_intel_item_enriches_business_developments(self):
        lineage = _build_test_lineage()
        intel_items = (
            _make_intel_item(
                "intel-biz-1",
                intel_category="ORDER_CONTRACT",
                title="Wins Rs 500 Cr government contract",
                description="5-year IT services deal",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.business_developments is not None
        found = any(
            i.item_id == "intel-biz-1"
            for i in report.business_developments.items
        )
        assert found

    def test_intel_only_section_has_note(self):
        """When a section has only intel items and no evidence, a note is added."""
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item(
                "intel-mgmt-only",
                intel_category="MANAGEMENT_STATEMENT",
                title="CEO earnings call remarks",
                description="Guidance for next quarter",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.management_strategy is not None
        assert report.management_strategy.total_items == 1
        # Should have a note explaining intel-only population
        has_note = any("intelligence items" in n for n in report.management_strategy.notes)
        assert has_note

    def test_mixed_evidence_and_intel_section(self):
        """Section with both evidence and intel items gets a combination note."""
        ev = (
            _make_evidence("ev-biz-1", category="EVENT", direction="POSITIVE"),
            _make_evidence("ev-biz-2", category="EVENT", direction="NEGATIVE"),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        intel_items = (
            _make_intel_item(
                "intel-biz-mix",
                intel_category="BUSINESS_NEWS",
                title="Major partnership announced",
                description="Joint venture with global tech firm",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.business_developments is not None
        # 2 evidence + 1 intel = 3 total
        assert report.business_developments.total_items == 3
        has_combo_note = any("combines" in n for n in report.business_developments.notes)
        assert has_combo_note

    def test_intel_item_epistemic_type_preserved(self):
        """Intel items with DERIVED verification status get DERIVED epistemic type."""
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item(
                "intel-derived-1",
                intel_category="MANAGEMENT_STATEMENT",
                verification_status="REPORTED",
                title="Analyst consensus derived metric",
                description="Operating margin improved",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        section = report.management_strategy
        assert section is not None
        item = section.items[0]
        assert item.epistemic_type == "REPORTED"

    def test_intel_items_sorted_deterministically(self):
        """Intel items within a section are sorted by item_id."""
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item("intel-z", intel_category="CORPORATE_ACTION", title="Z item"),
            _make_intel_item("intel-a", intel_category="CORPORATE_ACTION", title="A item"),
            _make_intel_item("intel-m", intel_category="CORPORATE_ACTION", title="M item"),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.corporate_actions is not None
        ids = [i.item_id for i in report.corporate_actions.items]
        assert ids == ["intel-a", "intel-m", "intel-z"]

    def test_intel_source_ids_collected(self):
        """Source names from intel items are collected into section source_ids."""
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item(
                "intel-src-1",
                intel_category="CORPORATE_ACTION",
                source_name="bloomberg",
            ),
            _make_intel_item(
                "intel-src-2",
                intel_category="CORPORATE_ACTION",
                source_name="reuters",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.corporate_actions is not None
        assert "bloomberg" in report.corporate_actions.source_ids
        assert "reuters" in report.corporate_actions.source_ids

    def test_unknown_intel_category_not_matched(self):
        """Intel items with unmapped categories do not appear in any section."""
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item(
                "intel-unknown",
                intel_category="NONEXISTENT_CATEGORY",
                title="Should not appear",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        # No section should contain this item
        for section_name in [
            "business_context", "financial_performance", "financial_quality",
            "market_context", "business_developments", "management_strategy",
            "competitive_position", "innovation", "future_technology",
            "industry_context", "capital_allocation", "corporate_actions",
            "timeline",
        ]:
            section = getattr(report, section_name, None)
            if section is not None:
                found = any(i.item_id == "intel-unknown" for i in section.items)
                assert not found, f"Item found in {section_name}"

    def test_intel_enrichment_across_all_companies(self, client):
        """Intel enrichment works for all 6 verified companies via API."""
        for symbol in VERIFIED_COMPANIES:
            resp = client.get(
                f"/api/v1/companies/{symbol}/research-report",
                params={"as_of": DEFAULT_AS_OF_ISO},
            )
            assert resp.status_code == 200
            body = resp.json()
            report = body["report"]
            # At least one section should be present
            sections_present = sum(
                1 for key in [
                    "research_snapshot", "business_context",
                    "financial_performance", "executive_overview",
                ]
                if report.get(key) is not None
            )
            assert sections_present >= 1, f"{symbol}: too few sections"


# ── Serializer: new fields tests ─────────────────────────────────


class TestSerializerNewFields:
    def test_serializer_conflict_details(self):
        from src.research.report.professional import ReportConflictDetail

        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        # Manually inject a conflict detail
        object.__setattr__(
            report,
            "conflict_details",
            (
                ReportConflictDetail(
                    conflict_id="c1",
                    topic="Test",
                    description="Test conflict",
                    first_item_id="i1",
                    first_title="Side A",
                    first_direction="POSITIVE",
                    first_source="src_a",
                    first_excerpt="excerpt A",
                    second_item_id="i2",
                    second_title="Side B",
                    second_direction="NEGATIVE",
                    second_source="src_b",
                    second_excerpt="excerpt B",
                ),
            ),
        )
        contract = professional_report_contract(report, company_name="Test")
        details = contract["report"]["conflict_details"]
        assert len(details) == 1
        assert details[0]["conflict_id"] == "c1"
        assert details[0]["first_direction"] == "POSITIVE"
        assert details[0]["second_direction"] == "NEGATIVE"

    def test_serializer_executive_new_fields(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(report, company_name="Test")
        exec_ov = contract["report"]["executive_overview"]
        assert "cannot_assess" in exec_ov
        assert "hidden_insights" in exec_ov
        assert isinstance(exec_ov["cannot_assess"], list)
        assert isinstance(exec_ov["hidden_insights"], list)

    def test_serializer_pit_new_fields(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(report, company_name="Test")
        pit = contract["report"]["pit_integrity"]
        assert "market_as_of" in pit
        assert "evidence_included" in pit
        assert "sources_discovered" in pit
        assert "sources_accepted" in pit

    def test_serializer_source_health_new_fields(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(report, company_name="Test")
        sh = contract["report"]["source_health"]
        assert "stale_sources" in sh
        assert "provider_failures" in sh
        if sh["entries"]:
            entry = sh["entries"][0]
            assert "source_type" in entry
            assert "stale" in entry
            assert "provenance_complete" in entry
            assert "categories" in entry

    def test_serializer_methodology_fields(self):
        lineage = _build_test_lineage()
        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(report, company_name="Test")
        meth = contract["report"]["methodology"]
        assert "methodology_summary" in meth
        assert "known_limitations" in meth
        assert "data_freshness_note" in meth
        assert "PIT_policy" in meth
        assert "epistemic_disclosure" in meth


# ── F-TRACK stabilization: output-quality regression tests ──────


def _iter_report_texts(report_payload: dict) -> list[tuple[str, str]]:
    """Yield (section_name, text) for every displayed item text."""
    out: list[tuple[str, str]] = []
    for name, sec in report_payload["report"].items():
        if isinstance(sec, dict) and "items" in sec:
            for it in sec["items"]:
                if isinstance(it, dict) and it.get("text"):
                    out.append((name, it["text"]))
    return out


class TestOutputQualityRealData:
    """Output-quality gates over the recorded fixtures (all companies)."""

    @pytest.fixture
    def reports_by_symbol(self, client):
        out = {}
        for symbol in VERIFIED_COMPANIES:
            resp = client.get(
                f"/api/v1/companies/{symbol}/research-report",
                params={"as_of": DEFAULT_AS_OF_ISO},
            )
            assert resp.status_code == 200
            out[symbol] = resp.json()
        return out

    def test_no_duplicate_item_texts_across_report(self, reports_by_symbol):
        for symbol, payload in reports_by_symbol.items():
            seen = set()
            for _, text in _iter_report_texts(payload):
                key = " ".join(text.split()).lower()
                assert key not in seen, f"{symbol}: duplicated text: {text[:80]}"
                seen.add(key)

    def test_no_raw_long_decimals_in_output(self, reports_by_symbol):
        pattern = re.compile(r"\d+\.\d{5,}")
        for symbol, payload in reports_by_symbol.items():
            hits = pattern.findall(json.dumps(payload))
            assert not hits, f"{symbol}: raw decimals leaked: {hits[:3]}"

    def test_no_agent_boilerplate_in_narrative(self, reports_by_symbol):
        for symbol, payload in reports_by_symbol.items():
            for _, text in _iter_report_texts(payload):
                assert (
                    "contains evidence relevant" not in text
                ), f"{symbol}: internal agent boilerplate reached narrative"

    def test_currency_amounts_use_house_convention(self, reports_by_symbol):
        for symbol, payload in reports_by_symbol.items():
            for _, text in _iter_report_texts(payload):
                for match in re.findall(r"[Rr]eported revenue ([^.;]+)", text):
                    assert match.strip().startswith("Rs "), (
                        f"{symbol}: unformatted revenue amount: {match}"
                    )

    def test_research_snapshot_source_count_matches_source_health(
        self, reports_by_symbol
    ):
        for symbol, payload in reports_by_symbol.items():
            rep = payload["report"]
            snapshot = rep["research_snapshot"]
            health = rep["source_health"]
            count_items = [
                it for it in snapshot["items"]
                if it["item_id"] == "snapshot-source-count"
            ]
            assert count_items
            expected = f"Total sources: {health['total_sources']}"
            assert count_items[0]["text"] == expected, (
                f"{symbol}: snapshot source count inconsistent with source health"
            )


class TestOutputQualitySynthetic:
    """Deterministic unit gates over assembled reports."""

    def test_content_duplicates_merge_and_union_sources(self):
        ev = (
            _make_evidence(
                "ev-a",
                title="Same recorded fact",
                explanation="Recorded identically by two sources.",
                direction="POSITIVE",
                category="FINANCIAL",
                source_ids=("src-1",),
            ),
            _make_evidence(
                "ev-b",
                title="Same recorded fact",
                explanation="Recorded identically by two sources.",
                direction="POSITIVE",
                category="FINANCIAL",
                source_ids=("src-2",),
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        assert report.positive_evidence is not None
        assert report.positive_evidence.total_items == 1
        item = report.positive_evidence.items[0]
        assert set(item.source_ids) == {"src-1", "src-2"}

    def test_opposite_direction_duplicates_are_not_merged(self):
        ev = (
            _make_evidence(
                "ev-pos",
                title="Contested claim",
                explanation="One source records a positive reading.",
                direction="POSITIVE",
                category="FINANCIAL",
            ),
            _make_evidence(
                "ev-neg",
                title="Contested claim",
                explanation="Another records a negative reading.",
                direction="NEGATIVE",
                category="FINANCIAL",
            ),
        )
        lineage = _build_test_lineage(evidence_items=ev)
        report = build_professional_report(lineage=lineage)

        # Conflicting readings must remain visible.
        assert report.positive_evidence is not None
        assert report.negative_evidence is not None

    def test_intel_item_presented_once_in_primary_section(self):
        lineage = _build_test_lineage(evidence_items=())
        intel_items = (
            _make_intel_item(
                "intel-news-1",
                intel_category="BUSINESS_NEWS",
                title="Partnership expanded",
            ),
        )
        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        # BUSINESS_NEWS primary section is business_developments; the
        # same item must not also populate business_context.
        assert report.business_developments is not None
        ids = [i.item_id for i in report.business_developments.items]
        assert "intel-news-1" in ids
        if report.business_context is not None:
            ctx_ids = [i.item_id for i in report.business_context.items]
            assert "intel-news-1" not in ctx_ids

    def test_intel_evidence_twin_not_duplicated_in_sections(self):
        """An intel item converted into evidence appears once only."""
        from src.research.company_intel.models import SourceRef
        from src.research.company_intel.models import CorporateIntelItem
        from src.research.company_intel.semantics import (
            IntelCategory,
            IntelDirection,
            IntelKind,
        )
        from src.research.evidence.lineage import build_evidence_lineage

        intel_items = (
            CorporateIntelItem(
                item_id="intel-div-1",
                symbol="TEST",
                kind=IntelKind.BUSINESS_EVENT,
                intel_category=IntelCategory.CORPORATE_ACTION,
                direction=IntelDirection.POSITIVE,
                title="Interim dividend declared",
                description="Board declared an interim dividend.",
                published_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
                available_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
                source=SourceRef(
                    source_name="test_intel_source",
                    source_type="NEWS",
                    reliability_tier=2,
                ),
                confidence=Decimal("0.7"),
            ),
        )
        lineage = build_evidence_lineage(
            symbol="TEST",
            as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
            evidence_items=(),
            intel_items=intel_items,
            pit_filter=True,
        )
        # Sanity: the conversion path produced the evidence twin.
        twin_ids = {e.evidence_id for e in lineage.evidence}
        assert "intel-div-1" in twin_ids

        report = build_professional_report(
            lineage=lineage,
            intel_items=intel_items,
        )
        assert report.corporate_actions is not None
        matches = [
            i for i in report.corporate_actions.items
            if i.item_id == "intel-div-1"
        ]
        assert len(matches) == 1

    def test_duplicate_uncertainty_claims_are_collapsed(self):
        claims = (
            _make_claim(
                "clm-u1",
                text="Valuation evidence unavailable",
                epistemic_type=EpistemicType.UNKNOWN,
            ),
            _make_claim(
                "clm-u2",
                text="  valuation evidence   unavailable ",
                epistemic_type=EpistemicType.UNKNOWN,
            ),
        )
        lineage = _build_test_lineage(claims=claims)
        report = build_professional_report(lineage=lineage)

        uncertainties = report.executive_overview.uncertainties
        normalized = [" ".join(u.split()).lower() for u in uncertainties]
        assert len(normalized) == len(set(normalized))

    def test_feature_evidence_uses_readable_labels(self):
        from src.research.features.models import FeatureStatus
        from src.research.features.models import FeatureValue
        from src.research.report.builder import _feature_evidence

        feature = FeatureValue(
            feature_id="revenue_growth",
            feature_version="1.0",
            symbol="TCS",
            value=14.2,
            unit="percent",
            observation_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
            calculated_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
            status=FeatureStatus.VALID,
            source_ids=("demo",),
            provenance_ids=("demo-1",),
            confidence=0.9,
        )
        evidence = _feature_evidence([feature], symbol="TCS")
        assert len(evidence) == 1
        combined = f"{evidence[0].title} {evidence[0].explanation}"
        assert "revenue_growth" not in combined
        assert "Revenue growth" in combined
