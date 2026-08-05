"""Unit tests for technical indicators."""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_vwap,
    get_trend_direction,
    interpret_rsi,
)


class TestEMA:
    """Tests for EMA calculations."""
    
    def test_ema_calculation(self):
        """Test basic EMA calculation."""
        prices = [10, 11, 12, 11, 10, 12, 14, 13, 12, 15]
        result = calculate_ema(prices, 5)
        
        # First 4 values should be None (period - 1)
        assert all(v is None for v in result[:4])
        # Remaining values should be calculated
        assert result[4] is not None
        assert isinstance(result[-1], float)
    
    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        prices = [10, 11, 12]
        result = calculate_ema(prices, 10)
        assert len(result) == len(prices)
        assert all(v is None for v in result)
    
    def test_ema_trend_detection(self):
        """Test EMA-based trend detection."""
        # Uptrend
        prices_up = list(range(100, 120))
        ema_20 = calculate_ema(prices_up, 20)
        ema_50 = calculate_ema(prices_up, 50)
        trend = get_trend_direction(ema_20[-1], ema_50[-1], prices_up[-1] * 0.9, prices_up[-1])
        assert trend == "strong_uptrend"
        
        # Downtrend
        prices_down = list(range(120, 100, -1))
        ema_20 = calculate_ema(prices_down, 20)
        ema_50 = calculate_ema(prices_down, 50)
        trend = get_trend_direction(ema_20[-1], ema_50[-1], prices_down[-1] * 1.1, prices_down[-1])
        assert trend == "strong_downtrend"


class TestRSI:
    """Tests for RSI calculations."""
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Generate oscillating prices
        prices = [100 + 5 * ((i % 10) - 5) for i in range(50)]
        result = calculate_rsi(prices, 14)
        
        assert len(result) == len(prices)
        # Values should be between 0 and 100
        valid_values = [v for v in result if v is not None]
        assert all(0 <= v <= 100 for v in valid_values)
    
    def test_rsi_interpretation(self):
        """Test RSI interpretation."""
        # Overbought
        signal = interpret_rsi(75)
        assert signal.signal == "overbought"
        
        # Oversold
        signal = interpret_rsi(25)
        assert signal.signal == "oversold"
        
        # Neutral
        signal = interpret_rsi(50)
        assert signal.signal == "neutral"
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        prices = [100, 101, 102]
        result = calculate_rsi(prices, 14)
        assert len(result) == len(prices)
        assert all(v is None for v in result)


class TestMACD:
    """Tests for MACD calculations."""
    
    def test_macd_calculation(self):
        """Test MACD calculation."""
        prices = [100 + (i % 20) for i in range(100)]
        macd_line, signal_line, histogram = calculate_macd(prices)
        
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)
        
        # Histogram should be MACD - Signal
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_line[i] is not None:
                assert abs(histogram[i] - (macd_line[i] - signal_line[i])) < 0.001


class TestATR:
    """Tests for ATR calculations."""
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        highs = [105, 110, 108, 112, 115]
        lows = [95, 98, 96, 100, 102]
        closes = [100, 105, 102, 108, 110]
        
        result = calculate_atr(highs, lows, closes, 5)
        
        assert len(result) == len(highs)
        assert all(v >= 0 for v in result if v is not None)
    
    def test_atr_values(self):
        """Test ATR values are reasonable."""
        # Flat market - low ATR
        prices = [100] * 20
        highs = [101] * 20
        lows = [99] * 20
        closes = prices.copy()
        
        atr = calculate_atr(highs, lows, closes, 14)
        valid_atr = [v for v in atr if v is not None]
        
        if valid_atr:
            assert max(valid_atr) < 5  # Should be low for flat market


class TestBollingerBands:
    """Tests for Bollinger Bands calculations."""
    
    def test_bollinger_calculation(self):
        """Test Bollinger Bands calculation."""
        prices = [100 + (i % 10) * 2 for i in range(50)]
        result = calculate_bollinger_bands(prices, 20, 2.0)
        
        assert len(result) == len(prices)
        
        # Check that bands are properly ordered
        for bb in result:
            if bb is not None:
                assert bb.upper > bb.middle > bb.lower
                assert 0 <= bb.percent_b <= 1
                assert bb.bandwidth > 0
    
    def test_bollinger_percent_b(self):
        """Test %B calculation."""
        prices = [100] * 30
        prices.extend([110, 90, 100])  # Above, below, middle
        result = calculate_bollinger_bands(prices, 20, 2.0)
        
        # Last value should be around 0.5 (at middle band)
        if result[-1]:
            assert 0.4 < result[-1].percent_b < 0.6


class TestVWAP:
    """Tests for VWAP calculations."""
    
    def test_vwap_calculation(self):
        """Test VWAP calculation."""
        highs = [105, 110, 108, 112, 115]
        lows = [95, 98, 96, 100, 102]
        closes = [100, 105, 102, 108, 110]
        volumes = [1000, 1500, 1200, 1800, 2000]
        
        result = calculate_vwap(highs, lows, closes, volumes)
        
        assert len(result) == len(highs)
        assert result[0] is not None
        
        # VWAP should be between high and low
        for i, vwap in enumerate(result):
            assert lows[i] <= vwap <= highs[i]


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_prices(self):
        """Test with empty price list."""
        result = calculate_ema([], 14)
        assert result == []
    
    def test_single_price(self):
        """Test with single price."""
        result = calculate_ema([100], 14)
        assert len(result) == 1
        assert result[0] is None
    
    def test_negative_prices(self):
        """Test with negative prices (edge case)."""
        prices = [100, 95, 90, 85, 80]
        result = calculate_ema(prices, 3)
        assert len(result) == len(prices)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
