"""AI Market Engine for generating trading insights."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json

from app.services.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_adx,
    calculate_bollinger_bands,
    calculate_atr,
    detect_ema_crossover,
    interpret_rsi,
    get_trend_direction,
)
from app.services.option_chain import OptionChainAnalysis


@dataclass
class PriceLevel:
    """Support or resistance level."""

    price: float
    strength: float  # 0-100
    level_type: str  # "support", "resistance"
    touches: int
    recent: bool


@dataclass
class TechnicalSignal:
    """Technical indicator signal."""

    indicator: str
    value: float
    signal: str  # "buy", "sell", "neutral"
    strength: float  # 0-100
    message: str


@dataclass
class MarketInsight:
    """Complete market analysis insight."""

    symbol: str
    timestamp: datetime
    trend: str  # "bullish", "bearish", "neutral", "ranging"
    momentum: str  # "strong", "moderate", "weak"
    sentiment: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0-100
    summary: str
    signals: List[TechnicalSignal]
    support_levels: List[PriceLevel]
    resistance_levels: List[PriceLevel]
    breakout_probability: float  # 0-100
    recommendation: str  # Educational only
    risk_factors: List[str]
    key_observations: List[str]


class AIMarketEngine:
    """AI-powered market analysis engine."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def analyze(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[int],
        option_chain: Optional[OptionChainAnalysis] = None,
    ) -> MarketInsight:
        """Perform comprehensive market analysis."""

        # Calculate technical indicators
        ema_20, ema_50, ema_200 = self._calculate_emas(closes)
        rsi_value = self._calculate_rsi(closes)
        macd_data = self._calculate_macd(closes)
        adx_data = self._calculate_adx(highs, lows, closes)
        bb_data = self._calculate_bollinger(closes)
        atr_value = self._calculate_atr(highs, lows, closes)

        # Generate signals
        signals = self._generate_signals(
            closes,
            ema_20,
            ema_50,
            ema_200,
            rsi_value,
            macd_data,
            adx_data,
            bb_data,
            volumes,
        )

        # Find support/resistance
        support, resistance = self._find_levels(highs, lows, closes, bb_data)

        # Determine trend and momentum
        trend, trend_confidence = self._determine_trend(
            closes, ema_20, ema_50, ema_200, adx_data
        )
        momentum, momentum_strength = self._analyze_momentum(
            rsi_value, macd_data, adx_data
        )

        # Calculate breakout probability
        breakout_prob = self._calculate_breakout_probability(
            closes, support, resistance, atr_value, volumes
        )

        # Overall sentiment
        sentiment = self._determine_sentiment(signals, option_chain, rsi_value)
        confidence = (trend_confidence + momentum_strength) / 2

        # Generate recommendation
        recommendation = self._generate_recommendation(
            trend, momentum, sentiment, signals, support, resistance
        )

        # Risk factors
        risk_factors = self._identify_risk_factors(
            rsi_value, macd_data, volumes, option_chain
        )

        # Key observations
        observations = self._generate_observations(
            prices, trend, momentum, signals, option_chain
        )

        # Summary
        summary = self._generate_summary(
            symbol=self.symbol,
            trend=trend,
            confidence=confidence,
            signals=signals,
            support=support,
            resistance=resistance,
        )

        return MarketInsight(
            symbol=self.symbol,
            timestamp=datetime.utcnow(),
            trend=trend,
            momentum=momentum,
            sentiment=sentiment,
            confidence=round(confidence, 1),
            summary=summary,
            signals=signals,
            support_levels=support,
            resistance_levels=resistance,
            breakout_probability=round(breakout_prob, 1),
            recommendation=recommendation,
            risk_factors=risk_factors,
            key_observations=observations,
        )

    def _calculate_emas(self, closes: List[float]) -> tuple:
        """Calculate EMAs."""
        ema_20 = calculate_ema(closes, 20)
        ema_50 = calculate_ema(closes, 50)
        ema_200 = calculate_ema(closes, 200)
        return ema_20, ema_50, ema_200

    def _calculate_rsi(self, closes: List[float]) -> float:
        """Calculate RSI."""
        rsi = calculate_rsi(closes, 14)
        return rsi[-1] if rsi and rsi[-1] is not None else 50.0

    def _calculate_macd(self, closes: List[float]) -> List:
        """Calculate MACD."""
        macd, signal, histogram = calculate_macd(closes)
        return list(zip(macd or [], signal or [], histogram or []))

    def _calculate_adx(
        self, highs: List[float], lows: List[float], closes: List[float]
    ) -> List:
        """Calculate ADX."""
        return calculate_adx(highs, lows, closes, 14)

    def _calculate_bollinger(self, closes: List[float]) -> List:
        """Calculate Bollinger Bands."""
        return calculate_bollinger_bands(closes, 20, 2.0)

    def _calculate_atr(
        self, highs: List[float], lows: List[float], closes: List[float]
    ) -> float:
        """Calculate ATR."""
        atr = calculate_atr(highs, lows, closes, 14)
        return atr[-1] if atr and atr[-1] is not None else 0.0

    def _generate_signals(
        self,
        closes: List[float],
        ema_20: List,
        ema_50: List,
        ema_200: List,
        rsi_value: float,
        macd_data: List,
        adx_data: List,
        bb_data: List,
        volumes: List[int],
    ) -> List[TechnicalSignal]:
        """Generate trading signals from indicators."""
        signals = []
        current_price = closes[-1] if closes else 0

        # EMA Signals
        if ema_20[-1] and ema_50[-1] and ema_200[-1]:
            trend_dir = get_trend_direction(
                ema_20[-1], ema_50[-1], ema_200[-1], current_price
            )
            if trend_dir == "strong_uptrend":
                signal = "buy"
                strength = 80
            elif trend_dir == "uptrend":
                signal = "buy"
                strength = 60
            elif trend_dir == "strong_downtrend":
                signal = "sell"
                strength = 80
            elif trend_dir == "downtrend":
                signal = "sell"
                strength = 60
            else:
                signal = "neutral"
                strength = 30

            signals.append(
                TechnicalSignal(
                    indicator="EMA (20/50/200)",
                    value=current_price,
                    signal=signal,
                    strength=strength,
                    message=f"Price {'above' if current_price > ema_20[-1] else 'below'} EMA structure",
                )
            )

        # RSI Signal
        rsi_signal = interpret_rsi(rsi_value)
        signals.append(
            TechnicalSignal(
                indicator="RSI (14)",
                value=round(rsi_value, 2),
                signal=rsi_signal.signal,
                strength=rsi_signal.strength,
                message=f"RSI at {rsi_value:.1f} - {rsi_signal.signal}",
            )
        )

        # MACD Signal
        if macd_data and len(macd_data) >= 2:
            current_macd = macd_data[-1]
            prev_macd = macd_data[-2]

            if current_macd[2] > 0 and prev_macd[2] <= 0:
                signal = "buy"
                strength = 70
                msg = "MACD crossed above signal"
            elif current_macd[2] < 0 and prev_macd[2] >= 0:
                signal = "sell"
                strength = 70
                msg = "MACD crossed below signal"
            elif current_macd[2] > 0:
                signal = "buy"
                strength = 50
                msg = "MACD histogram positive"
            else:
                signal = "sell"
                strength = 50
                msg = "MACD histogram negative"

            signals.append(
                TechnicalSignal(
                    indicator="MACD (12,26,9)",
                    value=round(current_macd[0], 2),
                    signal=signal,
                    strength=strength,
                    message=msg,
                )
            )

        # ADX Signal
        if adx_data and adx_data[-1]:
            adx = adx_data[-1]
            if adx.adx >= 25:
                strength = min(100, adx.adx)
                if adx.trend_direction == "up":
                    signal = "buy"
                    msg = f"Strong uptrend (ADX: {adx.adx:.1f})"
                else:
                    signal = "sell"
                    msg = f"Strong downtrend (ADX: {adx.adx:.1f})"
            else:
                signal = "neutral"
                strength = 40
                msg = f"Weak trend (ADX: {adx.adx:.1f})"

            signals.append(
                TechnicalSignal(
                    indicator="ADX (14)",
                    value=round(adx.adx, 2),
                    signal=signal,
                    strength=strength,
                    message=msg,
                )
            )

        # Bollinger Bands Signal
        if bb_data and bb_data[-1]:
            bb = bb_data[-1]
            if closes[-1] <= bb.lower:
                signal = "buy"
                strength = 75
                msg = "Price at lower Bollinger Band"
            elif closes[-1] >= bb.upper:
                signal = "sell"
                strength = 75
                msg = "Price at upper Bollinger Band"
            elif bb.percent_b < 0.2:
                signal = "buy"
                strength = 60
                msg = "Price near lower Bollinger Band"
            elif bb.percent_b > 0.8:
                signal = "sell"
                strength = 60
                msg = "Price near upper Bollinger Band"
            else:
                signal = "neutral"
                strength = 30
                msg = "Price in middle of Bollinger Bands"

            signals.append(
                TechnicalSignal(
                    indicator="Bollinger Bands (20,2)",
                    value=round(bb.middle, 2),
                    signal=signal,
                    strength=strength,
                    message=msg,
                )
            )

        return signals

    def _find_levels(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        bb_data: List,
    ) -> tuple[List[PriceLevel], List[PriceLevel]]:
        """Find support and resistance levels."""
        supports = []
        resistances = []

        # Use recent lows for support, highs for resistance
        lookback = min(50, len(closes))
        recent_closes = closes[-lookback:]
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(2, len(recent_closes) - 2):
            if (
                recent_highs[i] > recent_highs[i - 1]
                and recent_highs[i] > recent_highs[i - 2]
                and recent_highs[i] > recent_highs[i + 1]
                and recent_highs[i] > recent_highs[i + 2]
            ):
                swing_highs.append(recent_highs[i])
            if (
                recent_lows[i] < recent_lows[i - 1]
                and recent_lows[i] < recent_lows[i - 2]
                and recent_lows[i] < recent_lows[i + 1]
                and recent_lows[i] < recent_lows[i + 2]
            ):
                swing_lows.append(recent_lows[i])

        # Cluster similar levels
        tolerance = 0.005  # 0.5%

        # Support levels
        for low in sorted(set(swing_lows)):
            touches = sum(1 for l in swing_lows if abs(l - low) / low < tolerance)
            supports.append(
                PriceLevel(
                    price=round(low, 2),
                    strength=min(100, touches * 20),
                    level_type="support",
                    touches=touches,
                    recent=(low in recent_lows[-10:]),
                )
            )

        # Resistance levels
        for high in sorted(set(swing_highs)):
            touches = sum(1 for h in swing_highs if abs(h - high) / high < tolerance)
            resistances.append(
                PriceLevel(
                    price=round(high, 2),
                    strength=min(100, touches * 20),
                    level_type="resistance",
                    touches=touches,
                    recent=(high in recent_highs[-10:]),
                )
            )

        # Sort and limit
        supports.sort(key=lambda x: (x.strength, not x.recent), reverse=True)
        resistances.sort(key=lambda x: (x.strength, not x.recent), reverse=True)

        return supports[:5], resistances[:5]

    def _determine_trend(
        self,
        closes: List[float],
        ema_20: List,
        ema_50: List,
        ema_200: List,
        adx_data: List,
    ) -> tuple[str, float]:
        """Determine trend direction."""
        if not all([ema_20[-1], ema_50[-1], ema_200[-1]]):
            return "unknown", 0.0

        current_price = closes[-1]
        trend_dir = get_trend_direction(
            ema_20[-1], ema_50[-1], ema_200[-1], current_price
        )

        # ADX confirmation
        adx_strength = 50
        if adx_data and adx_data[-1]:
            adx_strength = adx_data[-1].adx

        # Map trend direction to standard output
        trend_map = {
            "strong_uptrend": "bullish",
            "uptrend": "bullish",
            "strong_downtrend": "bearish",
            "downtrend": "bearish",
            "ranging": "ranging",
            "unknown": "unknown",
        }
        trend = trend_map.get(trend_dir, "unknown")

        # Confidence based on ADX
        confidence = min(100, adx_strength * 1.2)

        return trend, confidence

    def _analyze_momentum(
        self,
        rsi_value: float,
        macd_data: List,
        adx_data: List,
    ) -> tuple[str, float]:
        """Analyze momentum."""
        momentum_score = 0

        # RSI contribution
        if rsi_value > 60:
            momentum_score += 33
        elif rsi_value < 40:
            momentum_score -= 33
        else:
            momentum_score += 15

        # MACD contribution
        if macd_data and len(macd_data) >= 2:
            if macd_data[-1][2] > 0:
                momentum_score += 33
            elif macd_data[-1][2] < 0:
                momentum_score -= 33

        # ADX contribution
        if adx_data and adx_data[-1]:
            if adx_data[-1].adx >= 25:
                momentum_score += 34

        # Interpret score
        if momentum_score >= 66:
            return "strong", min(100, momentum_score)
        elif momentum_score >= 33:
            return "moderate", momentum_score
        elif momentum_score <= -33:
            return "strong", min(100, abs(momentum_score))
        else:
            return "weak", abs(momentum_score)

    def _calculate_breakout_probability(
        self,
        closes: List[float],
        support: List[PriceLevel],
        resistance: List[PriceLevel],
        atr: float,
        volumes: List[int],
    ) -> float:
        """Calculate probability of breakout."""
        if not closes or len(closes) < 20:
            return 50.0

        current_price = closes[-1]

        # Distance to nearest resistance (as %)
        nearest_res = resistance[0].price if resistance else current_price * 1.02
        res_distance = (nearest_res - current_price) / current_price * 100

        # Distance to nearest support (as %)
        nearest_sup = support[0].price if support else current_price * 0.98
        sup_distance = (current_price - nearest_sup) / current_price * 100

        # ATR as % of price
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

        # Volume trend
        vol_trend = 1.0
        if len(volumes) >= 20:
            recent_vol = sum(volumes[-5:]) / 5
            avg_vol = sum(volumes[-20:]) / 20
            vol_trend = recent_vol / avg_vol if avg_vol > 0 else 1.0

        # Calculate probability
        # Closer to resistance with good volume = higher breakout chance
        prob = 50

        if res_distance < 1.0:  # Within 1%
            prob += 20
        elif res_distance < 2.0:
            prob += 10

        if vol_trend > 1.5:
            prob += 15
        elif vol_trend > 1.2:
            prob += 5

        # Range compression (lower ATR) = higher breakout
        if atr_pct < 1.0:
            prob += 10
        elif atr_pct > 2.0:
            prob -= 10

        return max(0, min(100, prob))

    def _determine_sentiment(
        self,
        signals: List[TechnicalSignal],
        option_chain: Optional[OptionChainAnalysis],
        rsi_value: float,
    ) -> str:
        """Determine overall sentiment."""
        buy_signals = sum(1 for s in signals if s.signal == "buy")
        sell_signals = sum(1 for s in signals if s.signal == "sell")

        # Add option chain sentiment
        if option_chain:
            if option_chain.pcr > 1.2:
                buy_signals += 1
            elif option_chain.pcr < 0.8:
                sell_signals += 1

        if buy_signals > sell_signals + 2:
            return "bullish"
        elif sell_signals > buy_signals + 2:
            return "bearish"
        else:
            return "neutral"

    def _generate_recommendation(
        self,
        trend: str,
        momentum: str,
        sentiment: str,
        signals: List[TechnicalSignal],
        support: List[PriceLevel],
        resistance: List[PriceLevel],
    ) -> str:
        """Generate educational recommendation."""
        recs = []

        recs.append(f"Current trend: {trend.upper()} with {momentum} momentum.")

        if support:
            recs.append(f"Key support at {support[0].price:.2f}.")
        if resistance:
            recs.append(f"Key resistance at {resistance[0].price:.2f}.")

        # Signal summary
        buy_count = sum(1 for s in signals if s.signal == "buy")
        sell_count = sum(1 for s in signals if s.signal == "sell")

        if buy_count > sell_count:
            recs.append(f"{buy_count} indicators suggest buying pressure.")
        elif sell_count > buy_count:
            recs.append(f"{sell_count} indicators suggest selling pressure.")
        else:
            recs.append("Indicators are mixed.")

        recs.append("This is educational analysis only, not trading advice.")

        return " ".join(recs)

    def _identify_risk_factors(
        self,
        rsi_value: float,
        macd_data: List,
        volumes: List[int],
        option_chain: Optional[OptionChainAnalysis],
    ) -> List[str]:
        """Identify key risk factors."""
        risks = []

        # Overbought/Oversold
        if rsi_value > 70:
            risks.append("RSI in overbought territory - reversal risk")
        elif rsi_value < 30:
            risks.append("RSI in oversold territory - reversal risk")

        # MACD divergence
        if macd_data and len(macd_data) >= 10:
            recent_5 = [m[2] for m in macd_data[-5:]]
            if all(x > 0 for x in recent_5) and rsi_value > 65:
                risks.append("Potential MACD/RSI divergence forming")

        # Volume anomaly
        if len(volumes) >= 20:
            recent_vol = sum(volumes[-5:]) / 5
            avg_vol = sum(volumes[-20:]) / 20
            if recent_vol > avg_vol * 3:
                risks.append("Unusual volume spike - exercise caution")

        # High PCR (hedge activity)
        if option_chain and option_chain.pcr > 1.5:
            risks.append("Very high PCR suggests elevated uncertainty")

        if not risks:
            risks.append("No significant risk factors identified")

        return risks

    def _generate_observations(
        self,
        prices: List[float],
        trend: str,
        momentum: str,
        signals: List[TechnicalSignal],
        option_chain: Optional[OptionChainAnalysis],
    ) -> List[str]:
        """Generate key observations."""
        observations = []

        if not prices:
            return observations

        # Recent price action
        if len(prices) >= 5:
            recent_change = (prices[-1] - prices[-5]) / prices[-5] * 100
            if abs(recent_change) > 2:
                observations.append(
                    f"Significant {recent_change:.1f}% move in last 5 periods"
                )

        # Trend consistency
        buy_signals = sum(1 for s in signals if s.signal == "buy")
        sell_signals = sum(1 for s in signals if s.signal == "sell")

        if buy_signals > sell_signals * 2:
            observations.append("Strong bullish alignment across indicators")
        elif sell_signals > buy_signals * 2:
            observations.append("Strong bearish alignment across indicators")

        # Option chain observations
        if option_chain:
            if option_chain.max_pain:
                observations.append(f"Max pain at {option_chain.max_pain:.0f}")

            if option_chain.iv_skew > 1.2:
                observations.append("Higher put IV suggests fear/premium for downside")
            elif option_chain.iv_skew < 0.8:
                observations.append("Lower put IV suggests complacency")

        return observations[:5]

    def _generate_summary(
        self,
        symbol: str,
        trend: str,
        confidence: float,
        signals: List[TechnicalSignal],
        support: List[PriceLevel],
        resistance: List[PriceLevel],
    ) -> str:
        """Generate market summary."""
        summary_parts = []

        # Overall view
        summary_parts.append(f"{symbol} shows {trend} bias")

        # Confidence
        if confidence >= 70:
            summary_parts.append("with high confidence")
        elif confidence >= 50:
            summary_parts.append("with moderate confidence")
        else:
            summary_parts.append("but confidence is low")

        # Key levels
        if support and resistance:
            summary_parts.append(
                f"Trading between {support[0].price:.0f} and {resistance[0].price:.0f}"
            )

        # Signal count
        buy_count = sum(1 for s in signals if s.signal == "buy")
        sell_count = sum(1 for s in signals if s.signal == "sell")

        summary_parts.append(f"({buy_count} buy, {sell_count} sell signals)")

        return " ".join(summary_parts)


def generate_market_insight(
    symbol: str,
    prices: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[int],
    option_chain: Optional[OptionChainAnalysis] = None,
) -> MarketInsight:
    """Convenience function to generate market insight."""
    engine = AIMarketEngine(symbol)
    return engine.analyze(prices, highs, lows, closes, volumes, option_chain)
