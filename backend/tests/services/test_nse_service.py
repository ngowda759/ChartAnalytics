"""Tests for the NSE-backed dashboard service.

Covers the regression where the scan dashboard rendered empty sets when the
live NSE source returned nothing (market closed, NSE blocking the request, or
nsetools missing). The dashboard must always have a non-empty row set for every
widget so the UI never shows "No data for table".
"""
import asyncio

import pytest

from app.services import nse_service


def _force_nse_down(monkeypatch):
    """Make every live NSE getter return [] (simulates NSE being unreachable)."""
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
    # Singleton must report unavailable too.
    monkeypatch.setattr(nse_service, "_get_nse", lambda: None)


def _build(monkeypatch=None):
    """Run the async dashboard builder and return (widgets, source, warnings)."""
    return asyncio.run(nse_service.build_nse_dashboard())


def _row_source(row):
    return (row.extra or {}).get("source")


class TestBuildNseDashboardFallback:
    """The dashboard is never empty, even when live NSE returns nothing."""

    @pytest.mark.parametrize("down", [False, True])
    def test_every_widget_has_rows(self, monkeypatch, down):
        if down:
            _force_nse_down(monkeypatch)

        widgets, source, warnings = _build()

        assert len(widgets) == 8, "expected the full widget set"
        for w in widgets:
            assert w.rows, f"widget '{w.id}' rendered empty"
            assert w.columns
            assert w.title
        if down:
            assert source == "synthetic_fallback"
            assert warnings, "warnings should list unavailable datasets"
        else:
            assert source == "live"

    def test_fallback_rows_are_tagged_when_nse_down(self, monkeypatch):
        _force_nse_down(monkeypatch)

        widgets, source, _ = _build()
        tagged = sum(
            1 for w in widgets for r in w.rows if _row_source(r) == "synthetic_fallback"
        )
        assert tagged > 0, "fallback rows should carry a source tag"
        assert source == "synthetic_fallback"

    def test_live_rows_are_not_tagged_when_nse_up(self, monkeypatch):
        # Live getters return a single dummy row each; none should be tagged.
        def live_rows(limit=20, **kw):
            from app.schemas.scanner import ScreenerRow

            return [ScreenerRow(symbol="LIVE", name="Live", ltp=1.0, change_percent=1.0)]

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
            monkeypatch.setattr(nse_service, fn_name, live_rows)

        widgets, source, _ = _build()
        tagged = sum(
            1 for w in widgets for r in w.rows if _row_source(r) == "synthetic_fallback"
        )
        assert tagged == 0, "live rows must not carry the fallback tag"
        assert source == "live"

    def test_sectoral_winners_falls_back_when_none_positive(self, monkeypatch):
        # Live sectoral indices all negative -> sectoral_winners must still fill.
        from app.schemas.scanner import ScreenerRow

        monkeypatch.setattr(
            nse_service,
            "get_sectoral_indices",
            lambda limit=50: [ScreenerRow(symbol="X", name="X", ltp=1.0, change_percent=-2.0)],
        )
        # Other live getters down so their fallbacks kick in too.
        for fn_name in (
            "get_all_indices",
            "get_top_gainers",
            "get_top_losers",
            "get_52_week_high",
            "get_52_week_low",
            "get_nr7_breakout_candidates",
            "get_potential_breakouts",
        ):
            monkeypatch.setattr(nse_service, fn_name, lambda *a, **k: [])

        widgets, _, _ = _build()
        sw = next(w for w in widgets if w.id == "sectoral_winners")
        assert sw.rows, "sectoral_winners should fall back when none are positive"

    def test_widget_ids_are_stable(self, monkeypatch):
        _force_nse_down(monkeypatch)
        widgets, _, _ = _build()
        ids = [w.id for w in widgets]
        assert ids == [
            "indices_momentum",
            "sectoral_winners",
            "top_gainers",
            "top_losers",
            "fifty_two_week_high",
            "fifty_two_week_low",
            "copy-morning-scanner-for-buy-nr7-based-breakout-8",
            "potential-breakouts",
        ]

    def test_schema_accepts_string_metadata_in_extra(self):
        """Regression: extra was typed Dict[str, float] but stores source strings."""
        from app.schemas.scanner import ScreenerRow

        row = ScreenerRow(
            symbol="X",
            extra={"source": "synthetic_fallback", "open": 123.0},
        )
        assert row.extra["source"] == "synthetic_fallback"
        assert row.extra["open"] == 123.0