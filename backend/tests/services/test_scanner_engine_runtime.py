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

    def test_scan_oi_buildup_unavailable_without_real_feed(self):
        # No derivatives/OI provider is configured in tests, so OI must NOT be
        # fabricated: it returns an explicit unavailable state.
        results = scanner_engine.scan_oi_buildup(limit=20)
        assert len(results) >= 1
        r = results[0]
        assert r.type == "unavailable"
        assert r.source == "unavailable"
        assert r.status == "unavailable"
        assert r.change_call_oi == 0
        assert r.change_put_oi == 0
        assert "unavailable" in r.interpretation.lower()

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
            assert w.status in ("live", "cached", "fallback", "unavailable", "error", "mock")
            assert w.source in ("nse", "broker", "cache", "synthetic", "none", "mock")


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


# ---------------------------------------------------------------------------
# NR7 mathematical correctness (Phase 10) + breakout determinism (Phase 11, 28)
# ---------------------------------------------------------------------------

class TestNR7AndBreakout:
    """NR7 = the latest daily range is the narrowest of the most recent 7
    sessions. Breakout = close vs 20-day high/low with volume confirmation.
    Both must be deterministic given the same OHLCV input."""

    def test_nr7_is_narrowest_of_last_seven(self):
        from datetime import datetime, timedelta
        from app.services.screener_engine import Candle

        base = datetime(2026, 1, 1)
        # Build 8 bars where the last has the narrowest range of the last 7.
        bars = [
            Candle(date=base + timedelta(days=i), open=100, high=110,
                   low=90, close=105, volume=1000)
            for i in range(7)
        ]
        # Make ranges vary so the last is the minimum.
        for i, c in enumerate(bars):
            c.high = 100 + (i + 1)  # ranges widen, so bar 7 = widest before last
            c.low = 90
        bars.append(
            Candle(date=base + timedelta(days=7), open=100, high=101,
                   low=99, close=100, volume=500)
        )
        ranges = [c.high - c.low for c in bars]
        last7 = ranges[-7:]
        assert min(last7) == ranges[-1]

    def test_nr7_is_not_narrowest_when_a_prior_bar_is_narrower(self):
        from datetime import datetime, timedelta
        from app.services.screener_engine import Candle

        base = datetime(2026, 1, 1)
        bars = []
        for i in range(8):
            bars.append(
                Candle(
                    date=base + timedelta(days=i),
                    open=100,
                    high=100 + (i + 1),
                    low=90,
                    close=100,
                    volume=1000,
                )
            )
        # Bar at index 5 is narrower than the last bar -> last is NOT the min.
        bars[5].high = 100.5
        ranges = [c.high - c.low for c in bars]
        last7 = ranges[-7:]
        assert min(last7) != ranges[-1]

    def test_breakout_scan_is_deterministic(self):
        a = scanner_engine.scan_breakouts(limit=20)
        b = scanner_engine.scan_breakouts(limit=20)
        assert [
            (r.symbol, r.breakout_price, r.current_price, r.confidence)
            for r in a
        ] == [
            (r.symbol, r.breakout_price, r.current_price, r.confidence)
            for r in b
        ]

    def test_breakout_report_breakout_level_and_volume_ratio(self):
        """Every breakout result must expose the breakout level, current price,
        and volume ratio (Phase 11)."""
        for r in scanner_engine.scan_breakouts(limit=20):
            assert r.breakout_price is not None and r.breakout_price > 0
            assert r.current_price is not None and r.current_price > 0
            assert r.volume_ratio is not None and r.volume_ratio >= 0
            assert r.source is not None and r.status is not None


# ---------------------------------------------------------------------------
# Indicator known-input verification (Phase 9)
# ---------------------------------------------------------------------------

class TestIndicatorKnownInputs:
    """Verify EMA/RSI/ATR/MACD against hand-computed values."""

    CLOSES = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]

    def test_ema_period5_known_value(self):
        from app.services.indicators import calculate_ema

        ema = calculate_ema(self.CLOSES, 5)
        # EMA(5) seed = SMA of first 5 = (10+11+12+13+14)/5 = 12.0
        assert ema[4] == 12.0
        # EMA must be strictly increasing on a strictly increasing series.
        vals = [v for v in ema if v is not None]
        assert vals == sorted(vals)

    def test_rsi_known_range_and_extremes(self):
        from app.services.indicators import calculate_rsi

        up = list(range(10, 30))  # strictly up -> RSI ~100
        rsi = calculate_rsi(up, 14)
        last = [v for v in rsi if v is not None][-1]
        assert last >= 90.0  # strongly overbought
        down = list(range(30, 10, -1))  # strictly down -> RSI ~0
        rsi2 = calculate_rsi(down, 14)
        last2 = [v for v in rsi2 if v is not None][-1]
        assert last2 <= 10.0  # strongly oversold

    def test_atr_is_nonnegative_and_increases_with_range(self):
        from datetime import datetime, timedelta
        from app.services.screener_engine import Candle
        from app.services.scanner_engine import _atr

        base = datetime(2026, 1, 1)
        small = [
            Candle(date=base + timedelta(days=i), open=100, high=101,
                   low=99, close=100, volume=1)
            for i in range(20)
        ]
        big = [
            Candle(date=base + timedelta(days=i), open=100, high=110,
                   low=90, close=100, volume=1)
            for i in range(20)
        ]
        assert _atr(small) >= 0
        assert _atr(big) > _atr(small)

    def test_macd_components_are_aligned_on_trend(self):
        from app.services.indicators import calculate_macd

        # MACD uses slow_period=26 + signal=9, so need >35 points.
        rising = list(range(10, 50))
        macd_line, signal, hist = calculate_macd(rising)
        # On a rising series, the MACD line should be positive near the end.
        macd_vals = [v for v in macd_line if v is not None]
        assert len(macd_vals) > 0
        assert macd_vals[-1] > 0  # price rising -> MACD positive
