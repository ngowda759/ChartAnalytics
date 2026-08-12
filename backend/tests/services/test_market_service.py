"""Tests for MarketDataService live-NSE index handling."""
import pytest

from app.services import market_service, nse_service


@pytest.fixture
def patch_index_quotes(monkeypatch):
    """Inject deterministic live NSE index dicts without network access."""

    def fake_quotes(limit=50):
        return [
            {
                "indexSymbol": "NIFTY 50",
                "index": "NIFTY 50",
                "last": 24287.15,
                "percentChange": -0.75,
                "variation": -183.4,
                "open": 24470.55,
                "high": 24500.0,
                "low": 24260.0,
                "previousClose": 24470.55,
            },
            {
                "indexSymbol": "INDIA VIX",
                "index": "INDIA VIX",
                "last": 11.95,
                "percentChange": 0.78,
                "variation": 0.09,
                "open": 11.86,
                "high": 12.1,
                "low": 11.8,
                "previousClose": 11.86,
            },
        ]

    monkeypatch.setattr(nse_service, "get_index_quotes", fake_quotes)
    monkeypatch.setattr(
        market_service, "get_index_quotes", fake_quotes, raising=False
    )
    return fake_quotes


class TestGetIndicesLive:
    """Live NSE indices are preferred; provider is the fallback."""

    @pytest.mark.asyncio
    async def test_returns_live_nse_indices(self, patch_index_quotes):
        svc = market_service.MarketDataService()
        indices = await svc.get_indices()

        assert len(indices) == 2
        nifty = indices[0]
        assert nifty.symbol == "NIFTY 50"
        assert nifty.name == "NIFTY 50"
        assert nifty.price == pytest.approx(24287.15)
        assert nifty.change_percent == pytest.approx(-0.75)
        assert nifty.previous_close == pytest.approx(24470.55)
        assert nifty.metadata.get("source") == "nsetools"

    @pytest.mark.asyncio
    async def test_falls_back_when_nse_unreachable(self, monkeypatch):
        # Simulate NSE being down (outside market hours).
        monkeypatch.setattr(
            market_service, "get_index_quotes", lambda limit=50: [], raising=False
        )
        svc = market_service.MarketDataService()
        indices = await svc.get_indices()

        # Mock provider returns the configured major indices.
        assert indices
        symbols = {i.symbol for i in indices}
        assert "NIFTY 50" in symbols
        assert all(i.metadata.get("source") != "nsetools" for i in indices)
