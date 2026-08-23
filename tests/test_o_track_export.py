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
