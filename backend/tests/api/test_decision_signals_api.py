"""API tests for Decision Signals.

Covers the response schema (metadata + source), caching, refresh, and the
404 path for an unknown single signal.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.services import decision_signals


class TestDecisionSignalsEndpoint:
    def test_signals_response_has_metadata(self):
        client = TestClient(app)
        r = client.get("/api/v1/decision-signals/signals?limit=5")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "synthetic"
        assert body["generated_at"]
        assert body["is_stale"] in (True, False)
        for s in body["signals"]:
            assert s["action"] in ("buy", "hold", "avoid")
            assert 0 <= s["score"] <= 100

    def test_caching_avoids_recomputation(self, monkeypatch):
        decision_signals.invalidate_signals_cache()
        client = TestClient(app)
        # First call populates the cache (runs the expensive evaluation).
        r1 = client.get("/api/v1/decision-signals/signals?limit=5")
        assert r1.status_code == 200
        first_ids = [s["id"] for s in r1.json()["signals"]]

        # Patch the expensive inner evaluation; a cache hit must not call it.
        def _boom(*a, **k):
            raise AssertionError("cache miss: evaluate_all should not run")

        monkeypatch.setattr(decision_signals, "evaluate_all", _boom)
        r2 = client.get("/api/v1/decision-signals/signals?limit=5")
        assert r2.status_code == 200
        assert [s["id"] for s in r2.json()["signals"]] == first_ids

    def test_refresh_bypasses_cache(self, monkeypatch):
        decision_signals.invalidate_signals_cache()
        client = TestClient(app)
        calls = {"n": 0}
        original = decision_signals.build_signals

        def counting(*a, **k):
            calls["n"] += 1
            return original(*a, **k)

        monkeypatch.setattr(decision_signals, "build_signals", counting)
        client.get("/api/v1/decision-signals/signals?limit=5")
        client.get("/api/v1/decision-signals/signals?limit=5&refresh=true")
        assert calls["n"] >= 2, "refresh must bypass the cache"

    def test_unknown_signal_returns_404(self):
        client = TestClient(app)
        r = client.get("/api/v1/decision-signals/signals/does-not-exist-xyz")
        assert r.status_code == 404

    def test_strategies_listed(self):
        client = TestClient(app)
        r = client.get("/api/v1/decision-signals/strategies")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert r.json()
