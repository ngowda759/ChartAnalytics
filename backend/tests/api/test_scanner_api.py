"""API tests for the NSE scan dashboard endpoint.

Covers success (live), fallback (NSE down), and the response envelope
(success / source / data / warnings).
"""
from fastapi.testclient import TestClient

import app.services.nse_service as nse_service
from app.main import app


def _force_nse_down(monkeypatch):
    nse_service.clear_nse_cache()
    for fn_name in (
        "get_all_indices",
        "get_sectoral_indices",
        "get_top_gainers",
        "get_top_losers",
        "get_52_week_high",
        "get_52_week_low",
        "get_nr7_breakout_candidates",
        "get_potential_breakouts",
    ):
        monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: [])
    monkeypatch.setattr(nse_service, "_get_nse", lambda: None)


def _force_nse_up(monkeypatch):
    nse_service.clear_nse_cache()
    from app.schemas.scanner import ScreenerRow

    live = [ScreenerRow(symbol="LIVE", name="Live", ltp=1.0, change_percent=1.0)]
    for fn_name in (
        "get_all_indices",
        "get_sectoral_indices",
        "get_top_gainers",
        "get_top_losers",
        "get_52_week_high",
        "get_52_week_low",
        "get_nr7_breakout_candidates",
        "get_potential_breakouts",
    ):
        monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: list(live))


class TestNseDashboardEndpoint:
    def test_live_response_envelope(self, monkeypatch):
        _force_nse_up(monkeypatch)
        client = TestClient(app)
        r = client.get("/api/v1/scanner/nse-dashboard")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["source"] == "live"
        assert "data" in body and "widgets" in body["data"]
        assert body["warnings"] == []
        assert body["generated_at"]

    def test_fallback_envelope_when_nse_down(self, monkeypatch):
        _force_nse_down(monkeypatch)
        client = TestClient(app)
        r = client.get("/api/v1/scanner/nse-dashboard")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["source"] == "synthetic_fallback"
        assert body["warnings"], "fallback must list unavailable datasets"
        tagged = [
            w for w in body["data"]["widgets"]
            for row in w["rows"]
            if (row.get("extra") or {}).get("source") == "synthetic_fallback"
        ]
        assert tagged, "fallback rows should carry a source tag"

    def test_endpoint_never_returns_empty_widgets(self, monkeypatch):
        _force_nse_down(monkeypatch)
        client = TestClient(app)
        r = client.get("/api/v1/scanner/nse-dashboard")
        body = r.json()
        for w in body["data"]["widgets"]:
            assert w["rows"], f"widget {w['id']} must not be empty"
