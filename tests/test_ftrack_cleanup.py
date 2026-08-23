"""
F-TRACK cleanup regressions.

Pins the two remaining F-track debts as closed:

1. Sector sentinel unification — unknown/unavailable sector data
   serializes as null, never a literal "unknown" sentinel; genuine
   sector values pass through unchanged.
2. Error envelope unification — every /api/v1 failure uses the single
   structured error contract
   ({"error": {"code", "message", "details"}}), including 422 request
   validation and routing-level 404/405, while legacy routes keep
   FastAPI's original {"detail": ...} bodies.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_api_error_handlers
from src.api.main import app as real_app
from src.api.query_utils import company_info, company_identity
from src.api.research_router import create_research_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeSectorService:
    """Minimal research service with a configurable sector value."""

    companies = ("TESTCO",)

    def __init__(self, sector):
        self._sector = sector

    def company_name(self, symbol):
        return "Test Company"

    def company_sector(self, symbol):
        return self._sector

    def research_available(self, symbol):
        return True

    def validate_company(self, symbol):
        normalized = symbol.strip().upper()
        if normalized not in self.companies:
            from src.api.errors import UnknownCompanyError

            raise UnknownCompanyError(
                "unknown company",
                details={"symbol": normalized},
            )
        return normalized


def _mini_app(service) -> FastAPI:
    application = FastAPI()
    register_api_error_handlers(application)
    application.include_router(create_research_router(service=service))
    return application


client = TestClient(real_app)


# ---------------------------------------------------------------------------
# 1. Unknown sector => null semantics
# ---------------------------------------------------------------------------


class TestUnknownSectorIsNull:
    @pytest.mark.parametrize("missing_sector", [None, "", "  "])
    def test_company_info_missing_sector_is_null(
        self, missing_sector
    ):
        info = company_info(FakeSectorService(missing_sector), "TESTCO")

        assert info["sector"] is None

    def test_discovery_endpoint_unknown_sector_is_null(self):
        app = _mini_app(FakeSectorService(None))
        mini_client = TestClient(app)

        resp = mini_client.get("/api/v1/companies")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["sector"] is None

    def test_no_sentinel_string_anywhere_in_payload(self):
        app = _mini_app(FakeSectorService(None))
        mini_client = TestClient(app)

        resp = mini_client.get("/api/v1/companies")

        def _strings(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, dict):
                for v in node.values():
                    yield from _strings(v)
            elif isinstance(node, list):
                for v in node:
                    yield from _strings(v)

        assert "unknown" not in set(_strings(resp.json()))

    def test_company_identity_registry_gap_is_null(self):
        identity = company_identity("NOTAREALSYMBOL")

        assert identity["sector"] is None
        assert identity["company_name"] == "NOTAREALSYMBOL"


# ---------------------------------------------------------------------------
# 2. Genuine sector values remain unchanged
# ---------------------------------------------------------------------------


class TestKnownSectorUnchanged:
    def test_company_info_passes_sector_through(self):
        info = company_info(
            FakeSectorService("Information Technology"), "TESTCO"
        )

        assert info["sector"] == "Information Technology"

    def test_discovery_endpoint_passes_sector_through(self):
        app = _mini_app(FakeSectorService("Pharmaceuticals"))
        mini_client = TestClient(app)

        resp = mini_client.get("/api/v1/companies")
        results = resp.json()["results"]

        assert results[0]["sector"] == "Pharmaceuticals"

    def test_registered_company_keeps_real_sector(self):
        resp = client.get("/api/v1/companies")
        results = {
            item["symbol"]: item["sector"]
            for item in resp.json()["results"]
        }

        # Real registry values must be untouched by the unification.
        assert results["TCS"] == "information technology"
        assert results["RELIANCE"] == "energy / conglomerate"


# ---------------------------------------------------------------------------
# 3. V1 validation errors use the structured envelope
# ---------------------------------------------------------------------------


class TestV1ValidationErrors:
    def test_query_constraint_violation_is_structured(self):
        resp = client.get(
            "/api/v1/companies/TCS/price-attribution",
            params={"as_of": "2026-08-22T00:00:00Z", "lookback_days": 400},
        )

        assert resp.status_code == 422
        body = resp.json()
        assert set(body.keys()) == {"error"}
        error = body["error"]
        assert set(error.keys()) == {"code", "message", "details"}
        assert error["code"] == "validation_error"
        assert isinstance(error["details"]["errors"], list)
        assert len(error["details"]["errors"]) >= 1

    def test_validation_error_details_are_json_safe(self):
        resp = client.get(
            "/api/v1/companies/TCS/price-attribution",
            params={"lookback_days": "not-a-number"},
        )

        assert resp.status_code == 422
        entry = resp.json()["error"]["details"]["errors"][0]
        assert isinstance(entry, dict)
        assert {"loc", "msg", "type"} <= set(entry.keys())


# ---------------------------------------------------------------------------
# 4. V1 not-found errors use the structured envelope
# ---------------------------------------------------------------------------


class TestV1NotFoundErrors:
    def test_unknown_company_is_structured(self):
        resp = client.get("/api/v1/companies/NOPE/research")

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "unknown_company"
        assert set(body["error"].keys()) == {"code", "message", "details"}

    def test_unknown_v1_path_is_structured(self):
        resp = client.get("/api/v1/companies/TCS/does-not-exist")

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "not_found"
        assert body["error"]["details"]["status_code"] == 404

    def test_wrong_method_on_v1_route_is_structured(self):
        resp = client.post("/api/v1/companies")

        assert resp.status_code == 405
        body = resp.json()
        assert body["error"]["code"] == "method_not_allowed"


# ---------------------------------------------------------------------------
# 5. Legacy compatibility preserved
# ---------------------------------------------------------------------------


class TestLegacyCompatibility:
    def test_legacy_invalid_horizon_body_unchanged(self):
        resp = client.get("/api/rankings/BOGUS_HORIZON")

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "invalid_horizon"
        assert detail["supported"] == ["INTRADAY", "SWING", "LONG_TERM"]

    def test_unknown_legacy_path_keeps_default_shape(self):
        resp = client.get("/api/definitely-not-a-route")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Not Found"}

    def test_legacy_method_mismatch_keeps_default_shape(self):
        resp = client.post("/health")

        assert resp.status_code == 405
        assert resp.json() == {"detail": "Method Not Allowed"}

    def test_legacy_health_still_works(self):
        resp = client.get("/health")

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Deterministic response shape
# ---------------------------------------------------------------------------


class TestDeterministicShape:
    def test_repeated_v1_failures_identical(self):
        first = client.get("/api/v1/companies/NOPE/research")
        second = client.get("/api/v1/companies/NOPE/research")

        assert first.status_code == second.status_code == 404
        assert first.json() == second.json()

    def test_envelope_key_set_exact(self):
        resp = client.get("/api/v1/companies/NOPE/research")
        body = resp.json()

        assert list(body.keys()) == ["error"]
        assert list(body["error"].keys()) == [
            "code",
            "message",
            "details",
        ]
