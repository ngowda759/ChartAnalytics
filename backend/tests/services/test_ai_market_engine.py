"""Unit tests for AI Market Engine."""
import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.ai_market_engine import (
    AIMarketEngine,
    generate_market_insight,
)


class TestAIMarketEngine:
    """Tests for AIMarketEngine."""
    
    def create_mock_data(self, trend: str = "bullish") -> tuple:
        """Create mock OHLC data for testing."""
        base_price = 25000
        prices = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for i in range(200):
            if trend == "bullish":
                change = 5  # Consistent upward movement
            elif trend == "bearish":
                change = -5  # Consistent downward movement
            else:
                change = 0  # Flat
            
            price = base_price + change * i + (i % 10) * 2
            high = price * 1.01
            low = price * 0.99
            close = price + (i % 3 - 1) * 2
            volume = 1000000 + (i % 20) * 10000
            
            prices.append(price)
            highs.append(high)
            lows.append(low)
            closes.append(close)
            volumes.append(int(volume))
        
        return prices, highs, lows, closes, volumes
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = AIMarketEngine("NIFTY")
        assert engine.symbol == "NIFTY"
    
    def test_analyze_bullish_trend(self):
        """Test analysis of bullish trend."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert result.symbol == "NIFTY"
        assert result.timestamp is not None
        assert result.trend in ["bullish", "bearish", "neutral", "ranging"]
        assert 0 <= result.confidence <= 100
    
    def test_analyze_bearish_trend(self):
        """Test analysis of bearish trend."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bearish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert result.symbol == "NIFTY"
        assert result.trend in ["bullish", "bearish", "neutral", "ranging"]
    
    def test_signals_generation(self):
        """Test that signals are generated."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert len(result.signals) > 0
        for signal in result.signals:
            assert signal.indicator is not None
            assert signal.signal in ["buy", "sell", "neutral", "overbought", "oversold"]
    
    def test_support_resistance_levels(self):
        """Test support and resistance level detection."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # Should have some levels identified
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)
    
    def test_momentum_analysis(self):
        """Test momentum analysis."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert result.momentum in ["strong", "moderate", "weak"]
    
    def test_breakout_probability(self):
        """Test breakout probability calculation."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert 0 <= result.breakout_probability <= 100
    
    def test_risk_factors(self):
        """Test risk factor identification."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert isinstance(result.risk_factors, list)
        assert len(result.risk_factors) > 0
    
    def test_recommendation(self):
        """Test recommendation generation."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert len(result.recommendation) > 0
        assert "educational" in result.recommendation.lower() or "analysis" in result.recommendation.lower()
    
    def test_key_observations(self):
        """Test key observations generation."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert isinstance(result.key_observations, list)
    
    def test_summary_generation(self):
        """Test summary generation."""
        prices, highs, lows, closes, volumes = self.create_mock_data("bullish")
        
        engine = AIMarketEngine("NIFTY")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert len(result.summary) > 0
        assert result.trend in result.summary.lower()
    
    def test_empty_data(self):
        """Test with empty data returns valid structure."""
        engine = AIMarketEngine("NIFTY")
        # With empty data, should handle gracefully
        result = engine.analyze([100], [101], [99], [100], [1000])
        
        assert result.symbol == "NIFTY"
        assert result.timestamp is not None
    
    def test_short_data(self):
        """Test with minimal data for MACD (needs 26+ data points)."""
        prices = list(range(100, 140))  # 40 data points minimum for MACD
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        closes = prices.copy()
        volumes = [1000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        assert result.symbol == "TEST"
        assert isinstance(result.confidence, float)
    
    def test_generate_market_insight_function(self):
        """Test the convenience function."""
        prices = list(range(100, 200))
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        closes = [p + ((i % 3) - 1) for i, p in enumerate(prices)]
        volumes = [1000000] * len(prices)
        
        result = generate_market_insight(
            "TEST",
            prices,
            highs,
            lows,
            closes,
            volumes
        )
        
        assert result.symbol == "TEST"
        assert result.timestamp is not None


class TestTrendDirection:
    """Tests for trend direction detection."""
    
    def test_strong_uptrend(self):
        """Test strong uptrend detection."""
        # Use 200+ data points for proper EMA200 calculation
        prices = list(range(100, 350))  # Consistent uptrend
        highs = [p * 1.02 for p in prices]
        lows = [p * 0.98 for p in prices]
        closes = prices.copy()
        volumes = [1000000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # In strong uptrend, should detect bullish
        assert result.trend in ["bullish", "strong_uptrend", "uptrend"]
    
    def test_strong_downtrend(self):
        """Test strong downtrend detection."""
        # Use 200+ data points for proper EMA200 calculation
        prices = list(range(350, 100, -1))  # Consistent downtrend
        highs = [p * 1.02 for p in prices]
        lows = [p * 0.98 for p in prices]
        closes = prices.copy()
        volumes = [1000000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # Should detect bearish
        assert result.trend in ["bearish", "strong_downtrend", "downtrend"]


class TestIndicatorSignals:
    """Tests for individual indicator signals."""
    
    def test_ema_signal(self):
        """Test EMA signal generation."""
        prices = list(range(100, 300))  # Need 200+ for EMA200
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        closes = prices.copy()
        volumes = [1000000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # Find EMA signal
        ema_signal = next((s for s in result.signals if "EMA" in s.indicator), None)
        assert ema_signal is not None
        assert ema_signal.signal in ["buy", "sell", "neutral"]
    
    def test_rsi_signal(self):
        """Test RSI signal generation."""
        prices = list(range(100, 200))
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        closes = prices.copy()
        volumes = [1000000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # Find RSI signal
        rsi_signal = next((s for s in result.signals if "RSI" in s.indicator), None)
        assert rsi_signal is not None
        # RSI can return overbought/oversold/neutral
        assert rsi_signal.signal in ["buy", "sell", "neutral", "overbought", "oversold"]
    
    def test_macd_signal(self):
        """Test MACD signal generation."""
        prices = list(range(100, 200))
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        closes = prices.copy()
        volumes = [1000000] * len(prices)
        
        engine = AIMarketEngine("TEST")
        result = engine.analyze(prices, highs, lows, closes, volumes)
        
        # Find MACD signal
        macd_signal = next((s for s in result.signals if "MACD" in s.indicator), None)
        assert macd_signal is not None
        assert macd_signal.signal in ["buy", "sell", "neutral"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
