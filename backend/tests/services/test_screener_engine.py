"""Tests for the Chartink-style screener engine and NSE service."""
import pytest

from app.services import screener_engine


class TestScreenerEngine:
    """Tests the NR7 breakout and potential-breakouts formula engine."""

    def test_lists_known_slugs(self):
        slugs = screener_engine.list_screener_slugs()
        assert "copy-morning-scanner-for-buy-nr7-based-breakout-8" in slugs
        assert "potential-breakouts" in slugs

    def test_build_widget_returns_widget_for_each_slug(self):
        for slug in screener_engine.list_screener_slugs():
            widget = screener_engine.build_screener_widget(slug, limit=25)
            assert widget is not None
            assert widget.id == slug
            assert widget.timeframe == "daily"
            assert all(c in widget.columns for c in ("symbol", "change_percent", "ltp"))

    def test_unknown_slug_returns_none(self):
        assert screener_engine.build_screener_widget("does-not-exist") is None

    def test_rows_carry_price_and_volume_when_present(self):
        widget = screener_engine.build_screener_widget("potential-breakouts", limit=25)
        assert widget is not None
        for row in widget.rows:
            assert row.symbol
            assert row.ltp is not None and row.ltp > 0
            assert row.change_percent is not None

    def test_ohlc_history_is_deterministic_within_hour(self):
        candles = screener_engine._generate_ohlc("RELIANCE", 2967.0, days=70)
        assert len(candles) == 70
        # all closes are positive and ordered ascending in time
        assert all(c.close > 0 for c in candles)
        assert candles == sorted(candles, key=lambda c: c.date)
