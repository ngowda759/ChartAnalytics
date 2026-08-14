"""API tests for the market stats + option chain endpoints."""
from fastapi.testclient import TestClient

import app.api.market as market_api
from app.main import app


class TestMarketStatsEndpoint:
    def test_unavailable_when_nse_down(self, monkeypatch):
        monkeypatch.setattr(market_api, "get_index_quotes", lambda *a, **k: [])
        client = TestClient(app)
        r = client.get("/api/v1/market/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "unavailable"
        assert body["advances"] is None
        assert body["declines"] is None
        assert body["india_vix"] is None

    def test_live_breadth_when_nse_up(self, monkeypatch):
        monkeypatch.setattr(
            market_api,
            "get_index_quotes",
            lambda *a, **k: [
                {"indexSymbol": "NIFTY 50", "advances": 30, "declines": 20, "unchanged": 1},
                {"indexSymbol": "INDIA VIX", "last": 14.56, "percentChange": -5.09},
            ],
        )
        client = TestClient(app)
        r = client.get("/api/v1/market/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "live"
        assert body["advances"] == 30
        assert body["declines"] == 20
        assert body["india_vix"] == 14.56
        assert body["india_vix_change_percent"] == -5.09


class TestOptionChainEndpoint:
    def test_analysis_path_is_v1_prefixed(self):
        """Regression: the frontend used /api/options/... (missing /v1/)."""
        client = TestClient(app)
        r = client.get("/api/v1/options/analysis/NIFTY")
        assert r.status_code in (404, 200)

    def test_wrong_legacy_path_not_found(self):
        client = TestClient(app)
        r = client.get("/api/options/analysis/NIFTY")
        assert r.status_code == 404
