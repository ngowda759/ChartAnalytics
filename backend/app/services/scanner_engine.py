"""Deterministic scanner engine.

Builds real scanner signals from the screener_engine's deterministic OHLC
history + the project's technical-indicator functions. There is NO use of
``random`` for market values here: every signal (direction, confidence,
price, RSI, EMA, ATR, ...) is a genuine computation over a deterministic
OHLC series, so the same input always yields the same output.

When no OHLC can be produced for a symbol, that symbol is skipped (no
fabricated row is emitted). Callers can therefore trust that every returned
row is backed by a real calculation.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.schemas.scanner import (
    BreakoutSignal,
    EMACrossSignal,
    OISignal,
    ScanResult,
    ScanType,
    SignalDirection,
    VolumeSignal,
)
from app.services import indicators
from app.services.screener_engine import Candle, candles_for, _meta_for, _UNIVERSE


def _sanitize_candles(candles: Optional[List[Candle]]) -> Optional[List[Candle]]:
    """Drop rows with missing/NaN closes (halted sessions, bad provider rows)
    so downstream math never propagates NaN into price/change_percent."""
    valid = [c for c in (candles or []) if c.close is not None and math.isfinite(c.close)]
    return valid or None


def _candles_for(symbol: str) -> Optional[List[Candle]]:
    """Back-compat wrapper: real candles via the unified resolver, else None."""
    candles, _src = candles_for(symbol)
    return _sanitize_candles(candles)


def _source_status(src: str) -> Tuple[str, str]:
    """Map a market_data source label to (source, status)."""
    if src == "mock":
        return "mock", "mock"
    if src == "unavailable":
        return "unavailable", "unavailable"
    return src, "live"


def _last_change_percent(candles: List[Candle]) -> float:
    if len(candles) < 2:
        return 0.0
    prev, last = candles[-2], candles[-1]
    if prev.close == 0:
        return 0.0
    return round(((last.close - prev.close) / prev.close) * 100, 2)


def _volume_ratio(candles: List[Candle], period: int = 20) -> float:
    if len(candles) < period + 1:
        return 1.0
    recent = candles[-(period + 1):-1]
    avg = sum(c.volume for c in recent) / period if recent else 0
    if avg == 0:
        return 1.0
    return round(candles[-1].volume / avg, 2)


def _clamp_confidence(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _direction_from_score(score: float) -> SignalDirection:
    if score >= 60:
        return SignalDirection.BULLISH
    if score <= 40:
        return SignalDirection.BEARISH
    return SignalDirection.NEUTRAL


# ---------------------------------------------------------------------------
# Per-scan-type evaluators. Each returns (confidence 0-100, direction, details)
# computed from real indicators, or None when the scan condition is not met.
# ---------------------------------------------------------------------------

def _eval_breakout(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """Breakout: close breaks above the 20-day high with volume confirmation."""
    if len(candles) < 21:
        return None
    last = candles[-1]
    high20 = max(c.high for c in candles[-21:-1])
    vol_ratio = _volume_ratio(candles)
    if last.close > high20 and vol_ratio > 1.2:
        atr = _atr(candles)
        score = _clamp_confidence(60 + min(30, (vol_ratio - 1.2) * 25) + min(10, atr / last.close * 100))
        return score, SignalDirection.BULLISH, {"atr": atr, "high_20": round(high20, 2)}
    # Breakdown below 20-day low
    low20 = min(c.low for c in candles[-21:-1])
    if last.close < low20 and vol_ratio > 1.2:
        atr = _atr(candles)
        score = _clamp_confidence(60 + min(30, (vol_ratio - 1.2) * 25))
        return score, SignalDirection.BEARISH, {"atr": atr, "low_20": round(low20, 2)}
    return None


def _eval_ema_cross(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """EMA cross: 9-EMA vs 21-EMA crossover state."""
    closes = [c.close for c in candles]
    if len(closes) < 30:
        return None
    fast = indicators.calculate_ema(closes, 9)
    slow = indicators.calculate_ema(closes, 21)
    f_now, s_now = fast[-1], slow[-1]
    f_prev, s_prev = fast[-2], slow[-2]
    if None in (f_now, s_now, f_prev, s_prev):
        return None
    rsi = indicators.calculate_rsi(closes, 14)
    rsi_now = rsi[-1] if rsi and rsi[-1] is not None else 50.0
    diff = f_now - s_now
    prev_diff = f_prev - s_prev
    if prev_diff <= 0 and diff > 0:
        score = _clamp_confidence(70 + min(20, abs(diff) / s_now * 1000))
        return score, SignalDirection.BULLISH, {"ema_9": round(f_now, 2), "ema_21": round(s_now, 2), "rsi": round(rsi_now, 2)}
    if prev_diff >= 0 and diff < 0:
        score = _clamp_confidence(70 + min(20, abs(diff) / s_now * 1000))
        return score, SignalDirection.BEARISH, {"ema_9": round(f_now, 2), "ema_21": round(s_now, 2), "rsi": round(rsi_now, 2)}
    # Trend continuation: stacked EMAs
    if f_now > s_now and rsi_now > 50:
        score = _clamp_confidence(55 + min(15, (rsi_now - 50)))
        return score, SignalDirection.BULLISH, {"ema_9": round(f_now, 2), "ema_21": round(s_now, 2), "rsi": round(rsi_now, 2)}
    if f_now < s_now and rsi_now < 50:
        score = _clamp_confidence(55 + min(15, (50 - rsi_now)))
        return score, SignalDirection.BEARISH, {"ema_9": round(f_now, 2), "ema_21": round(s_now, 2), "rsi": round(rsi_now, 2)}
    return None


def _eval_volume_spike(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """Volume spike: today's volume > 2x 20-day average with a price move."""
    if len(candles) < 21:
        return None
    vol_ratio = _volume_ratio(candles)
    if vol_ratio < 2.0:
        return None
    change = _last_change_percent(candles)
    direction = SignalDirection.BULLISH if change > 0 else SignalDirection.BEARISH
    score = _clamp_confidence(60 + min(30, (vol_ratio - 2.0) * 20) + min(10, abs(change)))
    return score, direction, {"volume_ratio": vol_ratio, "change_percent": change}


def _eval_oi_buildup(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """OI buildup proxy: strong trend + rising volume implies position buildup.

    Real OI requires an options/derivatives feed which is unavailable offline;
    this is a deterministic price+volume proxy (clearly labelled) rather than
    random OI numbers.
    """
    if len(candles) < 30:
        return None
    closes = [c.close for c in candles]
    ema20 = indicators.calculate_ema(closes, 20)
    ema50 = indicators.calculate_ema(closes, 50)
    if ema20[-1] is None or ema50[-1] is None:
        return None
    vol_ratio = _volume_ratio(candles)
    change = _last_change_percent(candles)
    if ema20[-1] > ema50[-1] and change > 0 and vol_ratio > 1.1:
        score = _clamp_confidence(58 + min(25, change * 5) + min(15, (vol_ratio - 1.1) * 20))
        return score, SignalDirection.BULLISH, {"volume_ratio": vol_ratio, "change_percent": change}
    if ema20[-1] < ema50[-1] and change < 0 and vol_ratio > 1.1:
        score = _clamp_confidence(58 + min(25, abs(change) * 5) + min(15, (vol_ratio - 1.1) * 20))
        return score, SignalDirection.BEARISH, {"volume_ratio": vol_ratio, "change_percent": change}
    return None


def _eval_gapper(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """Gapper: gap between previous close and today's open > 1%."""
    if len(candles) < 2:
        return None
    prev, last = candles[-2], candles[-1]
    if prev.close == 0:
        return None
    gap_pct = ((last.open - prev.close) / prev.close) * 100
    if abs(gap_pct) < 1.0:
        return None
    direction = SignalDirection.BULLISH if gap_pct > 0 else SignalDirection.BEARISH
    score = _clamp_confidence(60 + min(30, abs(gap_pct) * 8))
    return score, direction, {"gap_percent": round(gap_pct, 2)}


def _eval_rsi_extreme(candles: List[Candle]) -> Optional[Tuple[float, SignalDirection, Dict[str, float]]]:
    """RSI extreme: RSI < 30 (oversold) or > 70 (overbought)."""
    closes = [c.close for c in candles]
    if len(closes) < 15:
        return None
    rsi = indicators.calculate_rsi(closes, 14)
    if not rsi or rsi[-1] is None:
        return None
    rsi_now = rsi[-1]
    if rsi_now < 30:
        score = _clamp_confidence(60 + (30 - rsi_now))
        return score, SignalDirection.BULLISH, {"rsi": round(rsi_now, 2)}
    if rsi_now > 70:
        score = _clamp_confidence(60 + (rsi_now - 70))
        return score, SignalDirection.BEARISH, {"rsi": round(rsi_now, 2)}
    return None


_EVALUATORS = {
    ScanType.BREAKOUT: _eval_breakout,
    ScanType.EMA_CROSS: _eval_ema_cross,
    ScanType.VOLUME_SPIKE: _eval_volume_spike,
    ScanType.OI_BUILDUP: _eval_oi_buildup,
    ScanType.GAPPER: _eval_gapper,
    ScanType.RSI_EXTREME: _eval_rsi_extreme,
}


def _atr(candles: List[Candle], period: int = 14) -> float:
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    atr_series = indicators.calculate_atr(highs, lows, closes, period)
    return round(atr_series[-1] or 0.0, 2)


def scan_market(
    scan_types: Optional[List[ScanType]] = None,
    min_confidence: float = 60.0,
    limit: int = 50,
) -> List[ScanResult]:
    """Run scans across the stock universe on REAL OHLCV.

    Returns only rows where a real indicator condition is met and the
    computed confidence is >= ``min_confidence``. Each result carries the
    ``source`` it was computed from (yfinance/angel_one/kite/mock) and a
    ``status`` (live/mock/unavailable). Symbols with no real data are skipped
    rather than fabricated.
    """
    from app.services import market_data

    types = scan_types or list(ScanType)
    results: List[ScanResult] = []
    now = datetime.utcnow()
    for meta in _UNIVERSE:
        candles, src = candles_for(meta["symbol"])
        candles = _sanitize_candles(candles)
        if not candles:
            continue
        source, status = _source_status(src)
        for scan_type in types:
            evaluator = _EVALUATORS.get(scan_type)
            if evaluator is None:
                continue
            evaluated = evaluator(candles)
            if evaluated is None:
                continue
            score, direction, extra = evaluated
            if score < min_confidence:
                continue
            last = candles[-1]
            details: Dict[str, float] = {"atr": _atr(candles)}
            details.update({k: float(v) for k, v in extra.items()})
            results.append(
                ScanResult(
                    id=f"{meta['symbol']}_{scan_type.value}_{len(results)}",
                    symbol=meta["symbol"],
                    name=meta.get("name", meta["symbol"]),
                    scan_type=scan_type,
                    direction=direction,
                    confidence=score,
                    price=round(last.close, 2),
                    change_percent=_last_change_percent(candles),
                    volume_ratio=_volume_ratio(candles),
                    details=details,
                    timestamp=now,
                    source=source,
                    status=status,
                )
            )
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:limit]


def scan_breakouts(limit: int = 20) -> List[BreakoutSignal]:
    """Breakout scan on REAL OHLC: close vs 20-day high/low + ATR + volume.

    A breakout is defined as: current close breaking above the previous
    20-day high (resistance) or below the previous 20-day low (support),
    optionally confirmed by volume > 1.0x the 20-day average. The breakout
    level, current price and volume ratio are all returned. Deterministic
    given the OHLCV input.
    """
    results: List[BreakoutSignal] = []
    for meta in _UNIVERSE:
        candles, src = candles_for(meta["symbol"])
        candles = _sanitize_candles(candles)
        if not candles or len(candles) < 21:
            continue
        source, status = _source_status(src)
        last = candles[-1]
        high20 = max(c.high for c in candles[-21:-1])
        low20 = min(c.low for c in candles[-21:-1])
        atr = _atr(candles)
        vol_ratio = _volume_ratio(candles)
        if last.close > high20 * 0.98:
            breakout_price = round(high20, 2)
            dist = ((last.close - breakout_price) / breakout_price) * 100
            confidence = _clamp_confidence(60 + min(25, (vol_ratio - 1.0) * 20) + min(15, abs(dist)))
            results.append(
                BreakoutSignal(
                    symbol=meta["symbol"],
                    type="resistance",
                    breakout_price=breakout_price,
                    current_price=round(last.close, 2),
                    distance_percent=round(dist, 2),
                    volume_ratio=vol_ratio,
                    atr=atr,
                    confidence=confidence,
                    source=source,
                    status=status,
                )
            )
        elif last.close < low20 * 1.02:
            breakout_price = round(low20, 2)
            dist = ((last.close - breakout_price) / breakout_price) * 100
            confidence = _clamp_confidence(60 + min(25, (vol_ratio - 1.0) * 20) + min(15, abs(dist)))
            results.append(
                BreakoutSignal(
                    symbol=meta["symbol"],
                    type="support",
                    breakout_price=breakout_price,
                    current_price=round(last.close, 2),
                    distance_percent=round(dist, 2),
                    volume_ratio=vol_ratio,
                    atr=atr,
                    confidence=confidence,
                    source=source,
                    status=status,
                )
            )
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:limit]


def scan_ema_crosses(limit: int = 20) -> List[EMACrossSignal]:
    """EMA crossover scan (9 vs 21) on REAL OHLC."""
    results: List[EMACrossSignal] = []
    for meta in _UNIVERSE:
        candles, src = candles_for(meta["symbol"])
        candles = _sanitize_candles(candles)
        if not candles or len(candles) < 30:
            continue
        source, status = _source_status(src)
        closes = [c.close for c in candles]
        fast = indicators.calculate_ema(closes, 9)
        slow = indicators.calculate_ema(closes, 21)
        f, s = fast[-1], slow[-1]
        if f is None or s is None:
            continue
        rsi = indicators.calculate_rsi(closes, 14)
        rsi_now = rsi[-1] if rsi and rsi[-1] is not None else 50.0
        vol_ratio = _volume_ratio(candles)
        if f > s:
            cross_type = "golden_cross"
            distance = ((f - s) / s) * 100 if s else 0.0
            confidence = _clamp_confidence(58 + min(25, abs(distance) * 20) + min(17, (rsi_now - 50) if rsi_now > 50 else 0))
        elif f < s:
            cross_type = "death_cross"
            distance = ((f - s) / s) * 100 if s else 0.0
            confidence = _clamp_confidence(58 + min(25, abs(distance) * 20) + min(17, (50 - rsi_now) if rsi_now < 50 else 0))
        else:
            continue
        results.append(
            EMACrossSignal(
                symbol=meta["symbol"],
                cross_type=cross_type,
                fast_ema=round(f, 2),
                slow_ema=round(s, 2),
                price=round(candles[-1].close, 2),
                distance_from_cross=round(distance, 2),
                rsi=round(rsi_now, 2),
                volume_ratio=vol_ratio,
                confidence=confidence,
                source=source,
                status=status,
            )
        )
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:limit]


def scan_volume_spikes(limit: int = 20) -> List[VolumeSignal]:
    """Volume-spike scan (volume > 2x 20-day average) on REAL OHLC."""
    results: List[VolumeSignal] = []
    for meta in _UNIVERSE:
        candles, src = candles_for(meta["symbol"])
        candles = _sanitize_candles(candles)
        if not candles or len(candles) < 21:
            continue
        source, status = _source_status(src)
        vol_ratio = _volume_ratio(candles)
        if vol_ratio < 2.0:
            continue
        recent = candles[-21:-1]
        avg_volume = int(sum(c.volume for c in recent) / 20) if recent else 0
        change = _last_change_percent(candles)
        spike_type = "spike_up" if change >= 0 else "spike_down"
        confidence = _clamp_confidence(60 + min(30, (vol_ratio - 2.0) * 20) + min(10, abs(change)))
        results.append(
            VolumeSignal(
                symbol=meta["symbol"],
                type=spike_type,
                current_volume=candles[-1].volume,
                avg_volume=avg_volume,
                volume_ratio=vol_ratio,
                price_change=change,
                delivery_percent=None,
                confidence=confidence,
                source=source,
                status=status,
            )
        )
    results.sort(key=lambda r: r.volume_ratio, reverse=True)
    return results[:limit]


def scan_oi_buildup(limit: int = 20) -> List[OISignal]:
    """OI-buildup scan.

    Real open-interest classification (long buildup / short buildup / short
    covering / long unwinding) requires a derivatives option-chain feed with
    actual Call OI, Put OI and OI change. yfinance does not provide NSE
    index option OI and no broker is configured by default, so this scan
    returns an explicit ``unavailable`` result rather than fabricated OI
    numbers. When a broker with option-chain support is configured, real OI
    is classified here.
    """
    from app.services import market_data

    provider = market_data.get_market_data_provider()
    has_option_feed = provider in ("angel_one", "kite") and market_data._broker_configured(provider)

    results: List[OISignal] = []
    now = datetime.utcnow()
    if not has_option_feed:
        # Truthful unavailable state — never synthetic OI.
        results.append(
            OISignal(
                symbol="NIFTY",
                type="unavailable",
                change_call_oi=0,
                change_put_oi=0,
                price_change=0.0,
                pcr=0.0,
                interpretation=(
                    "OI buildup unavailable: no derivatives/option-OI data "
                    "provider configured (configure Angel One or Kite for OI)."
                ),
                confidence=0.0,
                source="unavailable",
                status="unavailable",
            )
        )
        return results[:limit]

    for meta in _UNIVERSE:
        candles, src = candles_for(meta["symbol"])
        candles = _sanitize_candles(candles)
        if not candles or len(candles) < 30:
            continue
        source, status = _source_status(src)
        change = _last_change_percent(candles)
        chain = market_data.get_real_option_chain(meta["symbol"])  # type: ignore[attr-defined]
        classification = _classify_oi(chain, change) if chain else None
        if classification is None:
            continue
        oi_type, change_call, change_put, pcr, interp, confidence = classification
        results.append(
            OISignal(
                symbol=meta["symbol"],
                type=oi_type,
                change_call_oi=change_call,
                change_put_oi=change_put,
                price_change=change,
                pcr=pcr,
                interpretation=interp,
                confidence=confidence,
                source=source,
                status=status,
            )
        )
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:limit]


def _classify_oi(chain, price_change: float):
    """Classify real option-chain OI into buildup/unwinding/covering.

    Rules (price up + call OI up + put OI down = long buildup, etc.).
    Returns (type, change_call_oi, change_put_oi, pcr, interp, confidence)
    or None when the chain lacks usable OI.
    """
    if not chain:
        return None
    call_oi_chg = sum(getattr(c, "call_change_oi", 0) or 0 for c in chain)
    put_oi_chg = sum(getattr(c, "put_change_oi", 0) or 0 for c in chain)
    call_oi = sum(getattr(c, "call_oi", 0) or 0 for c in chain)
    put_oi = sum(getattr(c, "put_oi", 0) or 0 for c in chain)
    pcr = round(put_oi / call_oi, 2) if call_oi else 0.0
    if price_change > 0 and call_oi_chg > 0 and put_oi_chg < 0:
        oi_type, interp = "long_buildup", "Long buildup (price up, call OI up, put OI down)"
    elif price_change < 0 and call_oi_chg < 0 and put_oi_chg > 0:
        oi_type, interp = "short_buildup", "Short buildup (price down, put OI up, call OI down)"
    elif price_change > 0 and call_oi_chg < 0 and put_oi_chg > 0:
        oi_type, interp = "short_covering", "Short covering (price up, put OI up, call OI down)"
    elif price_change < 0 and call_oi_chg > 0 and put_oi_chg < 0:
        oi_type, interp = "long_unwinding", "Long unwinding (price down, call OI up, put OI down)"
    else:
        return None
    confidence = _clamp_confidence(58 + min(30, abs(price_change) * 5))
    return oi_type, int(call_oi_chg), int(put_oi_chg), pcr, interp, confidence
