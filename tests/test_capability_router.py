"""
O-TRACK capability exposure router tests.

Pins the API surface over the existing deterministic engines:
- GET /api/v1/discovery (+ /trending)
- GET /api/v1/screener/fields
- POST /api/v1/screener
- GET /api/v1/companies/compare
- GET /api/v1/evidence/search
- GET /api/v1/companies/{symbol}/export

All endpoints must be deterministic, PIT-safe, null-safe, and free of
score/ranking/winner fields.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.capability_router import create_capability_router
from src.api.errors import register_api_error_handlers
from src.api.recorded_research import (
    COMPANY_NAMES,
    RecordedCompanyResearchService,
)

AS_OF = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)
AS_OF_ISO = "2026-08-10T12:00:00+00:00"


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("capability-archive")
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(create_capability_router(service=service))
    return TestClient(app)


def _scan_forbidden(node, forbidden):
    if isinstance(node, dict):
        for key, value in node.items():
            assert key.lower() not in forbidden, key
            _scan_forbidden(value, forbidden)
    elif isinstance(node, list):
        for entry in node:
            _scan_forbidden(entry, forbidden)


# ── Discover ──────────────────────────────────────────────────────


class TestDiscoveryRoute:
    def test_feed_is_deterministic_and_ordered(self, client):
        first = client.get(
            "/api/v1/discovery", params={"as_of": AS_OF_ISO}
        )
        second = client.get(
            "/api/v1/discovery", params={"as_of": AS_OF_ISO}
        )

        assert first.status_code == 200
        assert first.json() == second.json()

        payload = first.json()
        assert payload["as_of"].startswith("2026-08-10T12:00:00")
        assert payload["item_count"] == len(payload["items"])
        # Ordering itself is pinned by the O5 discovery-feed tests;
        # here we only pin that every item carries its identity.
        for item in payload["items"]:
            assert item["item_id"]
            assert item["symbol"]

    def test_items_carry_provenance_and_pit_fields(self, client):
        payload = client.get(
            "/api/v1/discovery", params={"as_of": AS_OF_ISO}
        ).json()

        assert payload["symbols_included"]
        for item in payload["items"]:
            assert item["symbol"]
            assert isinstance(item["pit_eligible"], bool)
            assert "provenance_ids" in item

    def test_item_type_filter(self, client):
        all_payload = client.get(
            "/api/v1/discovery", params={"as_of": AS_OF_ISO}
        ).json()
        target = next(iter(all_payload["type_counts"]))

        filtered = client.get(
            "/api/v1/discovery",
            params={"as_of": AS_OF_ISO, "item_types": target},
        )

        assert filtered.status_code == 200
        body = filtered.json()
        assert body["items"]
        assert {i["item_type"] for i in body["items"]} == {target}

    def test_unknown_item_type_rejected(self, client):
        response = client.get(
            "/api/v1/discovery",
            params={
                "as_of": AS_OF_ISO,
                "item_types": "NOT_A_TYPE",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "malformed_request"

    def test_trending_route(self, client):
        response = client.get(
            "/api/v1/discovery/trending",
            params={"as_of": AS_OF_ISO, "window_days": 30},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["window_days"] == 30
        ranked = payload["ranked"]
        counts = [c["recent_item_count"] for c in ranked]
        assert counts == sorted(counts, reverse=True)


# ── Screener ──────────────────────────────────────────────────────


class TestScreenerRoutes:
    def test_field_catalog_lists_real_fields(self, client):
        response = client.get("/api/v1/screener/fields")
        assert response.status_code == 200

        payload = response.json()
        names = [f["name"] for f in payload["fields"]]
        assert names == sorted(names)
        assert "revenue_latest" in names
        assert payload["available_count"] + payload[
            "unavailable_count"
        ] == len(payload["fields"])

        by_name = {f["name"]: f for f in payload["fields"]}
        unavailable = [
            n for n, f in by_name.items() if not f["available"]
        ]
        for name in unavailable:
            assert by_name[name]["availability_note"]

    def test_screen_run_executes_over_universe(self, client):
        definition = {
            "name": "Profitable companies",
            "description": "Reported profitability above zero.",
            "combine": "AND",
            "groups": [
                {
                    "logic": "AND",
                    "filters": [
                        {
                            "field": "net_profit_latest",
                            "operator": "gt",
                            "value": "0",
                        }
                    ],
                }
            ],
        }

        response = client.post(
            "/api/v1/screener",
            json={
                "definition": definition,
                "columns": [
                    "revenue_latest",
                    "net_profit_latest",
                    "operating_margin_pct",
                    "pit_checks_passed",
                    "evidence_item_count",
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()

        from src.screener.engine import ScreenDefinition

        canonical = ScreenDefinition.from_dict(definition).to_dict()
        assert payload["name"] == "Profitable companies"
        assert payload["definition_hash"]
        assert payload["selected_filters"] == canonical
        assert payload["universe_size"] >= 2
        assert payload["matched_count"] == len(payload["rows"])

        symbols = [row["symbol"] for row in payload["rows"]]
        assert symbols == sorted(symbols)

        for row in payload["rows"]:
            assert row["company_name"] == COMPANY_NAMES[row["symbol"]]
            assert len(row["columns"]) == 5
            for column in row["columns"]:
                assert (column["value"] is None) == (
                    not column["available"]
                )

    def test_screen_run_deterministic(self, client):
        body = {
            "definition": {
                "name": "det",
                "groups": [
                    {
                        "filters": [
                            {
                                "field": "revenue_latest",
                                "operator": "gte",
                                "value": "0",
                            }
                        ]
                    }
                ],
            },
            "columns": ["revenue_latest"],
        }

        first = client.post("/api/v1/screener", json=body).json()
        second = client.post("/api/v1/screener", json=body).json()
        assert first == second

    def test_unknown_filter_field_maps_to_400(self, client):
        response = client.post(
            "/api/v1/screener",
            json={
                "definition": {
                    "name": "bad",
                    "groups": [
                        {
                            "filters": [
                                {
                                    "field": "no_such_field",
                                    "operator": "gt",
                                    "value": "1",
                                }
                            ]
                        }
                    ],
                },
            },
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "malformed_request"
        assert "no_such_field" in body["error"]["message"]

    def test_unknown_column_maps_to_400(self, client):
        response = client.post(
            "/api/v1/screener",
            json={
                "definition": {"name": "cols"},
                "columns": ["no_such_column"],
            },
        )
        assert response.status_code == 400

    def test_no_score_or_ranking_fields_exist(self, client):
        payload = client.get("/api/v1/screener/fields").json()
        catalog = client.post(
            "/api/v1/screener",
            json={
                "definition": {"name": "scan"},
                "columns": ["sector"],
            },
        ).json()

        forbidden = {
            "score",
            "rank",
            "ranking",
            "winner",
            "recommendation",
        }
        _scan_forbidden(payload, forbidden)
        _scan_forbidden(catalog, forbidden)


# ── Compare ───────────────────────────────────────────────────────


class TestCompareRoute:
    def test_comparison_of_two_companies(self, client):
        response = client.get(
            "/api/v1/companies/compare",
            params={
                "symbols": "TCS,INFY",
                "as_of": AS_OF_ISO,
            },
        )

        assert response.status_code == 200
        payload = response.json()

        company_symbols = [
            c["symbol"] for c in payload["companies"]
        ]
        assert set(company_symbols) == {"TCS", "INFY"}
        assert payload["row_count"] > 0
        assert payload["rows"]

    def test_comparison_deterministic(self, client):
        params = {"symbols": "TCS,INFY,HDFCBANK", "as_of": AS_OF_ISO}
        first = client.get("/api/v1/companies/compare", params=params).json()
        second = client.get("/api/v1/companies/compare", params=params).json()
        assert first == second

    def test_requires_two_distinct_companies(self, client):
        response = client.get(
            "/api/v1/companies/compare",
            params={"symbols": "TCS,TCS"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "malformed_request"

    def test_unknown_company_maps_to_404(self, client):
        response = client.get(
            "/api/v1/companies/compare",
            params={"symbols": "TCS,NOTAREALCOMPANY"},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "unknown_company"


# ── Evidence search ───────────────────────────────────────────────


class TestEvidenceSearchRoute:
    def test_search_returns_hits_with_lineage(self, client):
        response = client.get(
            "/api/v1/evidence/search",
            params={"q": "", "as_of": AS_OF_ISO},
        )

        assert response.status_code == 200
        payload = response.json()

        assert payload["hit_count"] == len(payload["items"])
        assert payload["hit_count"] > 0
        assert payload["symbols_searched"]

        for item in payload["items"]:
            assert item["symbol"] in payload["symbols_searched"]
            assert "provenance_ids" in item
            assert "pit_eligible" in item

    def test_search_deterministic(self, client):
        params = {"q": "", "as_of": AS_OF_ISO}
        first = client.get("/api/v1/evidence/search", params=params).json()
        second = client.get("/api/v1/evidence/search", params=params).json()
        assert first == second

    def test_symbol_scope_restricts_results(self, client):
        scoped = client.get(
            "/api/v1/evidence/search",
            params={"q": "", "symbol": "TCS", "as_of": AS_OF_ISO},
        ).json()

        assert scoped["symbols_searched"] == ["TCS"]
        assert scoped["items"]
        assert {i["symbol"] for i in scoped["items"]} == {"TCS"}

    def test_historical_as_of_hides_not_yet_knowable_evidence(self, client):
        from datetime import datetime

        early = client.get(
            "/api/v1/evidence/search",
            params={"q": "", "as_of": "2020-01-01T00:00:00+00:00"},
        )

        if early.status_code == 404:
            # No recorded evidence is knowable that far back — the
            # honest PIT answer is unavailability, not fake emptiness.
            assert (
                early.json()["error"]["code"]
                == "research_data_unavailable"
            )
            return

        assert early.status_code == 200
        cutoff = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
        for item in early.json()["items"]:
            available_at = item.get("available_at")
            assert available_at is not None
            assert datetime.fromisoformat(available_at) <= cutoff

    def test_text_terms_filter_matches(self, client):
        unfiltered = client.get(
            "/api/v1/evidence/search",
            params={"q": "", "symbol": "TCS", "as_of": AS_OF_ISO},
        ).json()

        if not unfiltered["items"]:
            pytest.skip("no TCS evidence recorded")

        needle = unfiltered["items"][0]["title"].split()[0].lower()
        filtered = client.get(
            "/api/v1/evidence/search",
            params={
                "q": needle,
                "symbol": "TCS",
                "as_of": AS_OF_ISO,
            },
        ).json()

        assert filtered["hit_count"] <= unfiltered["hit_count"]


# ── Export ────────────────────────────────────────────────────────


class TestExportRoute:
    def test_export_package_verifies_and_deterministic(self, client):
        first = client.get(
            "/api/v1/companies/TCS/export",
            params={"as_of": AS_OF_ISO},
        )
        second = client.get(
            "/api/v1/companies/TCS/export",
            params={"as_of": AS_OF_ISO},
        )

        assert first.status_code == 200
        assert first.json() == second.json()

        payload = first.json()
        filenames = list(payload["files"])
        assert "research.json" in filenames
        assert "screener_fields.csv" in filenames

        manifest_names = [e["filename"] for e in payload["manifest"]]
        assert manifest_names == sorted(filenames)
        assert len(payload["package_sha256"]) == 64

    def test_export_unknown_company_404(self, client):
        response = client.get("/api/v1/companies/NOPE/export")
        assert response.status_code == 404

    def test_export_contains_existing_contract_shape(self, client):
        payload = client.get(
            "/api/v1/companies/HDFCBANK/export",
            params={"as_of": AS_OF_ISO},
        ).json()

        import json

        research = json.loads(payload["files"]["research.json"])
        # The exported research file IS the existing v1 contract.
        assert research["company"]["symbol"] == "HDFCBANK"
        assert "assessment" in research or "report" in research
