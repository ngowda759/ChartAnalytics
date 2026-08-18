"""Tests for the real scanner failure modes fixed in this change.

Covers:
- Scanner endpoints are deterministic (no random market values).
- Scanner results are computed from real indicators over seeded OHLC.
- NSE cache serves stale real data when the live source fails.
- NSE partial failure: one dataset down does not break the dashboard.
- Options endpoints return 503 (not random data) when no provider is live.
- Per-widget status/source provenance.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import nse_service, scanner_engine
from app.schemas.scanner import ScanType


# ---------------------------------------------------------------------------
# Deterministic scanner engine
# ---------------------------------------------------------------------------

class TestScannerDeterminism:
    def test_scan_market_is_deterministic(self):
        a = scanner_engine.scan_market(min_confidence=0.0, limit=50)
        b = scanner_engine.scan_market(min_confidence=0.0, limit=50)
        assert [(r.symbol, r.scan_type, r.confidence, r.price) for r in a] == [
            (r.symbol, r.scan_type, r.confidence, r.price) for r in b
        ]

    def test_scan_market_confidence_is_bounded(self):
        results = scanner_engine.scan_market(min_confidence=0.0, limit=100)
        for r in results:
            assert 0.0 <= r.confidence <= 100.0
            assert r.price > 0

    def test_scan_market_respects_min_confidence(self):
        results = scanner_engine.scan_market(min_confidence=80.0, limit=50)
        assert all(r.confidence >= 80.0 for r in results)

    def test_scan_breakouts_have_real_levels(self):
        results = scanner_engine.scan_breakouts(limit=20)
        for r in results:
            assert r.breakout_price > 0
            assert r.current_price > 0
            assert r.atr >= 0
            assert 0.0 <= r.confidence <= 100.0

    def test_scan_oi_buildup_is_labelled_proxy(self):
        results = scanner_engine.scan_oi_buildup(limit=20)
        for r in results:
            assert "proxy" in r.interpretation.lower()

    def test_no_random_in_production_scanner(self):
        """The scanner engine module must not import or use random for values."""
        import inspect

        src = inspect.getsource(scanner_engine)
        assert "random.uniform" not in src
        assert "random.choice" not in src
        assert "random.randint" not in src


# ---------------------------------------------------------------------------
# Scanner API endpoints (non-random)
# ---------------------------------------------------------------------------

class TestScannerApi:
    def test_scan_market_endpoint_deterministic(self):
        client = TestClient(app)
        a = client.get("/api/v1/scanner/?min_confidence=0&limit=20").json()
        b = client.get("/api/v1/scanner/?min_confidence=0&limit=20").json()
        # Same seeded hour -> identical results.
        assert [(r["symbol"], r["scan_type"], r["confidence"]) for r in a] == [
            (r["symbol"], r["scan_type"], r["confidence"]) for r in b
        ]

    def test_scan_summary_endpoint_works(self):
        client = TestClient(app)
        r = client.get("/api/v1/scanner/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["total_results"] >= 0
        assert "by_type" in body

    def test_breakouts_endpoint_non_random(self):
        client = TestClient(app)
        a = client.get("/api/v1/scanner/breakouts").json()
        b = client.get("/api/v1/scanner/breakouts").json()
        assert [(r["symbol"], r["breakout_price"]) for r in a] == [
            (r["symbol"], r["breakout_price"]) for r in b
        ]


# ---------------------------------------------------------------------------
# NSE cache + partial failure
# ---------------------------------------------------------------------------

class TestNseCacheAndPartialFailure:
    def test_cache_serves_stale_data_when_live_fails(self, monkeypatch):
        from app.schemas.scanner import ScreenerRow

        nse_service.clear_nse_cache()
        # Live rows carry the OHLC extra fields the NR7/PBO derivation needs so
        # the derived widgets can be recomputed from the cached rows.
        live = [ScreenerRow(
            symbol="LIVE", name="Live", ltp=100.0, change_percent=1.0, volume=5000,
            extra={"open": 99.0, "high": 100.5, "low": 98.8, "prev_close": 99.0,
                   "new_52wh": 100.5, "prev_52wh": 95.0},
        )]

        # First call: live succeeds -> cached.
        for fn_name in (
            "get_all_indices", "get_sectoral_indices", "get_top_gainers",
            "get_top_losers", "get_52_week_high", "get_52_week_low",
        ):
            monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: list(live))
        widgets, source, _ = asyncio.run(nse_service.build_nse_dashboard())
        assert source == "live"

        # Second call: live fails -> cached real data served (stale).
        for fn_name in (
            "get_all_indices", "get_sectoral_indices", "get_top_gainers",
            "get_top_losers", "get_52_week_high", "get_52_week_low",
        ):
            monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: [])
        widgets2, source2, _ = asyncio.run(nse_service.build_nse_dashboard())
        assert source2 == "cached"
        # Cached rows are the real LIVE rows, not synthetic fallback.
        gainers = next(w for w in widgets2 if w.id == "top_gainers")
        assert gainers.rows[0].symbol == "LIVE"
        assert gainers.status == "cached"

    def test_partial_failure_does_not_break_dashboard(self, monkeypatch):
        from app.schemas.scanner import ScreenerRow

        nse_service.clear_nse_cache()
        live = [ScreenerRow(symbol="LIVE", name="Live", ltp=1.0, change_percent=1.0)]
        # Gainers works, losers fails.
        monkeypatch.setattr(nse_service, "get_top_gainers", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_top_losers", lambda *a, **k: [])
        monkeypatch.setattr(nse_service, "get_all_indices", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_sectoral_indices", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_52_week_high", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_52_week_low", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_nr7_breakout_candidates", lambda *a, **k: list(live))
        monkeypatch.setattr(nse_service, "get_potential_breakouts", lambda *a, **k: list(live))

        widgets, source, _ = asyncio.run(nse_service.build_nse_dashboard())
        gainers = next(w for w in widgets if w.id == "top_gainers")
        losers = next(w for w in widgets if w.id == "top_losers")
        assert gainers.status == "live"
        assert gainers.rows[0].symbol == "LIVE"
        # Losers fell back but the widget still has rows.
        assert losers.rows, "losers widget must not be empty even on failure"
        assert source == "synthetic_fallback"

    def test_widget_status_source_fields_present(self, monkeypatch):
        nse_service.clear_nse_cache()
        for fn_name in (
            "get_all_indices", "get_sectoral_indices", "get_top_gainers",
            "get_top_losers", "get_52_week_high", "get_52_week_low",
        ):
            monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: [])
        widgets, _, _ = asyncio.run(nse_service.build_nse_dashboard())
        for w in widgets:
            assert w.status in ("live", "cached", "fallback", "unavailable", "error")
            assert w.source in ("nse", "broker", "cache", "synthetic", "none")


# ---------------------------------------------------------------------------
# Options: no fake data when provider unavailable
# ---------------------------------------------------------------------------

class TestOptionsUnavailable:
    def test_chain_returns_503_when_no_real_data(self, monkeypatch):
        # Force the market service to return no option chain analysis.
        from app.services import market_service

        async def no_analysis(self, symbol, expiry=None):
            return None

        monkeypatch.setattr(
            market_service.MarketDataService, "analyze_option_chain", no_analysis
        )
        client = TestClient(app)
        r = client.get("/api/v1/options/chain/NIFTY")
        assert r.status_code == 503
        assert "unavailable" in r.json()["detail"].lower()

    def test_pcr_returns_503_when_no_real_data(self, monkeypatch):
        from app.services import market_service

        async def no_analysis(self, symbol, expiry=None):
            return None

        monkeypatch.setattr(
            market_service.MarketDataService, "analyze_option_chain", no_analysis
        )
        client = TestClient(app)
        r = client.get("/api/v1/options/pcr/NIFTY")
        assert r.status_code == 503

    def test_max_pain_returns_503_when_no_real_data(self, monkeypatch):
        from app.services import market_service

        async def no_analysis(self, symbol, expiry=None):
            return None

        monkeypatch.setattr(
            market_service.MarketDataService, "analyze_option_chain", no_analysis
        )
        client = TestClient(app)
        r = client.get("/api/v1/options/max-pain/NIFTY")
        assert r.status_code == 503
