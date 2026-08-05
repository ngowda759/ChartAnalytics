"""Chart Analysis Service - Pattern detection and trading level identification."""
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class PatternType(str, Enum):
    # Continuation Patterns
    TRIANGLE_ASCENDING = "ascending_triangle"
    TRIANGLE_DESCENDING = "descending_triangle"
    TRIANGLE_SYMMETRIC = "symmetric_triangle"
    FLAG_BULL = "bull_flag"
    FLAG_BEAR = "bear_flag"
    PENNANT_BULL = "bull_pennant"
    PENNANT_BEAR = "bear_pennant"

    # Reversal Patterns
    HEAD_SHOULDERS = "head_and_shoulders"
    HEAD_SHOULDERS_INVERSE = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"

    # Candlestick Patterns
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    ENGULFING_BULL = "bullish_engulfing"
    ENGULFING_BEAR = "bearish_engulfing"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"

    # Other Patterns
    WEDGE_RISING = "rising_wedge"
    WEDGE_FALLING = "falling_wedge"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"
    RANGE = "range_bound"


class PatternDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TradingLevels:
    support: List[float]
    resistance: List[float]
    pivot: float
    s1: float
    r1: float
    s2: float
    r2: float


@dataclass
class Pattern:
    pattern_type: PatternType
    direction: PatternDirection
    confidence: PatternConfidence
    description: str
    start_index: int
    end_index: int


@dataclass
class TradeSetup:
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    risk_reward_1: float
    risk_reward_2: float
    risk_reward_3: float


@dataclass
class ChartAnalysisResult:
    patterns: List[Pattern]
    levels: TradingLevels
    trend: PatternDirection
    momentum: str
    volatility: str
    volume_profile: str
    bias: PatternDirection
    confidence: float
    setup: Optional[TradeSetup]
    summary: str
    educational_notes: List[str]


class ChartAnalysisService:
    """Service for analyzing charts and detecting patterns."""

    def analyze_chart(
        self,
        symbol: str,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[int],
        timestamps: List[str],
    ) -> ChartAnalysisResult:
        """Analyze chart and detect patterns."""
        logger.info("analyzing_chart", symbol=symbol)

        # Identify support and resistance levels
        levels = self._find_support_resistance(highs, lows, closes)

        # Detect patterns
        patterns = self._detect_patterns(highs, lows, closes)

        # Determine trend
        trend = self._determine_trend(closes)

        # Calculate momentum
        momentum = self._calculate_momentum(closes)

        # Calculate volatility
        volatility = self._calculate_volatility(closes)

        # Analyze volume
        volume_profile = self._analyze_volume(volumes)

        # Determine bias
        bias = self._determine_bias(trend, momentum, patterns)

        # Calculate confidence
        confidence = self._calculate_confidence(patterns, trend, volume_profile)

        # Generate trade setup if patterns found
        setup = self._generate_setup(levels, trend, patterns[-1] if patterns else None) if patterns else None

        # Generate summary
        summary = self._generate_summary(symbol, trend, patterns, bias)

        # Educational notes
        educational_notes = self._generate_educational_notes(patterns, trend)

        return ChartAnalysisResult(
            patterns=patterns,
            levels=levels,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume_profile=volume_profile,
            bias=bias,
            confidence=confidence,
            setup=setup,
            summary=summary,
            educational_notes=educational_notes,
        )

    def _find_support_resistance(
        self, highs: List[float], lows: List[float], closes: List[float]
    ) -> TradingLevels:
        """Find key support and resistance levels."""
        all_prices = highs + lows + closes
        price_range = max(all_prices) - min(all_prices)
        tolerance = price_range * 0.01

        # Simple pivot point calculation
        pivot = (max(highs[-20:]) + min(lows[-20:]) + closes[-1]) / 3
        r1 = 2 * pivot - min(lows[-20:])
        s1 = 2 * pivot - max(highs[-20:])
        r2 = pivot + (max(highs[-20:]) - min(lows[-20:]))
        s2 = pivot - (max(highs[-20:]) - min(lows[-20:]))

        # Find local peaks and troughs for S/R
        support = []
        resistance = []

        for i in range(5, len(lows) - 5):
            if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
                if not any(abs(lows[i] - s) < tolerance for s in support):
                    support.append(round(lows[i], 2))
            if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
                if not any(abs(highs[i] - r) < tolerance for r in resistance):
                    resistance.append(round(highs[i], 2))

        support = sorted(support)[:5]
        resistance = sorted(resistance, reverse=True)[:5]

        return TradingLevels(
            support=support,
            resistance=resistance,
            pivot=round(pivot, 2),
            s1=round(s1, 2),
            r1=round(r1, 2),
            s2=round(s2, 2),
            r2=round(r2, 2),
        )

    def _detect_patterns(
        self, highs: List[float], lows: List[float], closes: List[float]
    ) -> List[Pattern]:
        """Detect chart patterns."""
        patterns = []

        if len(closes) < 50:
            return patterns

        # Detect double bottom (bullish reversal)
        if self._is_double_bottom(lows):
            patterns.append(Pattern(
                pattern_type=PatternType.DOUBLE_BOTTOM,
                direction=PatternDirection.BULLISH,
                confidence=PatternConfidence.MEDIUM,
                description="A double bottom pattern suggests a potential bullish reversal from the support level.",
                start_index=len(closes) - 30,
                end_index=len(closes),
            ))

        # Detect double top (bearish reversal)
        if self._is_double_top(highs):
            patterns.append(Pattern(
                pattern_type=PatternType.DOUBLE_TOP,
                direction=PatternDirection.BEARISH,
                confidence=PatternConfidence.MEDIUM,
                description="A double top pattern suggests a potential bearish reversal from the resistance level.",
                start_index=len(closes) - 30,
                end_index=len(closes),
            ))

        # Detect ascending triangle
        if self._is_ascending_triangle(highs, lows):
            patterns.append(Pattern(
                pattern_type=PatternType.TRIANGLE_ASCENDING,
                direction=PatternDirection.BULLISH,
                confidence=PatternConfidence.MEDIUM,
                description="Ascending triangle with flat resistance and rising support - typically bullish continuation.",
                start_index=len(closes) - 40,
                end_index=len(closes),
            ))

        # Detect descending triangle
        if self._is_descending_triangle(highs, lows):
            patterns.append(Pattern(
                pattern_type=PatternType.TRIANGLE_DESCENDING,
                direction=PatternDirection.BEARISH,
                confidence=PatternConfidence.MEDIUM,
                description="Descending triangle with falling support and flat resistance - typically bearish continuation.",
                start_index=len(closes) - 40,
                end_index=len(closes),
            ))

        # Detect bull flag
        if self._is_bull_flag(closes):
            patterns.append(Pattern(
                pattern_type=PatternType.FLAG_BULL,
                direction=PatternDirection.BULLISH,
                confidence=PatternConfidence.HIGH,
                description="Bull flag pattern indicates continuation of bullish trend after a brief consolidation.",
                start_index=len(closes) - 25,
                end_index=len(closes),
            ))

        return patterns

    def _is_double_bottom(self, lows: List[float]) -> bool:
        """Detect double bottom pattern."""
        if len(lows) < 40:
            return False
        recent = lows[-40:]
        min1 = min(recent[:20])
        min2 = min(recent[20:])
        idx1 = recent[:20].index(min1)
        idx2 = recent[20:].index(min2) + 20
        if abs(min1 - min2) / min1 < 0.02:
            if abs(idx1 - idx2) >= 15:
                return True
        return False

    def _is_double_top(self, highs: List[float]) -> bool:
        """Detect double top pattern."""
        if len(highs) < 40:
            return False
        recent = highs[-40:]
        max1 = max(recent[:20])
        max2 = max(recent[20:])
        idx1 = recent[:20].index(max1)
        idx2 = recent[20:].index(max2) + 20
        if abs(max1 - max2) / max1 < 0.02:
            if abs(idx1 - idx2) >= 15:
                return True
        return False

    def _is_ascending_triangle(self, highs: List[float], lows: List[float]) -> bool:
        """Detect ascending triangle pattern."""
        if len(highs) < 40:
            return False
        recent_highs = highs[-40:-20]
        recent_lows = lows[-20:]
        high_std = max(recent_highs) - min(recent_highs)
        low_trend = recent_lows[-1] - recent_lows[0]
        if high_std < abs(low_trend) * 0.3 and low_trend > 0:
            return True
        return False

    def _is_descending_triangle(self, highs: List[float], lows: List[float]) -> bool:
        """Detect descending triangle pattern."""
        if len(highs) < 40:
            return False
        recent_highs = highs[-20:]
        recent_lows = lows[-40:-20]
        low_std = max(recent_lows) - min(recent_lows)
        high_trend = recent_highs[-1] - recent_highs[0]
        if low_std < abs(high_trend) * 0.3 and high_trend < 0:
            return True
        return False

    def _is_bull_flag(self, closes: List[float]) -> bool:
        """Detect bull flag pattern."""
        if len(closes) < 30:
            return False
        recent = closes[-30:]
        if recent[-1] > recent[0] * 1.05:
            mid_point = len(recent) // 2
            consolidation = recent[mid_point:]
            if max(consolidation) - min(consolidation) < (max(recent) - min(recent)) * 0.3:
                return True
        return False

    def _determine_trend(self, closes: List[float]) -> PatternDirection:
        """Determine current trend direction."""
        if len(closes) < 50:
            return PatternDirection.NEUTRAL

        # Simple moving average crossover
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50

        if sma20 > sma50 * 1.02:
            return PatternDirection.BULLISH
        elif sma20 < sma50 * 0.98:
            return PatternDirection.BEARISH
        return PatternDirection.NEUTRAL

    def _calculate_momentum(self, closes: List[float]) -> str:
        """Calculate momentum indicator."""
        if len(closes) < 14:
            return "neutral"

        gains = []
        losses = []
        for i in range(1, min(15, len(closes))):
            diff = closes[-i] - closes[-i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / 14 if gains else 0
        avg_loss = sum(losses) / 14 if losses else 0

        if avg_loss == 0:
            return "strong_bullish"
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        if rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        elif rsi > 55:
            return "bullish"
        elif rsi < 45:
            return "bearish"
        return "neutral"

    def _calculate_volatility(self, closes: List[float]) -> str:
        """Calculate volatility level."""
        if len(closes) < 20:
            return "normal"

        returns = []
        for i in range(1, min(21, len(closes))):
            returns.append((closes[-i] - closes[-i - 1]) / closes[-i - 1])

        volatility = sum(abs(r) for r in returns) / len(returns)

        if volatility > 0.03:
            return "high"
        elif volatility < 0.01:
            return "low"
        return "normal"

    def _analyze_volume(self, volumes: List[int]) -> str:
        """Analyze volume profile."""
        if len(volumes) < 20:
            return "insufficient_data"

        avg_volume = sum(volumes[-20:]) / 20
        recent_volume = sum(volumes[-5:]) / 5

        if recent_volume > avg_volume * 1.5:
            return "high_volume"
        elif recent_volume < avg_volume * 0.5:
            return "low_volume"
        return "normal_volume"

    def _determine_bias(
        self,
        trend: PatternDirection,
        momentum: str,
        patterns: List[Pattern],
    ) -> PatternDirection:
        """Determine overall market bias."""
        bullish_count = 0
        bearish_count = 0

        if trend == PatternDirection.BULLISH:
            bullish_count += 2
        elif trend == PatternDirection.BEARISH:
            bearish_count += 2

        if "bullish" in momentum or "overbought" in momentum:
            bullish_count += 1
        elif "bearish" in momentum or "oversold" in momentum:
            bearish_count += 1

        for pattern in patterns:
            if pattern.direction == PatternDirection.BULLISH:
                bullish_count += 1
            elif pattern.direction == PatternDirection.BEARISH:
                bearish_count += 1

        if bullish_count > bearish_count + 1:
            return PatternDirection.BULLISH
        elif bearish_count > bullish_count + 1:
            return PatternDirection.BEARISH
        return PatternDirection.NEUTRAL

    def _calculate_confidence(
        self, patterns: List[Pattern], trend: PatternDirection, volume_profile: str
    ) -> float:
        """Calculate confidence score for analysis."""
        confidence = 50.0

        # Pattern count bonus
        confidence += min(len(patterns) * 10, 20)

        # Pattern confidence bonus
        for pattern in patterns:
            if pattern.confidence == PatternConfidence.HIGH:
                confidence += 10
            elif pattern.confidence == PatternConfidence.MEDIUM:
                confidence += 5

        # Volume confirmation bonus
        if volume_profile == "high_volume":
            confidence += 10

        return min(confidence, 95)

    def _generate_setup(
        self,
        levels: TradingLevels,
        trend: PatternDirection,
        latest_pattern: Optional[Pattern],
    ) -> Optional[TradeSetup]:
        """Generate trade setup with entry, stop loss, and targets."""
        if not levels.resistance or not levels.support:
            return None

        if trend == PatternDirection.BULLISH:
            entry = levels.resistance[0] if levels.resistance else levels.pivot
            stop_loss = levels.support[0] if levels.support else entry * 0.98
            target_1 = levels.resistance[1] if len(levels.resistance) > 1 else entry * 1.03
            target_2 = levels.r1
            target_3 = levels.r2
        elif trend == PatternDirection.BEARISH:
            entry = levels.support[0] if levels.support else levels.pivot
            stop_loss = levels.resistance[0] if levels.resistance else entry * 1.02
            target_1 = levels.support[1] if len(levels.support) > 1 else entry * 0.97
            target_2 = levels.s1
            target_3 = levels.s2
        else:
            return None

        risk = abs(entry - stop_loss)
        if risk == 0:
            return None

        return TradeSetup(
            entry=round(entry, 2),
            stop_loss=round(stop_loss, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            target_3=round(target_3, 2),
            risk_reward_1=round(abs(target_1 - entry) / risk, 2),
            risk_reward_2=round(abs(target_2 - entry) / risk, 2),
            risk_reward_3=round(abs(target_3 - entry) / risk, 2),
        )

    def _generate_summary(
        self,
        symbol: str,
        trend: PatternDirection,
        patterns: List[Pattern],
        bias: PatternDirection,
    ) -> str:
        """Generate analysis summary."""
        pattern_names = [p.pattern_type.value for p in patterns]
        pattern_str = ", ".join(pattern_names) if pattern_names else "No clear patterns"

        trend_str = trend.value
        bias_str = bias.value

        return (
            f"{symbol} is showing a {trend_str} trend with {bias_str} bias. "
            f"Detected patterns: {pattern_str}. "
            f"This is educational analysis for learning purposes."
        )

    def _generate_educational_notes(
        self, patterns: List[Pattern], trend: PatternDirection
    ) -> List[str]:
        """Generate educational notes for learning."""
        notes = []

        for pattern in patterns:
            if pattern.pattern_type == PatternType.DOUBLE_BOTTOM:
                notes.append(
                    "Double Bottom: A bullish reversal pattern with two distinct lows at similar levels. "
                    "Wait for breakout above the neckline for confirmation."
                )
            elif pattern.pattern_type == PatternType.DOUBLE_TOP:
                notes.append(
                    "Double Top: A bearish reversal pattern with two peaks at similar levels. "
                    "Wait for breakdown below the neckline for confirmation."
                )
            elif pattern.pattern_type == PatternType.TRIANGLE_ASCENDING:
                notes.append(
                    "Ascending Triangle: Typically a bullish continuation pattern. "
                    "The flat top represents selling pressure being absorbed, while rising lows show buying accumulation."
                )
            elif pattern.pattern_type == PatternType.FLAG_BULL:
                notes.append(
                    "Bull Flag: A continuation pattern showing a strong upward move (flag pole) followed by a slight pullback (flag). "
                    "Breakout above the flag often targets the height of the flag pole."
                )

        if trend == PatternDirection.BULLISH:
            notes.append(
                "Uptrend: Higher highs and higher lows indicate bullish momentum. "
                "Look for buying opportunities at support levels."
            )
        elif trend == PatternDirection.BEARISH:
            notes.append(
                "Downtrend: Lower highs and lower lows indicate bearish momentum. "
                "Consider short positions or wait for reversal signals."
            )

        notes.append(
            "Remember: Technical analysis is probabilistic, not certain. "
            "Always use proper risk management and position sizing."
        )

        return notes


# Singleton instance
chart_analysis_service = ChartAnalysisService()
