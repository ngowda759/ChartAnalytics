"""Option Chain Analytics Service."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from app.integrations.data_providers.base import OptionChainData


@dataclass
class StrikeAnalysis:
    """Analysis for a single strike price."""

    strike: float
    call_oi: int
    put_oi: int
    call_change_oi: int
    put_change_oi: int
    call_volume: int
    put_volume: int
    call_iv: float
    put_iv: float
    call_ltp: float
    put_ltp: float
    oi_balance: int  # Put OI - Call OI
    net_building: str  # "short_covering", "long_unwinding", "fresh_shorting", "fresh_buildup", "neutral"
    interpretation: str


@dataclass
class OptionChainAnalysis:
    """Complete option chain analysis."""

    symbol: str
    spot_price: float
    expiry_date: datetime
    max_pain: float
    pcr: float
    pcr_change: float
    total_call_oi: int
    total_put_oi: int
    net_oi: int  # Put OI - Call OI
    atm_strike: float
    atm_iv: Optional[float]
    iv_skew: float  # Put IV / Call IV
    trend: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0-100
    strikes: List[StrikeAnalysis]
    support_levels: List[Dict[str, Any]]
    resistance_levels: List[Dict[str, Any]]
    interpretation: str
    source: str = "unavailable"
    status: str = "unavailable"
    timestamp: Optional[datetime] = None


class OptionChainAnalyzer:
    """Analyzes option chain data to generate insights."""

    def __init__(self, spot_price: float, expiry_date: datetime):
        self.spot_price = spot_price
        self.expiry_date = expiry_date

    def analyze(self, chain_data: List[OptionChainData]) -> OptionChainAnalysis:
        """Perform complete option chain analysis."""
        # Propagate the real provider source/status/timestamp so callers can
        # trace OI back to Angel One/Kite (or truthful "unavailable").
        src = getattr(chain_data[0], "source", "unavailable") if chain_data else "unavailable"
        status = getattr(chain_data[0], "status", "unavailable") if chain_data else "unavailable"
        chain_ts = getattr(chain_data[0], "timestamp", None) if chain_data else None

        # Group by strike
        strikes = self._process_chain_data(chain_data)

        # Calculate key metrics
        max_pain = self._find_max_pain(strikes)
        pcr = self._calculate_pcr(strikes)
        pcr_change = self._calculate_pcr_change(strikes)
        total_call_oi = sum(s.call_oi or 0 for s in strikes)
        total_put_oi = sum(s.put_oi or 0 for s in strikes)
        net_oi = total_put_oi - total_call_oi

        # ATM and IV
        atm_strike = self._find_atm_strike(strikes)
        atm_iv = self._get_atm_iv(strikes)
        iv_skew = self._calculate_iv_skew(strikes)

        # Trend analysis
        trend, confidence = self._analyze_trend(strikes, net_oi)

        # Support/Resistance
        support_levels = self._find_support_levels(strikes)
        resistance_levels = self._find_resistance_levels(strikes)

        # Overall interpretation
        interpretation = self._generate_interpretation(
            pcr, trend, confidence, support_levels, resistance_levels
        )

        return OptionChainAnalysis(
            symbol=chain_data[0].symbol if chain_data else "",
            spot_price=self.spot_price,
            expiry_date=self.expiry_date,
            max_pain=max_pain,
            pcr=pcr,
            pcr_change=pcr_change,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            net_oi=net_oi,
            atm_strike=atm_strike,
            atm_iv=atm_iv,
            iv_skew=iv_skew,
            trend=trend,
            confidence=confidence,
            strikes=strikes,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            interpretation=interpretation,
            source=src,
            status=status,
            timestamp=chain_ts,
        )

    def _process_chain_data(
        self, chain_data: List[OptionChainData]
    ) -> List[StrikeAnalysis]:
        """Process raw chain data into structured analysis."""
        strikes = []

        for data in chain_data:
            call_oi = data.call_oi or 0
            put_oi = data.put_oi or 0
            call_change_oi = data.call_change_oi or 0
            put_change_oi = data.put_change_oi or 0

            # OI Balance
            oi_balance = put_oi - call_oi

            # Net building analysis
            net_building = self._determine_net_building(call_change_oi, put_change_oi)

            # Interpretation for this strike
            interpretation = self._interpret_strike(
                data.strike,
                call_oi,
                put_oi,
                call_change_oi,
                put_change_oi,
            )

            strikes.append(
                StrikeAnalysis(
                    strike=data.strike,
                    call_oi=call_oi,
                    put_oi=put_oi,
                    call_change_oi=call_change_oi,
                    put_change_oi=put_change_oi,
                    call_volume=data.call_volume,
                    put_volume=data.put_volume,
                    call_iv=data.call_iv,
                    put_iv=data.put_iv,
                    call_ltp=data.call_ltp,
                    put_ltp=data.put_ltp,
                    oi_balance=oi_balance,
                    net_building=net_building,
                    interpretation=interpretation,
                )
            )

        return strikes

    def _determine_net_building(self, call_change_oi: int, put_change_oi: int) -> str:
        """Determine type of OI building at a strike (real OI change only)."""
        cc = call_change_oi or 0
        pc = put_change_oi or 0
        if cc > 0 and pc < 0:
            return "short_covering"
        elif pc > 0 and cc < 0:
            return "long_unwinding"
        elif cc > 0 and pc > 0:
            return "fresh_buildup"
        elif cc < 0 and pc < 0:
            return "fresh_shorting"
        else:
            return "neutral"

    def _interpret_strike(
        self,
        strike: float,
        call_oi: int,
        put_oi: int,
        call_change_oi: int,
        put_change_oi: int,
    ) -> str:
        """Generate interpretation for a specific strike."""
        # Distance from ATM
        distance_pct = abs(strike - self.spot_price) / self.spot_price * 100

        if distance_pct > 5:
            return "far_otm"

        # High OI concentration
        if call_oi > 1000000 or put_oi > 1000000:
            if strike < self.spot_price:
                return "strong_support"
            else:
                return "strong_resistance"

        # Significant OI change
        if call_change_oi > 500000:
            return "call_writing"
        elif put_change_oi > 500000:
            return "put_writing"

        return "normal"

    def _find_max_pain(self, strikes: List[StrikeAnalysis]) -> float:
        """Find max pain strike (where most loss occurs for option buyers)."""
        if not strikes:
            return self.spot_price

        # Calculate pain at each strike
        pain = {}
        for strike_data in strikes:
            strike = strike_data.strike
            # Call pain: loss if price goes below strike
            # Put pain: loss if price goes above strike
            pain[strike] = sum(
                max(0, self.spot_price - s.strike) * s.call_oi for s in strikes
            ) + sum(max(0, s.strike - self.spot_price) * s.put_oi for s in strikes)

        # Return strike with minimum pain
        return min(pain, key=pain.get) if pain else self.spot_price

    def _calculate_pcr(self, strikes: List[StrikeAnalysis]) -> float:
        """Calculate Put-Call Ratio (total put OI / total call OI).

        Real OI only. None OI (provider didn't report it) is treated as 0 —
        never fabricated. Returns 0.0 when call OI is 0 to avoid division by
        zero.
        """
        total_put_oi = sum(s.put_oi or 0 for s in strikes)
        total_call_oi = sum(s.call_oi or 0 for s in strikes)

        if total_call_oi == 0:
            return 0.0

        return round(total_put_oi / total_call_oi, 2)

    def _calculate_pcr_change(self, strikes: List[StrikeAnalysis]) -> float:
        """Calculate change in PCR from previous session."""
        total_put_change = sum(s.put_change_oi or 0 for s in strikes)
        total_call_change = sum(s.call_change_oi or 0 for s in strikes)

        if total_call_change == 0:
            return 0.0

        return round(total_put_change / total_call_change, 2)

    def _find_atm_strike(self, strikes: List[StrikeAnalysis]) -> float:
        """Find ATM strike (closest to spot price)."""
        if not strikes:
            return self.spot_price

        return min(strikes, key=lambda s: abs(s.strike - self.spot_price)).strike

    def _get_atm_iv(self, strikes: List[StrikeAnalysis]) -> Optional[float]:
        """Get ATM implied volatility (None when not reported by provider)."""
        atm_strike = self._find_atm_strike(strikes)

        for s in strikes:
            if s.strike == atm_strike:
                civ, piv = s.call_iv, s.put_iv
                if civ is None and piv is None:
                    return None
                if civ is None:
                    return piv
                if piv is None:
                    return civ
                return (civ + piv) / 2

        return None

    def _calculate_iv_skew(self, strikes: List[StrikeAnalysis]) -> float:
        """Calculate IV skew (put IV / call IV)."""
        atm_strike = self._find_atm_strike(strikes)

        for s in strikes:
            if s.strike == atm_strike:
                civ, piv = s.call_iv or 0, s.put_iv or 0
                if civ == 0:
                    return 0.0
                return round(piv / civ, 2)

        return 1.0

    def _analyze_trend(
        self, strikes: List[StrikeAnalysis], net_oi: int
    ) -> tuple[str, float]:
        """Analyze overall trend from option chain."""

        # PCR interpretation
        pcr = self._calculate_pcr(strikes)

        # OI distribution
        atm_idx = next(
            (
                i
                for i, s in enumerate(strikes)
                if s.strike == self._find_atm_strike(strikes)
            ),
            0,
        )

        upper_oi = sum(
            s.put_oi for s in strikes[:atm_idx] if s.strike < self.spot_price
        )
        lower_oi = sum(
            s.call_oi for s in strikes[atm_idx:] if s.strike >= self.spot_price
        )

        bullish_signals = 0
        bearish_signals = 0

        # High PCR (>1.2) suggests bearish (hedge)
        if pcr > 1.2:
            bullish_signals += 1
        elif pcr < 0.8:
            bearish_signals += 1

        # High net OI in puts
        if net_oi > 0:
            bullish_signals += 1

        # Put writing at lower strikes (support building)
        if lower_oi > upper_oi:
            bullish_signals += 1

        # Call writing at higher strikes (resistance)
        if upper_oi > lower_oi:
            bearish_signals += 1

        # Determine trend
        if bullish_signals > bearish_signals + 1:
            trend = "bullish"
            confidence = min(100, 50 + (bullish_signals - bearish_signals) * 15)
        elif bearish_signals > bullish_signals + 1:
            trend = "bearish"
            confidence = min(100, 50 + (bearish_signals - bullish_signals) * 15)
        else:
            trend = "neutral"
            confidence = 50

        return trend, confidence

    def _find_support_levels(
        self, strikes: List[StrikeAnalysis]
    ) -> List[Dict[str, Any]]:
        """Find support levels from put OI."""
        supports = []

        # High put OI = support
        sorted_by_put_oi = sorted(strikes, key=lambda s: s.put_oi, reverse=True)[:5]

        for s in sorted_by_put_oi:
            if s.strike < self.spot_price and s.put_oi > 500000:
                supports.append(
                    {
                        "strike": s.strike,
                        "oi": s.put_oi,
                        "change_oi": s.put_change_oi,
                        "type": "high_put_oi",
                        "strength": min(100, s.put_oi / 100000),
                    }
                )

        # Put writing = strong support
        for s in strikes:
            if s.strike < self.spot_price and s.put_change_oi > 300000:
                supports.append(
                    {
                        "strike": s.strike,
                        "oi": s.put_oi,
                        "change_oi": s.put_change_oi,
                        "type": "put_writing",
                        "strength": min(100, s.put_change_oi / 50000),
                    }
                )

        # Sort by strength
        supports.sort(key=lambda x: x["strength"], reverse=True)
        return supports[:5]

    def _find_resistance_levels(
        self, strikes: List[StrikeAnalysis]
    ) -> List[Dict[str, Any]]:
        """Find resistance levels from call OI."""
        resistances = []

        # High call OI = resistance
        sorted_by_call_oi = sorted(strikes, key=lambda s: s.call_oi, reverse=True)[:5]

        for s in sorted_by_call_oi:
            if s.strike > self.spot_price and s.call_oi > 500000:
                resistances.append(
                    {
                        "strike": s.strike,
                        "oi": s.call_oi,
                        "change_oi": s.call_change_oi,
                        "type": "high_call_oi",
                        "strength": min(100, s.call_oi / 100000),
                    }
                )

        # Call writing = strong resistance
        for s in strikes:
            if s.strike > self.spot_price and s.call_change_oi > 300000:
                resistances.append(
                    {
                        "strike": s.strike,
                        "oi": s.call_oi,
                        "change_oi": s.call_change_oi,
                        "type": "call_writing",
                        "strength": min(100, s.call_change_oi / 50000),
                    }
                )

        resistances.sort(key=lambda x: x["strength"], reverse=True)
        return resistances[:5]

    def _generate_interpretation(
        self,
        pcr: float,
        trend: str,
        confidence: float,
        supports: List[Dict],
        resistances: List[Dict],
    ) -> str:
        """Generate overall interpretation."""
        interpretations = []

        # PCR interpretation
        if pcr > 1.5:
            interpretations.append(
                f"PCR of {pcr:.2f} is very high, indicating strong hedging activity"
            )
        elif pcr > 1.2:
            interpretations.append(f"PCR of {pcr:.2f} suggests bullish sentiment")
        elif pcr < 0.7:
            interpretations.append(
                f"PCR of {pcr:.2f} is low, suggesting bearish sentiment"
            )
        else:
            interpretations.append(f"PCR of {pcr:.2f} is neutral")

        # Trend interpretation
        if trend == "bullish":
            interpretations.append(f"Bullish bias with {confidence:.0f}% confidence")
        elif trend == "bearish":
            interpretations.append(f"Bearish bias with {confidence:.0f}% confidence")
        else:
            interpretations.append("Market appears neutral/ranging")

        # Support/Resistance
        if supports:
            nearest_support = supports[0]["strike"]
            interpretations.append(f"Nearest support at {nearest_support:.0f}")

        if resistances:
            nearest_resistance = resistances[0]["strike"]
            interpretations.append(f"Nearest resistance at {nearest_resistance:.0f}")

        return ". ".join(interpretations)


def analyze_option_chain(
    chain_data: List[OptionChainData],
    spot_price: float,
    expiry_date: datetime,
) -> OptionChainAnalysis:
    """Convenience function to analyze option chain."""
    analyzer = OptionChainAnalyzer(spot_price, expiry_date)
    return analyzer.analyze(chain_data)


def calculate_max_pain(chain_data: List[OptionChainData], spot_price: float) -> float:
    """Calculate max pain strike only."""
    if not chain_data:
        return spot_price

    strikes = {}
    for data in chain_data:
        pain = sum(max(0, spot_price - d.strike) * d.call_oi for d in chain_data) + sum(
            max(0, d.strike - spot_price) * d.put_oi for d in chain_data
        )
        strikes[data.strike] = pain

    return min(strikes, key=strikes.get) if strikes else spot_price


def calculate_pcr(chain_data: List[OptionChainData]) -> float:
    """Calculate Put-Call Ratio."""
    if not chain_data:
        return 0.0

    total_put_oi = sum(d.put_oi for d in chain_data)
    total_call_oi = sum(d.call_oi for d in chain_data)

    if total_call_oi == 0:
        return 0.0

    return round(total_put_oi / total_call_oi, 2)
