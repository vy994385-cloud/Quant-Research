from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_research():
    response = client.get("/api/research/demo")

    assert response.status_code == 200

    data = response.json()

    assert data["company"]["symbol"] == "DEMO"

    assert "research_score" in data
    assert "intelligence" in data
    assert "financial_trends" in data
    assert "observations" in data
    assert "evidence" in data

    assert data["research_score"]["signal"] in {
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE",
    }

    assert data["research_score"]["total"]

    assert data["intelligence"]["signal_count"] == 3

    assert data["is_trade_signal"] is False