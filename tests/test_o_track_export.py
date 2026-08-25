"""
O-TRACK O11 — deterministic export package tests.

Pins:
- byte-identical packages for identical inputs;
- changed inputs produce different checksums;
- manifest integrity (per-file bytes + sha256, whole-package hash);
- tampering is detected by verify();
- canonical CSV output with sorted headers and rows;
- exports over real recorded artifacts round-trip.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

import pytest

from src.research.export import build_export_package
from src.research.comparison import build_company_comparison
from src.research.discovery_feed import build_discovery_feed

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, 12, tzinfo=TZ)


class _Payload:
    """Minimal pydantic-free JSON payload."""

    def to_dict(self):
        return {"b": 2, "a": 1}


def _simple_payloads():
    return {
        "summary.json": {"zeta": 1, "alpha": [1, 2, 3]},
        "rows.csv": [
            {"symbol": "TCS", "value": "120", "note": None},
            {"symbol": "INFY", "value": "90", "note": "x"},
        ],
    }


class TestDeterminism:
    def test_identical_inputs_byte_identical(self):
        first = build_export_package(_simple_payloads(), as_of=AS_OF)
        second = build_export_package(_simple_payloads(), as_of=AS_OF)

        assert first.files == second.files
        assert first.manifest == second.manifest
        assert first.package_sha256 == second.package_sha256
        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )

    def test_changed_input_changes_checksum(self):
        base = _simple_payloads()
        changed = {
            "summary.json": {"zeta": 2, "alpha": [1, 2, 3]},
            "rows.csv": base["rows.csv"],
        }

        a = build_export_package(base, as_of=AS_OF)
        b = build_export_package(changed, as_of=AS_OF)

        entry_a = next(
            e for e in a.manifest if e.filename == "summary.json"
        )
        entry_b = next(
            e for e in b.manifest if e.filename == "summary.json"
        )
        assert entry_a.sha256 != entry_b.sha256


class TestManifestIntegrity:
    def test_manifest_matches_files(self):
        package = build_export_package(_simple_payloads(), as_of=AS_OF)

        assert package.verify() is True
        assert {e.filename for e in package.manifest} == set(
            package.files
        )

    def test_tampering_detected(self):
        package = build_export_package(_simple_payloads(), as_of=AS_OF)

        tampered = package.model_copy(deep=True)
        tampered.files["summary.json"] = (
            tampered.files["summary.json"] + " "
        )
        assert tampered.verify() is False

    def test_canonical_json_sorted_keys(self):
        package = build_export_package(_simple_payloads(), as_of=AS_OF)
        parsed = json.loads(package.files["summary.json"])

        assert parsed == {"zeta": 1, "alpha": [1, 2, 3]}
        raw = package.files["summary.json"]
        assert raw.index('"alpha"') < raw.index('"zeta"')

    def test_canonical_csv_sorted_rows_and_headers(self):
        package = build_export_package(_simple_payloads(), as_of=AS_OF)
        text = package.files["rows.csv"]

        reader = list(csv.reader(io.StringIO(text)))
        header, rows = reader[0], reader[1:]

        assert header == ["note", "symbol", "value"]
        # Rows sort lexicographically across all fields:
        # empty note ("TCS") precedes "x" ("INFY").
        assert rows[0][header.index("symbol")] == "TCS"
        assert rows[0][header.index("note")] == ""
        assert rows[1][header.index("symbol")] == "INFY"

    def test_rejects_unknown_format_and_empty(self):
        with pytest.raises(ValueError):
            build_export_package({"x.txt": "hi"}, as_of=AS_OF)
        with pytest.raises(ValueError):
            build_export_package({}, as_of=AS_OF)
        with pytest.raises(ValueError):
            build_export_package(_simple_payloads(), as_of=datetime(2026, 8, 10))


@pytest.fixture(scope="module")
def recorded_pair(tmp_path_factory):
    from src.api.recorded_research import RecordedCompanyResearchService

    archive_root = tmp_path_factory.mktemp("o11-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)
    return [
        service.run(symbol, as_of=AS_OF) for symbol in ("TCS", "INFY")
    ]


class TestRecordedExport:
    def test_full_research_export_package(self, recorded_pair):
        feed = build_discovery_feed(recorded_pair, as_of=AS_OF)
        comparison = build_company_comparison(recorded_pair, as_of=AS_OF)

        feed_rows = [
            {
                "item_id": item.item_id,
                "symbol": item.symbol,
                "item_type": item.item_type.value,
                "title": item.title,
            }
            for item in feed.items
        ]

        package = build_export_package(
            {
                "discovery_feed.json": feed,
                "discovery_feed.csv": feed_rows,
                "comparison.json": comparison,
            },
            as_of=AS_OF,
        )

        assert package.verify() is True
        assert len(package.manifest) == 3

        exported_comparison = json.loads(
            package.files["comparison.json"]
        )
        assert exported_comparison["row_count"] == comparison.row_count

    def test_recorded_export_deterministic(self, recorded_pair):
        feed = build_discovery_feed(recorded_pair, as_of=AS_OF)

        first = build_export_package(
            {"discovery_feed.json": feed}, as_of=AS_OF
        )
        second = build_export_package(
            {"discovery_feed.json": feed}, as_of=AS_OF
        )

        assert first.package_sha256 == second.package_sha256


class TestExportManifestExpansion:
    """T1 expansion: evidence / pit / source manifests in exports."""

    @pytest.fixture(scope="class")
    def export_response(self, tmp_path_factory):
        from datetime import timezone as _tz

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.capability_router import (
            create_capability_router,
        )
        from src.api.errors import register_api_error_handlers
        from src.api.recorded_research import (
            RecordedCompanyResearchService,
        )

        archive = tmp_path_factory.mktemp("o11-expansion-archive")
        service = RecordedCompanyResearchService(archive_root=archive)
        app = FastAPI()
        register_api_error_handlers(app)
        app.include_router(
            create_capability_router(service=service)
        )
        client = TestClient(app)
        as_of_iso = "2026-08-10T12:00:00+00:00"
        response = client.get(
            "/api/v1/companies/TCS/export",
            params={"as_of": as_of_iso},
        )
        assert response.status_code == 200
        return response.json()

    def test_package_includes_evidence_pit_and_sources(
        self, export_response
    ):
        filenames = set(export_response["files"])
        assert {
            "research.json",
            "screener_fields.csv",
            "evidence.json",
            "pit.json",
            "sources.csv",
        } <= filenames

    def test_evidence_manifest_carries_lineage(self, export_response):
        import json as _json

        rows = _json.loads(export_response["files"]["evidence.json"])
        assert isinstance(rows, list) and rows
        for row in rows:
            assert row["evidence_id"]
            assert "source_ids" in row
            assert "provenance_ids" in row
            assert "pit_eligible" in row

    def test_pit_manifest_is_point_in_time_block(
        self, export_response
    ):
        import json as _json

        pit = _json.loads(export_response["files"]["pit.json"])
        assert pit["evidence_included"] >= 0
        assert "future_evidence_excluded" in pit
        assert isinstance(pit["pit_checks_passed"], bool)

    def test_sources_manifest_lists_staleness(self, export_response):
        import csv as _csv
        import io as _io

        content = export_response["files"]["sources.csv"]
        if not content:
            return
        reader = _csv.DictReader(_io.StringIO(content))
        for row in reader:
            assert "source_name" in row
            assert "stale" in row

    def test_expanded_package_verifies_and_rebuilds_identically(
        self, tmp_path_factory
    ):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.capability_router import (
            create_capability_router,
        )
        from src.api.errors import register_api_error_handlers
        from src.api.recorded_research import (
            RecordedCompanyResearchService,
        )
        from src.research.export import ExportPackage

        archive = tmp_path_factory.mktemp("o11-rebuild-archive")
        service = RecordedCompanyResearchService(archive_root=archive)
        app = FastAPI()
        register_api_error_handlers(app)
        app.include_router(
            create_capability_router(service=service)
        )
        client = TestClient(app)

        first = client.get(
            "/api/v1/companies/TCS/export",
            params={"as_of": "2026-08-10T12:00:00+00:00"},
        ).json()
        second = client.get(
            "/api/v1/companies/TCS/export",
            params={"as_of": "2026-08-10T12:00:00+00:00"},
        ).json()

        assert ExportPackage.model_validate(first).verify() is True
        assert (
            first["package_sha256"] == second["package_sha256"]
        )
