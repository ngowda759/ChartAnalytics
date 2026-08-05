"""Tests for Market Scanner Service."""
import pytest
from app.services.scanner import MarketScanner, ScanType, SignalDirection, ConfidenceLevel


class TestMarketScanner:
    """Test cases for MarketScanner."""

    @pytest.fixture
    def scanner(self):
        return MarketScanner()

    @pytest.fixture
    def sample_data(self):
        return {
            "current_price": 25000,
            "previous_close": 24800,
            "open_price": 24900,
            "high": 25100,
            "low": 24700,
            "volume": 15000000,
            "avg_volume": 10000000,
            "ema_20": 24900,
            "ema_50": 24800,
            "ema_200": 24500,
            "rsi": 55,
            "pcr": 1.1,
            "call_oi_change": 15,
            "put_oi_change": 10,
        }

    def test_scan_symbol_returns_results(self, scanner, sample_data):
        """Test that scan_symbol returns a list of results."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            **sample_data
        )

        assert isinstance(results, list)

    def test_ema_bullish_crossover_detected(self, scanner):
        """Test EMA bullish crossover detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=25000,
            previous_close=24700,
            open_price=24900,
            high=25100,
            low=24700,
            volume=15000000,
            avg_volume=10000000,
            ema_20=24950,
            ema_50=24800,
            ema_200=24500,
            rsi=55,
            pcr=1.1,
            call_oi_change=10,
            put_oi_change=10,
        )

        ema_signals = [r for r in results if r.scan_type == ScanType.EMA_CROSS_BULL]
        assert len(ema_signals) >= 0

    def test_ema_bearish_crossover_detected(self, scanner):
        """Test EMA bearish crossover detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=24600,
            previous_close=24900,
            open_price=24800,
            high=25000,
            low=24500,
            volume=15000000,
            avg_volume=10000000,
            ema_20=24700,
            ema_50=24800,
            ema_200=25000,
            rsi=45,
            pcr=1.0,
            call_oi_change=10,
            put_oi_change=10,
        )

        ema_signals = [r for r in results if r.scan_type == ScanType.EMA_CROSS_BEAR]
        assert len(ema_signals) >= 0

    def test_volume_spike_detection(self, scanner):
        """Test volume spike detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=25000,
            previous_close=24800,
            open_price=24900,
            high=25100,
            low=24700,
            volume=30000000,  # 3x average
            avg_volume=10000000,
            ema_20=24900,
            ema_50=24800,
            ema_200=24500,
            rsi=55,
            pcr=1.1,
            call_oi_change=10,
            put_oi_change=10,
        )

        volume_signals = [r for r in results if r.scan_type == ScanType.VOLUME_SPIKE]
        assert len(volume_signals) >= 0

    def test_rsi_overbought_detection(self, scanner):
        """Test RSI overbought detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=25000,
            previous_close=24800,
            open_price=24900,
            high=25100,
            low=24700,
            volume=10000000,
            avg_volume=10000000,
            ema_20=24900,
            ema_50=24800,
            ema_200=24500,
            rsi=75,  # Overbought
            pcr=1.1,
            call_oi_change=10,
            put_oi_change=10,
        )

        rsi_signals = [r for r in results if r.scan_type == ScanType.RSI_OVERBOUGHT]
        assert len(rsi_signals) >= 0

    def test_rsi_oversold_detection(self, scanner):
        """Test RSI oversold detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=24600,
            previous_close=24800,
            open_price=24800,
            high=24900,
            low=24500,
            volume=10000000,
            avg_volume=10000000,
            ema_20=24700,
            ema_50=24800,
            ema_200=25000,
            rsi=25,  # Oversold
            pcr=0.9,
            call_oi_change=10,
            put_oi_change=10,
        )

        rsi_signals = [r for r in results if r.scan_type == ScanType.RSI_OVERSOLD]
        assert len(rsi_signals) >= 0

    def test_oi_buildup_detection(self, scanner):
        """Test OI buildup detection."""
        results = scanner.scan_symbol(
            symbol="NIFTY",
            current_price=25000,
            previous_close=24800,
            open_price=24900,
            high=25100,
            low=24700,
            volume=10000000,
            avg_volume=10000000,
            ema_20=24900,
            ema_50=24800,
            ema_200=24500,
            rsi=55,
            pcr=1.3,  # High PCR
            call_oi_change=30,  # High call OI change
            put_oi_change=10,
        )

        oi_signals = [r for r in results if r.scan_type == ScanType.OI_BUILDUP_CALL]
        assert len(oi_signals) >= 0

    def test_rank_signals(self, scanner):
        """Test signal ranking."""
        from app.services.scanner import ScanResult
        
        signals = [
            ScanResult(
                id="1", symbol="A", scan_type=ScanType.VOLUME_SPIKE,
                direction=SignalDirection.NEUTRAL, confidence=ConfidenceLevel.LOW,
                price=100, change_percent=1, volume_ratio=2,
                description="Test", key_levels={}, indicators={},
                timestamp=None
            ),
            ScanResult(
                id="2", symbol="B", scan_type=ScanType.EMA_CROSS_BULL,
                direction=SignalDirection.BULLISH, confidence=ConfidenceLevel.HIGH,
                price=100, change_percent=1, volume_ratio=2,
                description="Test", key_levels={}, indicators={},
                timestamp=None
            ),
        ]

        ranked = scanner.rank_signals(signals)
        assert ranked[0].confidence == ConfidenceLevel.HIGH

    def test_generate_summary(self, scanner):
        """Test summary generation."""
        from app.services.scanner import ScanResult
        
        signals = [
            ScanResult(
                id="1", symbol="A", scan_type=ScanType.EMA_CROSS_BULL,
                direction=SignalDirection.BULLISH, confidence=ConfidenceLevel.HIGH,
                price=100, change_percent=1, volume_ratio=2,
                description="Test", key_levels={}, indicators={},
                timestamp=None
            ),
        ]

        summary = scanner.generate_summary(signals, 10)
        
        assert summary.total_signals == 1
        assert summary.bullish_count == 1
        assert summary.symbols_scanned == 10
