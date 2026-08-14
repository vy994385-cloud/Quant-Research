from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "quant-research-api"


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


def test_stock_search_empty_query_returns_demo():
    response = client.get("/api/stocks/search")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["symbol"] == "DEMO"
    assert data["results"][0]["research_ready"] is True


def test_stock_search_demo():
    response = client.get("/api/stocks/search?q=DEMO")

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "DEMO"
    assert data["count"] == 1
    assert data["results"][0]["symbol"] == "DEMO"
    assert data["results"][0]["company_name"] == "Demo Industries"


def test_demo_stock():
    response = client.get("/api/stocks/DEMO")

    assert response.status_code == 200

    data = response.json()

    assert data["company"]["symbol"] == "DEMO"
    assert "research_score" in data
    assert "intelligence" in data
    assert "evidence" in data


def test_demo_stock_research():
    response = client.get("/api/stocks/DEMO/research")

    assert response.status_code == 200

    data = response.json()

    assert data["company"]["symbol"] == "DEMO"
    assert "research_score" in data
    assert "rankings" in data
    assert "intelligence" in data
    assert "observations" in data
    assert "evidence" in data


def test_demo_stock_rankings():
    response = client.get("/api/stocks/DEMO/rankings")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "DEMO"
    assert data["company_name"] == "Demo Industries"

    rankings = data["rankings"]

    assert set(rankings) == {
        "intraday",
        "swing",
        "long_term",
    }

    assert rankings["intraday"]["horizon"] == "INTRADAY"
    assert rankings["swing"]["horizon"] == "SWING"
    assert rankings["long_term"]["horizon"] == "LONG_TERM"


def test_demo_intraday_ranking():
    response = client.get("/api/rankings/INTRADAY")

    assert response.status_code == 200

    data = response.json()

    assert data["horizon"] == "INTRADAY"
    assert data["count"] >= 1

    demo = next(
        item
        for item in data["results"]
        if item["symbol"] == "DEMO"
    )

    assert demo["score"]
    assert demo["signal"]
    assert demo["confidence"]


def test_demo_swing_ranking():
    response = client.get("/api/rankings/SWING")

    assert response.status_code == 200

    data = response.json()

    assert data["horizon"] == "SWING"
    assert data["count"] >= 1


def test_demo_long_term_ranking():
    response = client.get("/api/rankings/LONG_TERM")

    assert response.status_code == 200

    data = response.json()

    assert data["horizon"] == "LONG_TERM"
    assert data["count"] >= 1


def test_ranking_horizon_aliases():
    for alias, expected in {
        "INTRA": "INTRADAY",
        "LONG-TERM": "LONG_TERM",
        "LONGTERM": "LONG_TERM",
    }.items():
        response = client.get(
            f"/api/rankings/{alias}"
        )

        assert response.status_code == 200
        assert response.json()["horizon"] == expected


def test_invalid_ranking_horizon():
    response = client.get("/api/rankings/INVALID")

    assert response.status_code == 400

    data = response.json()

    assert data["detail"]["error"] == "invalid_horizon"
    assert data["detail"]["supported"] == [
        "INTRADAY",
        "SWING",
        "LONG_TERM",
    ]


def test_demo_stock_research_and_stock_match():
    research = client.get(
        "/api/stocks/DEMO/research"
    )

    stock = client.get(
        "/api/stocks/DEMO"
    )

    assert research.status_code == 200
    assert stock.status_code == 200

    research_data = research.json()
    stock_data = stock.json()

    assert (
        research_data["company"]["symbol"]
        == stock_data["company"]["symbol"]
    )

    assert (
        research_data["research_score"]["total"]
        == stock_data["research_score"]["total"]
    )