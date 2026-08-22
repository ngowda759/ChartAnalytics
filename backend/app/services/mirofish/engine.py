"""MiroFish swarm-prediction engine — deterministic, offline port.

Adapted from the MiroFish swarm-intelligence prediction engine (AGPL-3.0,
github.com/666ghj/MiroFish). The original builds a parallel digital world of
thousands of LLM agents from seed data and reads the emergent consensus as a
forecast. This port keeps the same conceptual pipeline with zero external
dependencies:

  seed extraction (OHLCV + indicators) -> swarm generation (persona agents)
  -> simulation rounds (social influence / herding) -> consensus aggregation
  -> prediction report (direction, conviction, price forecast).

Every agent is a deterministic function of the unified candle resolver's
OHLCV and the indicators package, seeded per symbol + hour, so predictions
are stable within an hour, never empty, and CI-testable. An LLM can be wired
in later behind a key; the deterministic path stays the default + fallback.
"""

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import structlog

from app.schemas.predictions import (
    SwarmDirection,
    SwarmPrediction,
    SwarmPredictionSummary,
    SwarmRoundSnapshot,
)
from app.services.cache import TTLCache
from app.services.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)
from app.services.screener_engine import Candle, _UNIVERSE, candles_for

logger = structlog.get_logger()

SWARM_SIZE = 24
SIMULATION_ROUNDS = 4
HORIZON_DAYS = 5
HORIZON_LABEL = "5 sessions (swing)"

# Predictions derive from candles seeded per symbol + hour, so they are stable
# within an hour. Cache per symbol for ~30 minutes so dashboards embedding a
# prediction (decision signals, scanners, agent analysis) don't re-simulate
# the swarm on every request.
_PREDICTION_CACHE: TTLCache = TTLCache(ttl=30 * 60)


# --- seed extraction ---------------------------------------------------------


@dataclass
class SeedSnapshot:
    """Normalized market features (all in [-1, 1] unless noted) extracted
    from OHLCV — the "seed information" the swarm reacts to."""

    trend: float  # EMA 20/50/200 alignment
    momentum: float  # RSI + MACD blend
    volume_flow: float  # latest volume vs its average, signed by price move
    price_position: float  # Bollinger %B mapped to [-1, 1]
    drift: float  # blended 5/20-session return
    volatility_pct: float  # ATR as % of price (positive, unbounded)
    last_close: float
    atr: float


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _pct_change(candles: List[Candle], period: int) -> float:
    if len(candles) <= period:
        return 0.0
    prev = candles[-period - 1].close
    if prev <= 0:
        return 0.0
    return ((candles[-1].close - prev) / prev) * 100.0


def extract_seed(candles: List[Candle]) -> SeedSnapshot:
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    last = candles[-1]

    ema20 = calculate_ema(closes, 20)[-1]
    ema50 = calculate_ema(closes, 50)[-1]
    ema200 = calculate_ema(closes, 200)[-1]
    trend = 0.0
    if None not in (ema20, ema50):
        spread = (ema20 - ema50) / ema50 * 100 if ema50 else 0.0
        trend += _clamp(spread / 4.0)
        trend += 0.4 if last.close > ema20 else -0.4
        if ema200 is not None:
            trend += 0.3 if ema50 > ema200 else -0.3
    trend = _clamp(trend)

    rsi_val = calculate_rsi(closes, 14)[-1]
    macd_line, _, _ = calculate_macd(closes)
    macd_val = macd_line[-1]
    momentum = 0.0
    if rsi_val is not None:
        momentum += _clamp((rsi_val - 50.0) / 25.0) * 0.6
    if macd_val is not None:
        scale = last.close * 0.01 or 1.0
        momentum += _clamp(macd_val / scale) * 0.4
    momentum = _clamp(momentum)

    vols = [c.volume for c in candles]
    avg_vol = sum(vols[-21:-1]) / 20 if len(vols) > 20 else (sum(vols) / len(vols) if vols else 0)
    vol_ratio = last.volume / avg_vol if avg_vol > 0 else 1.0
    day_move = _pct_change(candles, 1)
    volume_flow = _clamp((vol_ratio - 1.0) * (1.0 if day_move >= 0 else -1.0))

    bb = calculate_bollinger_bands(closes, 20)[-1]
    price_position = _clamp((bb.percent_b - 0.5) * 2.0) if bb is not None else 0.0

    drift = _clamp((0.6 * _pct_change(candles, 5) + 0.4 * _pct_change(candles, 20)) / 8.0)

    atr_list = calculate_atr(highs, lows, closes, 14)
    atr_val = atr_list[-1] if atr_list else None
    atr = float(atr_val) if atr_val is not None else last.close * 0.02
    volatility_pct = (atr / last.close * 100.0) if last.close > 0 else 0.0

    return SeedSnapshot(
        trend=round(trend, 4),
        momentum=round(momentum, 4),
        volume_flow=round(volume_flow, 4),
        price_position=round(price_position, 4),
        drift=round(drift, 4),
        volatility_pct=round(volatility_pct, 4),
        last_close=last.close,
        atr=round(atr, 4),
    )


# --- swarm generation --------------------------------------------------------


@dataclass
class SwarmAgent:
    """One persona agent in the simulated world."""

    persona: str
    weights: Dict[str, float]
    aggressiveness: float
    herd: float  # susceptibility to social influence
    memory: float  # weight on own previous stance
    stance: float = 0.0


# Persona feature weights mirror classic market-participant archetypes, the
# way MiroFish generates heterogeneous agent personas from the seed graph.
_PERSONAS: List[Tuple[str, Dict[str, float], float]] = [
    ("Momentum Trader", {"momentum": 0.55, "drift": 0.25, "volume_flow": 0.2}, 0.7),
    ("Trend Follower", {"trend": 0.6, "drift": 0.25, "momentum": 0.15}, 0.5),
    ("Mean Reversion", {"price_position": -0.5, "momentum": -0.3, "trend": 0.2}, 0.3),
    ("Value Investor", {"drift": 0.4, "trend": 0.3, "price_position": -0.3}, 0.15),
    ("Breakout Trader", {"volume_flow": 0.45, "price_position": 0.35, "momentum": 0.2}, 0.65),
    ("Contrarian", {"drift": -0.4, "price_position": -0.35, "momentum": -0.25}, 0.1),
]


def _seed_for(symbol: str) -> int:
    # SHA-256 (not builtin hash()) so swarm generation is reproducible across
    # processes/Python versions; builtin string hash is salted per process.
    hour_salt = datetime.utcnow().strftime("%Y%m%d%H")
    digest = hashlib.sha256(f"mirofish:{symbol}:{hour_salt}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def build_swarm(symbol: str, size: int = SWARM_SIZE) -> List[SwarmAgent]:
    """Deterministically generate the agent population for a symbol."""
    rng = random.Random(_seed_for(symbol))
    swarm: List[SwarmAgent] = []
    for i in range(size):
        persona, base_weights, base_herd = _PERSONAS[i % len(_PERSONAS)]
        weights = {k: _clamp(v * rng.uniform(0.8, 1.2), -1.0, 1.0) for k, v in base_weights.items()}
        swarm.append(
            SwarmAgent(
                persona=persona,
                weights=weights,
                aggressiveness=rng.uniform(0.6, 1.4),
                herd=_clamp(base_herd * rng.uniform(0.7, 1.3), 0.0, 0.95),
                memory=rng.uniform(0.25, 0.75),
            )
        )
    return swarm


# --- simulation --------------------------------------------------------------


def _own_signal(agent: SwarmAgent, seed: SeedSnapshot) -> float:
    features = {
        "trend": seed.trend,
        "momentum": seed.momentum,
        "volume_flow": seed.volume_flow,
        "price_position": seed.price_position,
        "drift": seed.drift,
    }
    raw = sum(agent.weights.get(k, 0.0) * v for k, v in features.items())
    return math.tanh(agent.aggressiveness * raw)


def simulate(
    swarm: List[SwarmAgent], seed: SeedSnapshot, rounds: int = SIMULATION_ROUNDS
) -> Tuple[List[SwarmRoundSnapshot], float]:
    """Run the opinion-dynamics simulation.

    Round 0 is each agent's independent reaction to the seed. Every following
    round blends the agent's own signal with the current swarm consensus
    (social influence), so opinions evolve the way MiroFish's agents do
    through interaction. Returns (round snapshots, final consensus).
    """
    for agent in swarm:
        agent.stance = _own_signal(agent, seed)

    snapshots: List[SwarmRoundSnapshot] = []
    consensus = 0.0
    for rnd in range(rounds):
        consensus = sum(a.stance for a in swarm) / len(swarm)
        bull = sum(1 for a in swarm if a.stance > 0.1)
        bear = sum(1 for a in swarm if a.stance < -0.1)
        neutral = len(swarm) - bull - bear
        snapshots.append(
            SwarmRoundSnapshot(
                round=rnd,
                bullish_pct=round(bull / len(swarm) * 100, 1),
                bearish_pct=round(bear / len(swarm) * 100, 1),
                neutral_pct=round(neutral / len(swarm) * 100, 1),
                consensus=round(consensus, 4),
            )
        )
        if rnd < rounds - 1:
            for agent in swarm:
                social = agent.herd * consensus + (1.0 - agent.herd) * _own_signal(agent, seed)
                agent.stance = _clamp(agent.memory * agent.stance + (1.0 - agent.memory) * social)
    return snapshots, consensus


# --- aggregation -------------------------------------------------------------

_DIRECTION_THRESHOLD = 0.12


def _direction_for(consensus: float) -> SwarmDirection:
    if consensus > _DIRECTION_THRESHOLD:
        return SwarmDirection.BULLISH
    if consensus < -_DIRECTION_THRESHOLD:
        return SwarmDirection.BEARISH
    return SwarmDirection.NEUTRAL


def _key_drivers(seed: SeedSnapshot) -> List[str]:
    contributions = {
        "trend": ("EMA trend alignment", seed.trend),
        "momentum": ("RSI/MACD momentum", seed.momentum),
        "volume_flow": ("volume flow", seed.volume_flow),
        "price_position": ("Bollinger price position", seed.price_position),
        "drift": ("recent price drift", seed.drift),
    }
    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1][1]), reverse=True)
    drivers = []
    for _key, (label, value) in ranked[:3]:
        tone = "supportive" if value > 0.1 else "adverse" if value < -0.1 else "muted"
        drivers.append(f"{label} {tone} ({value:+.2f})")
    drivers.append(f"volatility (ATR) {seed.volatility_pct:.2f}% of price")
    return drivers


def _report(
    direction: SwarmDirection,
    conviction: int,
    consensus: float,
    seed: SeedSnapshot,
    counts: Tuple[int, int, int],
    rounds: List[SwarmRoundSnapshot],
) -> str:
    bull, bear, neutral = counts
    drift_note = ""
    if len(rounds) >= 2:
        delta = rounds[-1].consensus - rounds[0].consensus
        if abs(delta) >= 0.05:
            drift_note = (
                f" Opinion {'firmed up' if delta > 0 else 'softened'} over the "
                f"simulation (consensus {rounds[0].consensus:+.2f} -> {rounds[-1].consensus:+.2f})."
            )
    return (
        f"A swarm of {bull + bear + neutral} persona agents (momentum, trend, "
        f"mean-reversion, value, breakout, contrarian) simulated on the latest "
        f"market seed reached a {direction.value} consensus of {consensus:+.2f} "
        f"with conviction {conviction}/100: {bull} bullish, {bear} bearish, "
        f"{neutral} neutral.{drift_note} Volatility context: ATR "
        f"{seed.volatility_pct:.2f}% of price. Educational simulation — not "
        f"investment advice."
    )


def predict_from_candles(
    symbol: str,
    candles: List[Candle],
    name: Optional[str] = None,
    source: str = "mock",
    status: str = "mock",
) -> SwarmPrediction:
    """Run the full MiroFish pipeline on a candle series."""
    seed = extract_seed(candles)
    swarm = build_swarm(symbol)
    rounds, consensus = simulate(swarm, seed)

    direction = _direction_for(consensus)
    bull = sum(1 for a in swarm if a.stance > 0.1)
    bear = sum(1 for a in swarm if a.stance < -0.1)
    neutral = len(swarm) - bull - bear
    if consensus > 0:
        agreement = sum(1 for a in swarm if a.stance > 0) / len(swarm)
    elif consensus < 0:
        agreement = sum(1 for a in swarm if a.stance < 0) / len(swarm)
    else:
        agreement = 1.0

    conviction = int(round(100 * (0.5 * min(1.0, abs(consensus) * 2.0) + 0.5 * agreement)))
    conviction = max(0, min(100, conviction))

    # Forecast: consensus scaled by volatility over the horizon, damped by
    # conviction, capped at +/-15% so the band stays sane.
    move = consensus * seed.volatility_pct * math.sqrt(HORIZON_DAYS) * (0.4 + 0.6 * conviction / 100.0)
    # Clamp to +/-15% and normalize -0.0 -> 0.0 so the band stays sane and
    # the serialized output never shows a negative zero.
    predicted_change = round(max(-15.0, min(15.0, move)), 2) + 0.0
    price = seed.last_close
    target = round(price * (1.0 + predicted_change / 100.0), 2)
    band = seed.atr * 1.5
    target_low = round(min(target, price) - band, 2)
    target_high = round(max(target, price) + band, 2)

    confidence = round(
        min(0.95, 0.3 + 0.65 * agreement) * (1.0 - min(0.5, seed.volatility_pct / 20.0)), 2
    )
    confidence = max(0.0, min(1.0, confidence))

    return SwarmPrediction(
        symbol=symbol,
        name=name,
        direction=direction,
        conviction=conviction,
        predicted_change_percent=predicted_change,
        current_price=round(price, 2),
        target_price=target,
        target_low=target_low,
        target_high=target_high,
        horizon=HORIZON_LABEL,
        confidence=confidence,
        agents_total=len(swarm),
        agents_bullish=bull,
        agents_bearish=bear,
        agents_neutral=neutral,
        rounds=rounds,
        key_drivers=_key_drivers(seed),
        report=_report(direction, conviction, consensus, seed, (bull, bear, neutral), rounds),
        timestamp=datetime.utcnow(),
        source=source,
        status=status,
    )


def _unavailable_prediction(symbol: str, name: Optional[str]) -> SwarmPrediction:
    """Truthful result when real market data could not be fetched."""
    return SwarmPrediction(
        symbol=symbol,
        name=name,
        direction=SwarmDirection.NEUTRAL,
        conviction=0,
        predicted_change_percent=0.0,
        confidence=0.0,
        report="Market data unavailable; swarm simulation skipped.",
        timestamp=datetime.utcnow(),
        source="unavailable",
        status="unavailable",
    )


def _source_status(src: str) -> Tuple[str, str]:
    if src == "mock":
        return "mock", "mock"
    if src == "unavailable":
        return "unavailable", "unavailable"
    return src, "live"


def predict_symbol(
    symbol: str,
    name: Optional[str] = None,
    use_cache: bool = True,
) -> SwarmPrediction:
    """Predict one symbol via the unified candle resolver (cached per symbol)."""
    key = symbol.upper()
    if use_cache:
        cached = _PREDICTION_CACHE.get(key)
        if cached is not None:
            return cached

    meta = next((m for m in _UNIVERSE if m["symbol"] == key), None)
    name = name or (meta.get("name") if meta else None)
    candles, src = candles_for(key)
    # Providers occasionally return rows with missing/NaN closes (e.g. a
    # halted session); drop them so the forecast never propagates NaN.
    candles = [c for c in (candles or []) if c.close is not None and math.isfinite(c.close)]
    if len(candles) < 30:
        prediction = _unavailable_prediction(key, name)
    else:
        source, status = _source_status(src)
        prediction = predict_from_candles(key, candles, name=name, source=source, status=status)
    _PREDICTION_CACHE.set(key, prediction)
    return prediction


def predict_universe(limit: int = 25, use_cache: bool = True) -> List[SwarmPrediction]:
    results = [predict_symbol(m["symbol"], m.get("name"), use_cache=use_cache) for m in _UNIVERSE[:limit]]
    results.sort(key=lambda p: (p.conviction, p.predicted_change_percent), reverse=True)
    return results


def summary_for_symbol(symbol: str) -> SwarmPredictionSummary:
    """Compact prediction for embedding in signals/scans/agent analysis."""
    p = predict_symbol(symbol)
    return SwarmPredictionSummary(
        direction=p.direction,
        conviction=p.conviction,
        predicted_change_percent=p.predicted_change_percent,
        target_price=p.target_price,
        confidence=p.confidence,
    )


def invalidate_prediction_cache() -> None:
    _PREDICTION_CACHE.clear()


def prediction_cache_age_seconds() -> Optional[float]:
    """Seconds since the oldest cached prediction was written, else None."""
    import time

    if not _PREDICTION_CACHE._store:  # noqa: SLF001 - introspection
        return None
    oldest = min(exp for _, exp in _PREDICTION_CACHE._store.values())  # noqa: SLF001
    return max(0.0, time.monotonic() - (oldest - _PREDICTION_CACHE._ttl))  # noqa: SLF001
