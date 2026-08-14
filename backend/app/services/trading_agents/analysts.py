"""Analyst agents — ported/inspired by TradingAgents (Apache-2.0).

Deterministic, offline analysts that derive per-symbol reports from the
screener-engine synthetic OHLC + the existing indicators package, mirroring
the TradingAgents analyst roles (market / fundamentals / news / sentiment).
Each report carries a 0-100 bullishness score so the downstream debate and
managers can combine them without an LLM.
"""

from dataclasses import dataclass
from typing import List, Tuple

from app.services.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_supertrend,
    interpret_rsi,
)
from app.services.screener_engine import Candle

EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 200


def _last(seq):
    return seq[-1] if seq else None


def _pct_change(candles: List[Candle], period: int) -> float:
    if len(candles) <= period:
        return 0.0
    prev = candles[-period - 1].close
    if prev <= 0:
        return 0.0
    return ((candles[-1].close - prev) / prev) * 100.0


@dataclass
class RawAnalyst:
    role: str
    summary: str
    score: int
    key_points: List[str]


def market_analyst(candles: List[Candle]) -> RawAnalyst:
    """Technical / market analyst: trend, momentum, volatility from indicators."""
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    ema20 = _last(calculate_ema(closes, EMA_FAST))
    ema50 = _last(calculate_ema(closes, EMA_SLOW))
    ema200 = _last(calculate_ema(closes, EMA_TREND))
    rsi_val = _last(calculate_rsi(closes, 14))
    macd_line, _signal, _hist = calculate_macd(closes)
    macd_val = _last(macd_line)
    adx_list = calculate_adx(highs, lows, closes, 14)
    adx_val = _last(adx_list)
    bb_list = calculate_bollinger_bands(closes, 20)
    bb_val = _last(bb_list)
    st_list = calculate_supertrend(highs, lows, closes, 10, 3.0)
    st_val = _last(st_list)
    change = _pct_change(candles, 5)

    points = []
    score = 50

    if None not in (ema20, ema50, ema200) and closes[-1] > ema20 > ema50 > ema200:
        points.append(f"Stacked EMAs (20>50>200) with price above the stack — strong uptrend")
        score += 18
    elif None not in (ema20, ema50) and closes[-1] > ema20 > ema50:
        points.append("Price above EMA20 > EMA50 — uptrend in force")
        score += 10
    elif None not in (ema20, ema50) and closes[-1] < ema20 < ema50:
        points.append("Price below EMA20 < EMA50 — downtrend pressure")
        score -= 12

    if macd_val is not None:
        if macd_val > 0:
            points.append("MACD line above zero — bullish momentum")
            score += 8
        else:
            points.append("MACD line below zero — bearish momentum")
            score -= 8

    if rsi_val is not None:
        band = interpret_rsi(rsi_val)
        if band.signal == "oversold":
            points.append(f"RSI {rsi_val:.1f} oversold — reversal potential")
            score += 6
        elif band.signal == "overbought":
            points.append(f"RSI {rsi_val:.1f} overbought — pullback risk")
            score -= 6
        else:
            points.append(f"RSI {rsi_val:.1f} neutral")

    if adx_val is not None:
        if adx_val.trend_direction == "up" and adx_val.adx >= 25:
            points.append(f"ADX {adx_val.adx:.1f} — strengthening uptrend")
            score += 6
        elif adx_val.trend_direction == "down" and adx_val.adx >= 25:
            points.append(f"ADX {adx_val.adx:.1f} — strengthening downtrend")
            score -= 6

    if st_val is not None:
        if st_val.trend == "up":
            points.append("Supertrend bullish")
            score += 4
        else:
            points.append("Supertrend bearish")
            score -= 4

    if bb_val is not None:
        if bb_val.percent_b > 1.0:
            points.append("Price above upper Bollinger band — overextension")
            score -= 3
        elif bb_val.percent_b < 0.0:
            points.append("Price below lower Bollinger band — oversold stretch")
            score += 3

    points.append(f"5-session change {change:+.2f}%")
    score = max(0, min(100, int(round(score))))
    summary = "Technical picture is " + (
        "bullish" if score >= 60 else "bearish" if score <= 40 else "mixed"
    ) + f" (score {score})."
    return RawAnalyst("Market Analyst", summary, score, points)


def fundamentals_analyst(candles: List[Candle]) -> RawAnalyst:
    """Fundamentals proxy: derive a quality/valuation proxy from OHLC stats.

    No fundamentals feed is available offline, so this analyst derives a
    stability/quality proxy (return drift, volatility, drawdown) — clearly
    labelled as a proxy so consumers know it is not live fundamental data.
    """
    closes = [c.close for c in candles]
    if len(closes) < 30:
        return RawAnalyst(
            "Fundamentals Analyst", "Insufficient history for a quality proxy.", 50, []
        )

    drift = _pct_change(candles, 30)
    mean = sum(closes[-60:]) / min(60, len(closes))
    variance = sum((p - mean) ** 2 for p in closes[-60:]) / min(60, len(closes))
    vol = (variance ** 0.5) / mean * 100 if mean > 0 else 0.0

    peak = max(closes[-60:])
    trough = min(closes[-60:])
    drawdown = ((trough - peak) / peak) * 100 if peak > 0 else 0.0

    score = 50
    points = []
    if drift > 5:
        score += 12
        points.append(f"30-session drift {drift:+.2f}% — positive momentum")
    elif drift < -5:
        score -= 10
        points.append(f"30-session drift {drift:+.2f}% — negative momentum")
    else:
        points.append(f"30-session drift {drift:+.2f}% — stable")

    if vol < 3:
        score += 8
        points.append(f"60-session volatility {vol:.2f}% — low, stable")
    elif vol > 8:
        score -= 6
        points.append(f"60-session volatility {vol:.2f}% — high, unstable")

    if drawdown > -5:
        score += 6
        points.append(f"Drawdown from 60-session peak {drawdown:+.2f}% — shallow")
    elif drawdown < -20:
        score -= 6
        points.append(f"Drawdown from 60-session peak {drawdown:+.2f}% — deep")

    points.append("Note: derived from OHLC stats (no live fundamentals feed).")
    score = max(0, min(100, int(round(score))))
    summary = f"Quality proxy score {score} (drift {drift:+.1f}%, vol {vol:.1f}%)."
    return RawAnalyst("Fundamentals Analyst", summary, score, points)


def news_analyst(candles: List[Candle]) -> RawAnalyst:
    """News analyst proxy: infers news tone from recent price/volume action."""
    if len(candles) < 6:
        return RawAnalyst("News Analyst", "Insufficient history.", 50, [])

    last = candles[-1]
    prev = candles[-2]
    change = ((last.close - prev.close) / prev.close) * 100 if prev.close > 0 else 0.0
    avg_vol = sum(c.volume for c in candles[-6:-1]) / 5
    vol_ratio = last.volume / avg_vol if avg_vol > 0 else 1.0

    score = 50
    points = []
    if change > 2 and vol_ratio > 1.3:
        score += 14
        points.append(f"Up {change:+.2f}% on {vol_ratio:.2f}x volume — positive flow")
    elif change < -2 and vol_ratio > 1.3:
        score -= 14
        points.append(f"Down {change:+.2f}% on {vol_ratio:.2f}x volume — negative flow")
    else:
        points.append(f"Move {change:+.2f}% on {vol_ratio:.2f}x volume — muted news impact")

    points.append("Note: inferred from price/volume (no live news feed).")
    score = max(0, min(100, int(round(score))))
    summary = f"Inferred news tone score {score}."
    return RawAnalyst("News Analyst", summary, score, points)


def sentiment_analyst(candles: List[Candle]) -> RawAnalyst:
    """Sentiment analyst proxy: band + score from multi-period returns."""
    if len(candles) < 20:
        return RawAnalyst("Sentiment Analyst", "Insufficient history.", 50, [])

    r5 = _pct_change(candles, 5)
    r20 = _pct_change(candles, 20)
    blended = 0.6 * r5 + 0.4 * r20

    if blended > 3:
        band = "bullish"
        score = min(100, int(round(55 + blended * 2)))
    elif blended < -3:
        band = "bearish"
        score = max(0, int(round(45 + blended * 2)))
    else:
        band = "neutral"
        score = int(round(50 + blended))

    points = [
        f"5-session return {r5:+.2f}%, 20-session return {r20:+.2f}%",
        f"Sentiment band: {band} (score {score})",
        "Note: derived from returns (no social/news sentiment feed).",
    ]
    summary = f"Sentiment {band} (score {score})."
    return RawAnalyst("Sentiment Analyst", summary, score, points)


def run_analysts(candles: List[Candle]) -> List[RawAnalyst]:
    return [
        market_analyst(candles),
        fundamentals_analyst(candles),
        news_analyst(candles),
        sentiment_analyst(candles),
    ]


def composite_score(analysts: List[RawAnalyst]) -> Tuple[int, List[str]]:
    """Weighted blend of analyst scores into a single 0-100 bullishness score."""
    weights = {
        "Market Analyst": 0.4,
        "Fundamentals Analyst": 0.25,
        "News Analyst": 0.2,
        "Sentiment Analyst": 0.15,
    }
    total_w = 0.0
    acc = 0.0
    for a in analysts:
        w = weights.get(a.role, 0.0)
        acc += w * a.score
        total_w += w
    score = int(round(acc / total_w)) if total_w > 0 else 50
    return score, [a.role for a in analysts]
