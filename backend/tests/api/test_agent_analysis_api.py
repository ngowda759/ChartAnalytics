"""API tests for Agent Analysis.

Covers the list endpoint (metadata + source), caching, refresh, and the
single-symbol endpoint.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.services import trading_agents


class TestAgentAnalysisEndpoint:
    def test_list_response_has_metadata(self):
        client = TestClient(app)
        r = client.get("/api/v1/agent-analysis/?limit=5")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "synthetic"
        assert body["generated_at"]
        assert body["is_stale"] in (True, False)
        assert "results" in body
        for res in body["results"]:
            assert res["final_decision"]["rating"] in (
                "Buy", "Overweight", "Hold", "Underweight", "Sell"
            )
            assert 0.0 <= res["confidence"] <= 1.0

    def test_caching_avoids_recomputation(self, monkeypatch):
        trading_agents.invalidate_analysis_cache()
        client = TestClient(app)
        r1 = client.get("/api/v1/agent-analysis/?limit=5")
        assert r1.status_code == 200
        first = [r["symbol"] for r in r1.json()["results"]]

        def _boom(*a, **k):
            raise AssertionError("cache miss: pipeline should not re-run")

        # Patch the underlying pipeline function referenced by the cached wrapper.
        monkeypatch.setattr(trading_agents, "_analyze_universe", _boom)
        r2 = client.get("/api/v1/agent-analysis/?limit=5")
        assert r2.status_code == 200
        assert [r["symbol"] for r in r2.json()["results"]] == first

    def test_refresh_bypasses_cache(self, monkeypatch):
        trading_agents.invalidate_analysis_cache()
        client = TestClient(app)
        calls = {"n": 0}
        original = trading_agents._analyze_universe

        def counting(*a, **k):
            calls["n"] += 1
            return original(*a, **k)

        monkeypatch.setattr(trading_agents, "_analyze_universe", counting)
        client.get("/api/v1/agent-analysis/?limit=5")
        client.get("/api/v1/agent-analysis/?limit=5&refresh=true")
        assert calls["n"] >= 2, "refresh must bypass the cache"

    def test_single_symbol(self):
        client = TestClient(app)
        r = client.get("/api/v1/agent-analysis/RELIANCE")
        assert r.status_code == 200
        body = r.json()
        assert body["symbol"] == "RELIANCE"
        assert body["source"] == "synthetic"
