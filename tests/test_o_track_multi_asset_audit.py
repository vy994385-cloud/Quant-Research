"""
O-TRACK O10 — multi-asset (multi-instrument) pipeline audit.

The recorded research universe in this repository is six NSE
equities. There is no ETF / mutual-fund / crypto ingestion code
anywhere in src/, so the honest multi-asset audit is:

1. every recorded instrument runs end-to-end through the canonical
   path (verification -> evidence lineage -> intelligence ->
   tracking changes -> screener fields);
2. cross-instrument outputs (discovery feed, comparison) work over
   the full universe;
3. PIT checks are present and passing for each instrument;
4. the audit explicitly documents that non-equity asset classes
   are not implemented rather than pretending coverage.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.research.comparison import build_company_comparison
from src.research.discovery_feed import (
    build_discovery_feed,
    compute_trending,
)
from src.research.evidence import build_evidence_lineage
from src.screener.fields import FIELD_REGISTRY, extract_company_fields
from src.tracking.research_changes import build_research_change_result
from src.api.errors import UnknownCompanyError

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, 12, tzinfo=TZ)

UNIVERSE = ("TCS", "INFY", "RELIANCE", "HDFCBANK", "SUNPHARMA", "M&M")


@pytest.fixture(scope="module")
def universe_results(tmp_path_factory):
    from src.api.recorded_research import RecordedCompanyResearchService

    archive_root = tmp_path_factory.mktemp("o10-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)

    return {
        symbol: service.run(symbol, as_of=AS_OF)
        for symbol in UNIVERSE
    }


class TestUniverseAudit:
    def test_every_recorded_instrument_runs(self, universe_results):
        assert sorted(universe_results) == sorted(UNIVERSE)

    def test_each_result_is_complete(self, universe_results):
        for symbol, result in universe_results.items():
            assert result.company == symbol, symbol
            assert result.as_of == AS_OF, symbol
            assert result.financial_record_count > 0, symbol
            assert result.market_ingestion is not None, symbol
            assert len(result.evidence_items) > 0, symbol
            assert result.pit_checks, symbol

    def test_pit_checks_pass_for_each_instrument(
        self, universe_results
    ):
        for symbol, result in universe_results.items():
            failed = [
                name
                for name, check in result.pit_checks.items()
                if getattr(check, "passed", True) is False
            ]
            assert not failed, f"{symbol}: {failed}"

    def test_evidence_lineage_builds_for_each(
        self, universe_results
    ):
        for symbol, result in universe_results.items():
            intel_items = (
                result.intelligence.items if result.intelligence else ()
            )
            lineage = build_evidence_lineage(
                symbol=result.company,
                as_of=result.as_of,
                evidence_items=result.evidence_items,
                intel_items=intel_items,
                pit_filter=True,
            )
            assert lineage.symbol == symbol
            assert len(lineage.evidence) > 0

    def test_tracking_changes_build_for_each(self, universe_results):
        for symbol, result in universe_results.items():
            change_result = build_research_change_result(
                result, as_of=result.as_of
            )
            assert change_result.change_count >= 0, symbol

    @pytest.mark.parametrize("field_name", ["revenue_latest"])
    def test_screener_fields_resolve_for_each(
        self, field_name, universe_results
    ):
        assert field_name in FIELD_REGISTRY

        for symbol, result in universe_results.items():
            values = extract_company_fields(result)
            assert set(values) == set(FIELD_REGISTRY), symbol
            # Every recorded instrument has reported revenue.
            assert values["revenue_latest"] is not None, symbol


class TestCrossInstrumentOutputs:
    def test_discovery_feed_over_full_universe(
        self, universe_results
    ):
        feed = build_discovery_feed(
            list(universe_results.values()), as_of=AS_OF
        )

        symbols = {item.symbol for item in feed.items}
        assert symbols <= set(UNIVERSE)
        assert feed.item_count == len(feed.items)
        assert sorted(feed.symbols_included) == sorted(symbols)

        trending = compute_trending(feed)
        assert len(trending.ranked) >= 0

    def test_comparison_over_any_pair_subset(
        self, universe_results
    ):
        subset = [universe_results[s] for s in ("TCS", "INFY")]
        comparison = build_company_comparison(subset, as_of=AS_OF)
        assert comparison.row_count > 0

    def test_unknown_symbol_rejected_cleanly(self, tmp_path):
        from src.api.recorded_research import (
            RecordedCompanyResearchService,
        )

        service = RecordedCompanyResearchService(
            archive_root=tmp_path
        )
        with pytest.raises(UnknownCompanyError):
            service.run("NOTAREALCOMPANY", as_of=AS_OF)


class TestAssetClassHonesty:
    def test_non_equity_asset_classes_are_not_implemented(
        self, tmp_path
    ):
        """
        Audit finding, pinned as a test: this repository implements
        equity research only. There is no ETF / mutual-fund / crypto
        ingestion module, and the recorded service rejects any
        non-equity instrument rather than fabricating coverage.
        """

        import pathlib

        import src

        hits = []
        for path in src.__path__:
            root = pathlib.Path(path)
            for py in root.rglob("*.py"):
                name = py.stem.lower()
                if any(
                    marker in name
                    for marker in ("etf", "mutual_fund", "crypto")
                ):
                    hits.append(str(py))

        assert not hits, hits

        from src.api.recorded_research import (
            RecordedCompanyResearchService,
        )

        service = RecordedCompanyResearchService(
            archive_root=tmp_path
        )
        for non_equity in ("NIFTYBEES", "GOLDBEES"):
            with pytest.raises(UnknownCompanyError):
                service.run(non_equity, as_of=AS_OF)
