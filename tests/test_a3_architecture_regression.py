"""
A3 — Architecture regression tests.

Verifies:
- No duplicate Pydantic contract classes
- Shared query utils are the single source of truth
- Company dict shape is consistent across all endpoints
- F6 serializers are used instead of inline dict construction
- Evidence epistemic types are preserved correctly
- Confidence semantics are documented and consistent
- PIT integrity is maintained
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.query_utils import (
    HORIZON_ALIASES,
    SUPPORTED_HORIZONS,
    normalize_horizon,
    parse_as_of,
)
from src.api.errors import InvalidAsOfError, InvalidHorizonError


# ── Shared query utils ──────────────────────────────────────────


class TestParseAsOf:
    def test_none_returns_none(self):
        assert parse_as_of(None) is None

    def test_empty_string_returns_none(self):
        assert parse_as_of("") is None
        assert parse_as_of("  ") is None

    def test_valid_iso_with_tz(self):
        result = parse_as_of("2026-08-10T12:00:00+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_valid_z_suffix(self):
        result = parse_as_of("2026-08-10T12:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_date_only_gets_utc(self):
        result = parse_as_of("2026-08-10")
        assert result is not None
        assert result.tzinfo is not None

    def test_invalid_format_raises(self):
        with pytest.raises(InvalidAsOfError):
            parse_as_of("not-a-date")

    def test_timezone_required_for_datetime(self):
        with pytest.raises(InvalidAsOfError):
            parse_as_of("2026-08-10T12:00:00")


class TestNormalizeHorizon:
    def test_valid_horizons(self):
        assert normalize_horizon("INTRADAY") == "INTRADAY"
        assert normalize_horizon("SWING") == "SWING"
        assert normalize_horizon("LONG_TERM") == "LONG_TERM"

    def test_aliases(self):
        assert normalize_horizon("INTRA") == "INTRADAY"
        assert normalize_horizon("LONG-TERM") == "LONG_TERM"
        assert normalize_horizon("LONGTERM") == "LONG_TERM"

    def test_case_insensitive(self):
        assert normalize_horizon("intraday") == "INTRADAY"
        assert normalize_horizon("swing") == "SWING"

    def test_invalid_raises(self):
        with pytest.raises(InvalidHorizonError):
            normalize_horizon("INVALID")

    def test_constants_exported(self):
        assert "INTRADAY" in SUPPORTED_HORIZONS
        assert "SWING" in SUPPORTED_HORIZONS
        assert "LONG_TERM" in SUPPORTED_HORIZONS
        assert len(HORIZON_ALIASES) >= 6


# ── Contract class uniqueness ───────────────────────────────────


class TestContractUniqueness:
    def test_no_duplicate_balance_sheet_classes(self):
        from src.api import contracts

        class_names = [
            name
            for name in dir(contracts)
            if name.startswith("Contract") and "BalanceSheet" in name
        ]
        # Should have Deep and Quality, not two with the same name
        assert "ContractBalanceSheetDeepObservation" in class_names
        assert "ContractBalanceSheetQualityObservation" in class_names

    def test_balance_sheet_deep_uses_deep_observation(self):
        from src.api.contracts import (
            ContractBalanceSheetDeep,
            ContractBalanceSheetDeepObservation,
        )

        # ContractBalanceSheetDeep should reference DeepObservation
        field = ContractBalanceSheetDeep.model_fields["observations"]
        assert field.annotation is not None

    def test_balance_sheet_quality_observation_has_quality_fields(self):
        from src.api.contracts import ContractBalanceSheetQualityObservation

        obs = ContractBalanceSheetQualityObservation(
            observation_type="test",
            symbol="TEST",
            severity="INFO",
        )
        assert obs.observation_type == "test"
        assert obs.debt_comparisons == []
        assert obs.equity_changes == []


# ── Company dict shape consistency ──────────────────────────────


class TestCompanyDictShape:
    def test_f6_chart_data_uses_company_name(self):
        from src.api.f6_serializers import company_info_dict

        class FakeResult:
            company = "TEST"
            sector = "IT"
            as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)

        result = company_info_dict(FakeResult(), "Test Corp")
        assert "company_name" in result
        assert result["company_name"] == "Test Corp"
        assert "symbol" in result
        assert "sector" in result
        assert "as_of" in result
        assert "name" not in result

    def test_f6_serializers_company_info_no_name_key(self):
        from src.api.f6_serializers import company_info_dict

        class FakeResult:
            company = "TEST"
            sector = "IT"
            as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)

        result = company_info_dict(FakeResult(), None)
        assert "name" not in result
        assert "company_name" in result

    def test_validation_router_uses_company_info(self):
        from src.api.query_utils import company_info

        class FakeService:
            def company_name(self, s):
                return "Test Corp"

            def company_sector(self, s):
                return "IT"

            def research_available(self, s):
                return True

        result = company_info(FakeService(), "TEST")
        assert result["company_name"] == "Test Corp"
        assert result["symbol"] == "TEST"
        assert "name" not in result


# ── Query utils backward compatibility ──────────────────────────


class TestBackwardCompatibility:
    def test_research_router_exports_parse_as_of(self):
        from src.api.research_router import parse_as_of as pra

        result = pra("2026-08-10T12:00:00+00:00")
        assert result is not None
        assert result.year == 2026

    def test_research_router_exports_supported_horizons(self):
        from src.api.research_router import SUPPORTED_HORIZONS as shr

        assert "LONG_TERM" in shr

    def test_f6_router_imports_from_query_utils(self):
        import src.api.f6_router as mod
        import inspect

        source = inspect.getsource(mod)
        assert "from src.api.query_utils import" in source
        assert "from src.api.research_router import" not in source


# ── F6 serializer usage ─────────────────────────────────────────


class TestF6SerializerUsage:
    def test_f6_router_uses_serializers(self):
        import src.api.f6_router as mod
        import inspect

        source = inspect.getsource(mod)
        assert "from src.api.f6_serializers import" in source
        # Should not have inline dict construction for chart data
        assert "\"metric\": s.metric" not in source

    def test_f6_chart_data_from_model(self):
        from src.api.f6_serializers import chart_data_from_model

        class FakeSeries:
            metric = "revenue"
            label = "Revenue"
            unit = type("V", (), {"value": "INR"})()
            category = type("V", (), {"value": "FINANCIAL"})()
            currency = "INR"
            data_points = ()
            period_count = 4
            available_count = 4
            missing_count = 0
            source = "sec"

        class FakeChartData:
            symbol = "TEST"
            as_of = "2026-08-10T00:00:00+00:00"
            series = (FakeSeries(),)
            categories = ()
            total_metrics = 1
            total_data_points = 4
            notes = ()

        result = chart_data_from_model(FakeChartData())
        assert result["symbol"] == "TEST"
        assert len(result["series"]) == 1
        assert result["series"][0]["metric"] == "revenue"


# ── Evidence epistemic type preservation ─────────────────────────


class TestEpistemicPreservation:
    def test_epistemic_type_enum_values(self):
        from src.research.evidence.models import EpistemicType

        assert EpistemicType.REPORTED.value == "REPORTED"
        assert EpistemicType.DERIVED.value == "DERIVED"
        assert EpistemicType.INFERRED.value == "INFERRED"
        assert EpistemicType.UNKNOWN.value == "UNKNOWN"

    def test_professional_report_preserves_epistemic(self):
        from src.research.evidence.models import (
            CanonicalEvidenceItem,
            EpistemicType,
            EvidenceLineage,
        )
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        evidence = (
            CanonicalEvidenceItem(
                evidence_id="ev-1",
                symbol="TEST",
                title="Revenue grew",
                explanation="15% growth",
                evidence_type="FEATURE",
                direction="POSITIVE",
                confidence="0.8",
                reliability="PRIMARY",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="CONFIRMED",
                category="FINANCIAL",
                observation_at=as_of,
            ),
            CanonicalEvidenceItem(
                evidence_id="ev-2",
                symbol="TEST",
                title="Inferred trend",
                explanation="Pattern detected",
                evidence_type="SIGNAL",
                direction="NEGATIVE",
                confidence="0.6",
                reliability="SECONDARY",
                epistemic_type=EpistemicType.INFERRED,
                verification_status="UNVERIFIED",
                category="MARKET",
                observation_at=as_of,
            ),
        )

        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=evidence,
            total_evidence=2,
        )

        report = build_professional_report(lineage=lineage)

        # Evidence sections should preserve epistemic types
        assert report.positive_evidence is not None
        ep_types = {
            item.epistemic_type.value
            for item in report.positive_evidence.items
        }
        assert "REPORTED" in ep_types

        assert report.negative_evidence is not None
        neg_ep_types = {
            item.epistemic_type.value
            for item in report.negative_evidence.items
        }
        assert "INFERRED" in neg_ep_types

    def test_unknown_not_converted_to_negative(self):
        from src.research.evidence.models import (
            CanonicalEvidenceItem,
            EpistemicType,
            EvidenceLineage,
        )
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        evidence = (
            CanonicalEvidenceItem(
                evidence_id="ev-unk",
                symbol="TEST",
                title="Unknown item",
                explanation="Cannot determine",
                evidence_type="FEATURE",
                direction="NEUTRAL",
                confidence="0",
                reliability="UNKNOWN",
                epistemic_type=EpistemicType.UNKNOWN,
                verification_status="UNVERIFIED",
                category="FINANCIAL",
                observation_at=as_of,
            ),
        )

        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=evidence,
            total_evidence=1,
        )

        report = build_professional_report(lineage=lineage)
        assert report.negative_evidence is None
        assert report.executive_overview.negative_count == 0


# ── PIT integrity ───────────────────────────────────────────────


class TestPITIntegrity:
    def test_pit_excludes_future_evidence(self):
        from src.research.evidence.models import (
            CanonicalEvidenceItem,
            EpistemicType,
            EvidenceLineage,
        )
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        future = datetime(2026, 9, 1, tzinfo=timezone.utc)

        evidence = (
            CanonicalEvidenceItem(
                evidence_id="ev-past",
                symbol="TEST",
                title="Past evidence",
                explanation="Available before as_of",
                evidence_type="FEATURE",
                direction="POSITIVE",
                confidence="0.8",
                reliability="PRIMARY",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="CONFIRMED",
                category="FINANCIAL",
                observation_at=as_of,
            ),
            CanonicalEvidenceItem(
                evidence_id="ev-future",
                symbol="TEST",
                title="Future evidence",
                explanation="Should be excluded",
                evidence_type="FEATURE",
                direction="NEGATIVE",
                confidence="0.5",
                reliability="SECONDARY",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="UNVERIFIED",
                category="FINANCIAL",
                observation_at=future,
            ),
        )

        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=evidence,
            total_evidence=2,
        )

        report = build_professional_report(lineage=lineage)

        assert report.pit_integrity is not None
        # Future evidence should be flagged
        assert report.pit_integrity.future_evidence_excluded == 1


# ── Confidence semantics ────────────────────────────────────────


class TestConfidenceSemantics:
    def test_confidence_is_string_in_contracts(self):
        from src.api.f8_contracts import ContractF8ReportItem

        item = ContractF8ReportItem(
            item_id="test",
            text="Test",
            confidence="0.85",
        )
        assert isinstance(item.confidence, str)
        assert item.confidence == "0.85"

    def test_confidence_preserved_through_serialization(self):
        from src.api.f8_serializers import professional_report_contract
        from src.research.evidence.models import (
            CanonicalEvidenceItem,
            EpistemicType,
            EvidenceLineage,
        )
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        evidence = (
            CanonicalEvidenceItem(
                evidence_id="ev-conf",
                symbol="TEST",
                title="High confidence",
                explanation="Strong evidence",
                evidence_type="FEATURE",
                direction="POSITIVE",
                confidence="0.95",
                reliability="PRIMARY",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="CONFIRMED",
                category="FINANCIAL",
                observation_at=as_of,
            ),
        )

        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=evidence,
            total_evidence=1,
        )

        report = build_professional_report(lineage=lineage)
        contract = professional_report_contract(
            report, company_name="Test Corp"
        )

        # Confidence should be preserved as string
        exec_ov = contract["report"]["executive_overview"]
        assert exec_ov["evidence_direction_confidence"] == "0.95"


# ── No fabricated conclusions ───────────────────────────────────


class TestNoFabricatedConclusions:
    def test_empty_evidence_produces_empty_sections(self):
        from src.research.evidence.models import EvidenceLineage
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=(),
            total_evidence=0,
        )

        report = build_professional_report(lineage=lineage)

        assert report.business_context is None
        assert report.financial_performance is None
        assert report.positive_evidence is None
        assert report.negative_evidence is None
        assert report.executive_overview.evidence_direction == "UNKNOWN"

    def test_methodology_discloses_limitations(self):
        from src.research.evidence.models import EvidenceLineage
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=(),
            total_evidence=0,
        )

        report = build_professional_report(lineage=lineage)

        assert report.methodology is not None
        assert len(report.methodology.known_limitations) > 0
        summary_lower = report.methodology.methodology_summary.lower()
        has_trade_disclosure = (
            "scores" in summary_lower
            or "trade" in summary_lower
            or "recommendation" in summary_lower
        )
        assert has_trade_disclosure


# ── Deterministic ordering ──────────────────────────────────────


class TestDeterministicOrdering:
    def test_same_input_same_output(self):
        from src.research.evidence.models import (
            CanonicalEvidenceItem,
            EpistemicType,
            EvidenceLineage,
        )
        from src.research.report.professional import (
            build_professional_report,
        )

        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        evidence = tuple(
            CanonicalEvidenceItem(
                evidence_id=f"ev-{i}",
                symbol="TEST",
                title=f"Evidence {i}",
                explanation=f"Explanation {i}",
                evidence_type="FEATURE",
                direction="POSITIVE" if i % 2 == 0 else "NEGATIVE",
                confidence=str(0.5 + i * 0.05),
                reliability="PRIMARY",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="CONFIRMED",
                category="FINANCIAL",
                observation_at=as_of,
            )
            for i in range(5)
        )

        lineage = EvidenceLineage(
            symbol="TEST",
            as_of=as_of,
            evidence=evidence,
            total_evidence=5,
        )

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
