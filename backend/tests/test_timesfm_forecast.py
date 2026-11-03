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
