"""Tests for Chart Analysis Service."""
import pytest
from app.services.chart_analysis import (
    ChartAnalysisService,
    PatternType,
    PatternDirection,
    PatternConfidence,
)


class TestChartAnalysisService:
    """Test cases for ChartAnalysisService."""

    @pytest.fixture
    def service(self):
        return ChartAnalysisService()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for testing."""
        import random
        base = 25000
        highs = [base + random.uniform(100, 300) for _ in range(60)]
        lows = [base - random.uniform(100, 300) for _ in range(60)]
        closes = [base + random.uniform(-100, 100) for _ in range(60)]
        volumes = [random.randint(1000000, 5000000) for _ in range(60)]
        timestamps = [f"2024-01-{i+1:02d}T09:15:00" for i in range(60)]
        return highs, lows, closes, volumes, timestamps

    def test_analyze_chart_returns_result(self, service, sample_data):
        """Test that analyze_chart returns a valid result."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result is not None
        assert result.trend in PatternDirection
        assert result.momentum is not None
        assert result.volatility is not None
        assert result.confidence >= 0
        assert len(result.educational_notes) > 0

    def test_support_resistance_levels(self, service, sample_data):
        """Test that support and resistance levels are identified."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.levels is not None
        assert len(result.levels.support) <= 5
        assert len(result.levels.resistance) <= 5
        assert result.levels.pivot > 0
        assert result.levels.s1 > 0
        assert result.levels.r1 > 0

    def test_pattern_detection(self, service, sample_data):
        """Test that patterns are detected."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.patterns is not None
        assert isinstance(result.patterns, list)

    def test_trend_detection_bullish(self, service):
        """Test bullish trend detection."""
        closes = [25000 + i * 50 for i in range(60)]
        highs = [c + 100 for c in closes]
        lows = [c - 100 for c in closes]
        volumes = [1000000] * 60
        timestamps = [f"2024-01-{i+1:02d}T09:15:00" for i in range(60)]

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.trend == PatternDirection.BULLISH

    def test_trend_detection_bearish(self, service):
        """Test bearish trend detection."""
        closes = [25000 - i * 50 for i in range(60)]
        highs = [c + 100 for c in closes]
        lows = [c - 100 for c in closes]
        volumes = [1000000] * 60
        timestamps = [f"2024-01-{i+1:02d}T09:15:00" for i in range(60)]

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.trend == PatternDirection.BEARISH

    def test_momentum_calculation(self, service, sample_data):
        """Test momentum calculation."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        valid_momentum = [
            "strong_bullish",
            "bullish",
            "neutral",
            "bearish",
            "strong_bearish",
            "overbought",
            "oversold",
        ]
        assert result.momentum in valid_momentum

    def test_volatility_calculation(self, service, sample_data):
        """Test volatility calculation."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        valid_volatility = ["high", "normal", "low"]
        assert result.volatility in valid_volatility

    def test_volume_analysis(self, service, sample_data):
        """Test volume profile analysis."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        valid_profiles = [
            "high_volume",
            "normal_volume",
            "low_volume",
            "insufficient_data",
        ]
        assert result.volume_profile in valid_profiles

    def test_bias_determination(self, service, sample_data):
        """Test market bias determination."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.bias in PatternDirection
        assert 0 <= result.confidence <= 100

    def test_educational_notes_generation(self, service, sample_data):
        """Test that educational notes are generated."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.educational_notes is not None
        assert len(result.educational_notes) > 0
        # Last note should be about risk management
        assert "risk" in result.educational_notes[-1].lower()

    def test_summary_generation(self, service, sample_data):
        """Test that summary is generated."""
        highs, lows, closes, volumes, timestamps = sample_data

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.summary is not None
        assert "NIFTY" in result.summary
        assert len(result.summary) > 0

    def test_insufficient_data_handling(self, service):
        """Test handling of insufficient data."""
        closes = [25000, 25100, 25050]
        highs = [c + 50 for c in closes]
        lows = [c - 50 for c in closes]
        volumes = [1000000, 1000000, 1000000]
        timestamps = ["2024-01-01T09:15:00"] * 3

        result = service.analyze_chart(
            symbol="NIFTY",
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )

        assert result.trend == PatternDirection.NEUTRAL
        assert result.confidence >= 0
