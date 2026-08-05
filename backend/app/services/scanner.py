"""Market Scanner Service - Detects trading opportunities and setups."""
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ScanType(str, Enum):
    BREAKOUT_RESISTANCE = "breakout_resistance"
    BREAKOUT_SUPPORT = "breakout_support"
    EMA_CROSS_BULL = "ema_cross_bullish"
    EMA_CROSS_BEAR = "ema_cross_bearish"
    VOLUME_SPIKE = "volume_spike"
    OI_BUILDUP_CALL = "oi_buildup_call"
    OI_BUILDUP_PUT = "oi_buildup_put"
    LONG_UNWINDING = "long_unwinding"
    SHORT_BUILDING = "short_building"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ScanResult:
    id: str
    symbol: str
    scan_type: ScanType
    direction: SignalDirection
    confidence: ConfidenceLevel
    price: float
    change_percent: float
    volume_ratio: float
    description: str
    key_levels: Dict[str, float]
    indicators: Dict[str, float]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanSummary:
    total_signals: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    high_confidence_count: int
    symbols_scanned: int
    timestamp: datetime


class MarketScanner:
    """Service for scanning markets and detecting trading opportunities."""

    def __init__(self):
        self.logger = structlog.get_logger()

    def scan_symbol(
        self,
        symbol: str,
        current_price: float,
        previous_close: float,
        open_price: float,
        high: float,
        low: float,
        volume: int,
        avg_volume: int,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        rsi: float,
        pcr: float,
        call_oi_change: float,
        put_oi_change: float,
    ) -> List[ScanResult]:
        """Scan a single symbol for trading opportunities."""
        results = []
        self.logger.info("scanning_symbol", symbol=symbol)

        change_percent = ((current_price - previous_close) / previous_close) * 100
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

        # Check for EMA crossovers
        if ema_20 > ema_50 and previous_close < (ema_20 + ema_50) / 2:
            results.append(self._create_ema_bullish_signal(
                symbol, current_price, change_percent, volume_ratio, ema_20, ema_50
            ))
        elif ema_20 < ema_50 and previous_close > (ema_20 + ema_50) / 2:
            results.append(self._create_ema_bearish_signal(
                symbol, current_price, change_percent, volume_ratio, ema_20, ema_50
            ))

        # Check for breakouts
        if current_price > high * 0.998 and volume_ratio > 1.5:
            results.append(self._create_breakout_signal(
                symbol, current_price, change_percent, volume_ratio, high, low, "resistance"
            ))
        elif current_price < low * 1.002 and volume_ratio > 1.5:
            results.append(self._create_breakout_signal(
                symbol, current_price, change_percent, volume_ratio, high, low, "support"
            ))

        # Check for volume spikes
        if volume_ratio > 2.0:
            results.append(self._create_volume_signal(
                symbol, current_price, change_percent, volume_ratio, volume, avg_volume
            ))

        # Check RSI levels
        if rsi > 70:
            results.append(self._create_rsi_signal(
                symbol, current_price, change_percent, volume_ratio, rsi, "overbought"
            ))
        elif rsi < 30:
            results.append(self._create_rsi_signal(
                symbol, current_price, change_percent, volume_ratio, rsi, "oversold"
            ))

        # Check for OI buildup
        if call_oi_change > 20 and pcr > 1.2:
            results.append(self._create_oi_signal(
                symbol, current_price, change_percent, volume_ratio, call_oi_change, put_oi_change, "call"
            ))
        elif put_oi_change > 20 and pcr < 0.8:
            results.append(self._create_oi_signal(
                symbol, current_price, change_percent, volume_ratio, call_oi_change, put_oi_change, "put"
            ))

        # Check for gaps
        gap_percent = ((open_price - previous_close) / previous_close) * 100
        if gap_percent > 3:
            results.append(self._create_gap_signal(
                symbol, current_price, change_percent, volume_ratio, gap_percent, "up"
            ))
        elif gap_percent < -3:
            results.append(self._create_gap_signal(
                symbol, current_price, change_percent, volume_ratio, gap_percent, "down"
            ))

        return results

    def _create_ema_bullish_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        ema_20: float, ema_50: float
    ) -> ScanResult:
        """Create EMA bullish crossover signal."""
        confidence = ConfidenceLevel.HIGH if vol_ratio > 1.5 else ConfidenceLevel.MEDIUM
        
        return ScanResult(
            id=f"{symbol}_ema_bull_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=ScanType.EMA_CROSS_BULL,
            direction=SignalDirection.BULLISH,
            confidence=confidence,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"EMA 20 crossed above EMA 50 - Bullish momentum confirmed",
            key_levels={"ema_20": round(ema_20, 2), "ema_50": round(ema_50, 2)},
            indicators={"ema_20": round(ema_20, 2), "ema_50": round(ema_50, 2)},
            timestamp=datetime.utcnow(),
            metadata={"crossover_type": "bullish"}
        )

    def _create_ema_bearish_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        ema_20: float, ema_50: float
    ) -> ScanResult:
        """Create EMA bearish crossover signal."""
        confidence = ConfidenceLevel.HIGH if vol_ratio > 1.5 else ConfidenceLevel.MEDIUM
        
        return ScanResult(
            id=f"{symbol}_ema_bear_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=ScanType.EMA_CROSS_BEAR,
            direction=SignalDirection.BEARISH,
            confidence=confidence,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"EMA 20 crossed below EMA 50 - Bearish momentum confirmed",
            key_levels={"ema_20": round(ema_20, 2), "ema_50": round(ema_50, 2)},
            indicators={"ema_20": round(ema_20, 2), "ema_50": round(ema_50, 2)},
            timestamp=datetime.utcnow(),
            metadata={"crossover_type": "bearish"}
        )

    def _create_breakout_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        high: float, low: float, breakout_type: str
    ) -> ScanResult:
        """Create breakout signal."""
        confidence = ConfidenceLevel.HIGH if vol_ratio > 2 else ConfidenceLevel.MEDIUM
        scan_type = ScanType.BREAKOUT_RESISTANCE if breakout_type == "resistance" else ScanType.BREAKOUT_SUPPORT
        
        return ScanResult(
            id=f"{symbol}_breakout_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=scan_type,
            direction=SignalDirection.BULLISH if breakout_type == "resistance" else SignalDirection.BEARISH,
            confidence=confidence,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"Price breakout above {breakout_type} on high volume",
            key_levels={"high": round(high, 2), "low": round(low, 2)},
            indicators={"range": round(high - low, 2)},
            timestamp=datetime.utcnow(),
            metadata={"breakout_type": breakout_type}
        )

    def _create_volume_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        volume: int, avg_volume: int
    ) -> ScanResult:
        """Create volume spike signal."""
        confidence = ConfidenceLevel.MEDIUM if vol_ratio < 3 else ConfidenceLevel.HIGH
        
        return ScanResult(
            id=f"{symbol}_volume_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=ScanType.VOLUME_SPIKE,
            direction=SignalDirection.NEUTRAL,
            confidence=confidence,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"Volume spike detected - {vol_ratio:.1f}x average volume",
            key_levels={},
            indicators={"volume": volume, "avg_volume": avg_volume},
            timestamp=datetime.utcnow(),
            metadata={"volume_ratio": round(vol_ratio, 2)}
        )

    def _create_rsi_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        rsi: float, rsi_type: str
    ) -> ScanResult:
        """Create RSI overbought/oversold signal."""
        scan_type = ScanType.RSI_OVERBOUGHT if rsi_type == "overbought" else ScanType.RSI_OVERSOLD
        
        return ScanResult(
            id=f"{symbol}_rsi_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=scan_type,
            direction=SignalDirection.BEARISH if rsi_type == "overbought" else SignalDirection.BULLISH,
            confidence=ConfidenceLevel.MEDIUM,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"RSI at {rsi:.1f} - {rsi_type} zone, potential reversal possible",
            key_levels={},
            indicators={"rsi": round(rsi, 2)},
            timestamp=datetime.utcnow(),
            metadata={"rsi_type": rsi_type}
        )

    def _create_oi_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        call_oi: float, put_oi: float, buildup_type: str
    ) -> ScanResult:
        """Create OI buildup signal."""
        scan_type = ScanType.OI_BUILDUP_CALL if buildup_type == "call" else ScanType.OI_BUILDUP_PUT
        
        return ScanResult(
            id=f"{symbol}_oi_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=scan_type,
            direction=SignalDirection.BULLISH if buildup_type == "call" else SignalDirection.BEARISH,
            confidence=ConfidenceLevel.MEDIUM,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"OI buildup in {buildup_type} options - smart money positioning",
            key_levels={},
            indicators={"call_oi_change": round(call_oi, 2), "put_oi_change": round(put_oi, 2)},
            timestamp=datetime.utcnow(),
            metadata={"buildup_type": buildup_type}
        )

    def _create_gap_signal(
        self, symbol: str, price: float, change: float, vol_ratio: float,
        gap_percent: float, gap_direction: str
    ) -> ScanResult:
        """Create gap signal."""
        scan_type = ScanType.GAP_UP if gap_direction == "up" else ScanType.GAP_DOWN
        
        return ScanResult(
            id=f"{symbol}_gap_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            scan_type=scan_type,
            direction=SignalDirection.BULLISH if gap_direction == "up" else SignalDirection.BEARISH,
            confidence=ConfidenceLevel.HIGH,
            price=price,
            change_percent=change,
            volume_ratio=vol_ratio,
            description=f"Gap {gap_direction} of {abs(gap_percent):.1f}% - monitor for fill or continuation",
            key_levels={},
            indicators={"gap_percent": round(gap_percent, 2)},
            timestamp=datetime.utcnow(),
            metadata={"gap_direction": gap_direction}
        )

    def rank_signals(self, signals: List[ScanResult]) -> List[ScanResult]:
        """Rank signals by confidence and relevance."""
        confidence_weights = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1,
        }

        def signal_score(s: ScanResult) -> tuple:
            direction_score = 2 if s.direction != SignalDirection.NEUTRAL else 0
            return (
                confidence_weights[s.confidence] + direction_score,
                -abs(s.change_percent),  # Prefer smaller changes (more sustainable)
                -s.volume_ratio,  # Prefer lower volume for cleaner signals
            )

        return sorted(signals, key=signal_score, reverse=True)

    def generate_summary(self, signals: List[ScanResult], symbols_scanned: int) -> ScanSummary:
        """Generate summary of scan results."""
        bullish = sum(1 for s in signals if s.direction == SignalDirection.BULLISH)
        bearish = sum(1 for s in signals if s.direction == SignalDirection.BEARISH)
        neutral = sum(1 for s in signals if s.direction == SignalDirection.NEUTRAL)
        high_conf = sum(1 for s in signals if s.confidence == ConfidenceLevel.HIGH)

        return ScanSummary(
            total_signals=len(signals),
            bullish_count=bullish,
            bearish_count=bearish,
            neutral_count=neutral,
            high_confidence_count=high_conf,
            symbols_scanned=symbols_scanned,
            timestamp=datetime.utcnow(),
        )


# Singleton instance
market_scanner = MarketScanner()
