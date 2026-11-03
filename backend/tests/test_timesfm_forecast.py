from datetime import datetime

import numpy as np

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
    point = np.array([102.0, 103.0])
    quantiles = np.zeros((2, 10), dtype=float)
    quantiles[:, 1] = [98.0, 97.0]
    quantiles[:, 9] = [106.0, 108.0]

    result = _build_forecast_payload("nifty", candles, "yfinance", 2, point, quantiles)

    assert result["symbol"] == "NIFTY"
    assert result["target"] == "close"
    assert result["forecast"][0]["median"] == 102.0
    assert result["forecast"][0]["lower"] == 98.0
    assert result["forecast"][0]["upper"] == 106.0
    assert result["forecast"][0]["timestamp"].startswith("2026-11-03")
    assert result["forecast"][1]["timestamp"].startswith("2026-11-04")


def test_forecast_symbol_uses_real_closes_and_model(monkeypatch):
    from datetime import timedelta

    from app.services import market_data, timesfm_forecast

    candles = [
        Candle(datetime(2026, 1, 1) + timedelta(days=index), 100.0 + index)
        for index in range(60)
    ]
    calls = {}

    class FakeModel:
        def forecast(self, horizon, inputs):
            calls["horizon"] = horizon
            calls["inputs"] = inputs
            points = np.asarray([[160.0, 161.0]], dtype=np.float32)
            quantiles = np.zeros((1, horizon, 10), dtype=np.float32)
            quantiles[:, :, 1] = 155.0
            quantiles[:, :, 9] = 165.0
            return points[:, :horizon], quantiles

    monkeypatch.setattr(
        market_data,
        "get_real_candles",
        lambda symbol, interval, limit: (candles, market_data.SOURCE_YFINANCE),
    )
    monkeypatch.setattr(timesfm_forecast, "_load_model", lambda: FakeModel())
    timesfm_forecast.clear_forecast_cache()

    result = timesfm_forecast.forecast_symbol("nifty", horizon=2, context=60, refresh=True)

    assert result["symbol"] == "NIFTY"
    assert result["source"] == market_data.SOURCE_YFINANCE
    assert result["forecast"][0]["median"] == 160.0
    assert calls["horizon"] == 2
    assert len(calls["inputs"][0]) == 60
    timesfm_forecast.clear_forecast_cache()


def test_forecast_symbol_rejects_mock_market_data(monkeypatch):
    from app.services import market_data, timesfm_forecast

    candles = [Candle(datetime(2026, 1, 1), 100.0)] * 60
    monkeypatch.setattr(
        market_data,
        "get_real_candles",
        lambda symbol, interval, limit: (candles, market_data.SOURCE_MOCK),
    )
    monkeypatch.setattr(
        timesfm_forecast,
        "_load_model",
        lambda: (_ for _ in ()).throw(AssertionError("model must not load for mock data")),
    )
    timesfm_forecast.clear_forecast_cache()

    import pytest

    with pytest.raises(timesfm_forecast.TimesFMUnavailable, match="Real daily OHLCV"):
        timesfm_forecast.forecast_symbol("nifty", horizon=2, context=60, refresh=True)
