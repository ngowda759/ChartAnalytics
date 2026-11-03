from datetime import datetime

from app.services.timesfm_forecast import _build_forecast_payload, _next_weekday


class Candle:
    def __init__(self, date, close):
        self.date = date
        self.close = close


def test_next_weekday_skips_weekends():
    # Friday -> Monday
    assert _next_weekday(datetime(2026, 10, 30), 1) == datetime(2026, 11, 2)


def test_forecast_payload_uses_median_and_outer_quantiles():
    candles = [Candle(datetime(2026, 11, 2), 100.0)]
    forecast_points = [
        {"step": 1, "median": 102.0, "lower": 98.0, "upper": 106.0},
        {"step": 2, "median": 103.0, "lower": 97.0, "upper": 108.0},
    ]

    result = _build_forecast_payload("nifty", candles, "yfinance", 2, forecast_points)

    assert result["symbol"] == "NIFTY"
    assert result["target"] == "close"
    assert result["forecast"][0]["median"] == 102.0
    assert result["forecast"][0]["lower"] == 98.0
    assert result["forecast"][0]["upper"] == 106.0
    assert result["forecast"][0]["timestamp"].startswith("2026-11-03")
    assert result["forecast"][1]["timestamp"].startswith("2026-11-04")


def test_forecast_symbol_uses_real_closes_and_remote_inference(monkeypatch):
    from datetime import timedelta

    from app.core.config import settings
    from app.services import market_data, timesfm_forecast

    candles = [
        Candle(datetime(2026, 1, 1) + timedelta(days=index), 100.0 + index)
        for index in range(60)
    ]
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "symbol": "NIFTY",
                "model_id": settings.TIMESFM_MODEL_ID,
                "forecast": [
                    {"step": 1, "median": 160.0, "lower": 155.0, "upper": 165.0},
                    {"step": 2, "median": 161.0, "lower": 156.0, "upper": 166.0},
                ],
            }

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(
        market_data,
        "get_real_candles",
        lambda symbol, interval, limit: (candles, market_data.SOURCE_YFINANCE),
    )
    monkeypatch.setattr(timesfm_forecast.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "TIMESFM_SERVICE_URL", "https://timesfm.example")
    monkeypatch.setattr(settings, "TIMESFM_SERVICE_TOKEN", "test-token")
    timesfm_forecast.clear_forecast_cache()

    result = timesfm_forecast.forecast_symbol("nifty", horizon=2, context=60, refresh=True)

    assert result["symbol"] == "NIFTY"
    assert result["source"] == market_data.SOURCE_YFINANCE
    assert result["forecast"][0]["median"] == 160.0
    assert calls["url"] == "https://timesfm.example/forecast"
    assert calls["kwargs"]["headers"]["Authorization"] == "Bearer test-token"
    assert len(calls["kwargs"]["json"]["closes"]) == 60
    timesfm_forecast.clear_forecast_cache()


def test_forecast_symbol_rejects_mock_market_data(monkeypatch):
    import pytest

    from app.core.config import settings
    from app.services import market_data, timesfm_forecast

    monkeypatch.setattr(settings, "TIMESFM_SERVICE_URL", "https://timesfm.example")
    monkeypatch.setattr(settings, "TIMESFM_SERVICE_TOKEN", "test-token")
    candles = [Candle(datetime(2026, 1, 1), 100.0)] * 60
    monkeypatch.setattr(
        market_data,
        "get_real_candles",
        lambda symbol, interval, limit: (candles, market_data.SOURCE_MOCK),
    )
    timesfm_forecast.clear_forecast_cache()

    with pytest.raises(timesfm_forecast.TimesFMUnavailable, match="Real daily OHLCV"):
        timesfm_forecast.forecast_symbol("nifty", horizon=2, context=60, refresh=True)


def test_forecast_symbol_requires_remote_service_configuration(monkeypatch):
    import pytest

    from app.core.config import settings
    from app.services import timesfm_forecast

    monkeypatch.setattr(settings, "TIMESFM_SERVICE_URL", "")
    monkeypatch.setattr(settings, "TIMESFM_SERVICE_TOKEN", "")
    with pytest.raises(timesfm_forecast.TimesFMUnavailable, match="not configured"):
        timesfm_forecast.forecast_symbol("nifty", horizon=2, context=60, refresh=True)
