"""Strategy template engine — YAML-driven strategy cards adapted from
daily_stock_analysis (MIT) and evaluated against synthetic OHLC + indicators.

Each strategy YAML defines a set of weighted ``rules`` that the engine checks
against per-symbol candle history. Matching rules are combined into a score
(0-100), a buy/hold/avoid action, and entry/stop/target levels. Results feed
the decision-signals service so the dashboard always has actionable output,
even when the live NSE source is unavailable.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from app.services.indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_supertrend,
)
from app.services.screener_engine import Candle, _generate_ohlc, _UNIVERSE

logger = structlog.get_logger()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "data" / "strategy_templates"

# Score thresholds (mirrors DSA's action_for_score mapping).
ACTION_BUY = "buy"
ACTION_HOLD = "hold"
ACTION_AVOID = "avoid"
HORIZON_SWING = "swing"


@dataclass
class RuleResult:
    kind: str
    matched: bool
    weight: float
    detail: str = ""


@dataclass
class StrategyEval:
    symbol: str
    name: Optional[str]
    strategy: str
    display_name: str
    category: str
    action: str
    score: int
    confidence: float
    entry: Optional[float]
    stop_loss: Optional[float]
    target: Optional[float]
    horizon: str
    reasons: List[str]
    timestamp: datetime


def list_template_slugs() -> List[str]:
    if not _TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _TEMPLATES_DIR.glob("*.yaml"))


def load_template(slug: str) -> Optional[Dict[str, Any]]:
    path = _TEMPLATES_DIR / f"{slug}.yaml"
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_all_templates() -> Dict[str, Dict[str, Any]]:
    templates: Dict[str, Dict[str, Any]] = {}
    for slug in list_template_slugs():
        tpl = load_template(slug)
        if tpl and "rules" in tpl:
            templates[slug] = tpl
    return templates


# --- indicator helpers -------------------------------------------------------


def _sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _volume_avg(volumes: List[int], period: int) -> Optional[float]:
    return _sma([float(v) for v in volumes], period)


def _last_index(values: List[Any]) -> int:
    return len(values) - 1


# --- rule evaluators ---------------------------------------------------------


def _eval_ma_cross_up(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    fast = int(rule.get("fast", 5))
    slow = int(rule.get("slow", 10))
    within = int(rule.get("within_sessions", 3))
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)
    n = len(closes)
    for i in range(max(1, n - within), n):
        if fast_ema[i] is None or slow_ema[i] is None:
            continue
        if fast_ema[i] > slow_ema[i] and fast_ema[i - 1] <= slow_ema[i - 1]:
            return RuleResult("ma_cross_up", True, weight, f"MA{fast} crossed above MA{slow}")
    return RuleResult("ma_cross_up", False, weight, "no recent golden cross")


def _eval_ma_stack(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    periods = rule.get("periods", [20, 40, 60])
    order = rule.get("order", "asc")
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    emas = [calculate_ema(closes, p) for p in periods]
    last = [e[-1] for e in emas]
    if any(v is None for v in last):
        return RuleResult("ma_stack", False, weight, "insufficient history for stack")
    if order == "asc":
        ok = all(last[i] > last[i + 1] for i in range(len(last) - 1))
        label = "ascending"
    else:
        ok = all(last[i] < last[i + 1] for i in range(len(last) - 1))
        label = "descending"
    detail = f"MA{periods} {label} stack" if ok else "no aligned MA stack"
    return RuleResult("ma_stack", ok, weight, detail)


def _eval_price_above_ma(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 20))
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    ema = calculate_ema(closes, period)
    last = closes[-1]
    val = ema[-1]
    if val is None:
        return RuleResult("price_above_ma", False, weight, "insufficient history")
    ok = last > val
    return RuleResult("price_above_ma", ok, weight, f"close {last:.2f} {'>' if ok else '<='} EMA{period} {val:.2f}")


def _eval_volume_above_avg(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("avg_period", 5))
    min_ratio = float(rule.get("min_ratio", 1.0))
    weight = float(rule.get("weight", 0.0))
    vols = [c.volume for c in candles]
    avg = _volume_avg(vols[:-1], period) if len(vols) > period else _volume_avg(vols, period)
    if avg is None or avg <= 0:
        return RuleResult("volume_above_avg", False, weight, "insufficient volume history")
    ratio = vols[-1] / avg
    ok = ratio >= min_ratio
    return RuleResult(
        "volume_above_avg", ok, weight,
        f"volume ratio {ratio:.2f} {'>=' if ok else '<'} {min_ratio}",
    )


def _eval_close_above_max_high(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 20))
    weight = float(rule.get("weight", 0.0))
    if len(candles) <= period:
        return RuleResult("close_above_max_high", False, weight, "insufficient history")
    prior_high = max(c.high for c in candles[-period - 1:-1])
    ok = candles[-1].close > prior_high
    return RuleResult(
        "close_above_max_high", ok, weight,
        f"close {candles[-1].close:.2f} {'>' if ok else '<='} {period}d high {prior_high:.2f}",
    )


def _eval_strong_close(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    min_pos = float(rule.get("min_close_position", 0.7))
    weight = float(rule.get("weight", 0.0))
    last = candles[-1]
    span = last.high - last.low
    if span <= 0:
        return RuleResult("strong_close", False, weight, "zero range")
    pos = (last.close - last.low) / span
    ok = pos >= min_pos
    return RuleResult("strong_close", ok, weight, f"close position {pos:.2f}")


def _eval_macd_above_zero(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    macd_line, _signal, _hist = calculate_macd(closes)
    val = macd_line[-1]
    if val is None:
        return RuleResult("macd_above_zero", False, weight, "insufficient history")
    ok = val > 0
    return RuleResult("macd_above_zero", ok, weight, f"MACD line {val:.4f} {'>' if ok else '<='} 0")


def _eval_rsi_recover(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 14))
    oversold = float(rule.get("oversold", 30))
    within = int(rule.get("within_sessions", 3))
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    rsi = calculate_rsi(closes, period)
    n = len(closes)
    dipped = False
    for i in range(max(0, n - within - 1), n):
        if rsi[i] is not None and rsi[i] < oversold:
            dipped = True
            break
    current = rsi[-1]
    recovered = current is not None and current > oversold
    ok = dipped and recovered
    return RuleResult(
        "rsi_recover", ok, weight,
        f"RSI dipped below {oversold} and recovered to {current:.1f}" if ok else "no oversold recovery",
    )


def _eval_close_up(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    weight = float(rule.get("weight", 0.0))
    ok = candles[-1].close > candles[-2].close
    return RuleResult("close_up", ok, weight, "close higher than prior session" if ok else "close not higher")


def _eval_bollinger_squeeze(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 20))
    percentile = float(rule.get("width_percentile", 20))
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    bands = calculate_bollinger_bands(closes, period)
    widths = [b.bandwidth for b in bands if b is not None]
    if len(widths) < period:
        return RuleResult("bollinger_squeeze", False, weight, "insufficient history")
    current = widths[-1]
    threshold = _percentile(widths[:-1], percentile)
    ok = threshold is not None and current <= threshold
    return RuleResult(
        "bollinger_squeeze", ok, weight,
        f"bandwidth {current:.2f} {'<=' if ok else '>'} {percentile}th pct {threshold:.2f}" if threshold else "no percentile",
    )


def _eval_close_above_bollinger_upper(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 20))
    weight = float(rule.get("weight", 0.0))
    closes = [c.close for c in candles]
    bands = calculate_bollinger_bands(closes, period)
    last_band = bands[-1]
    if last_band is None:
        return RuleResult("close_above_bollinger_upper", False, weight, "insufficient history")
    ok = candles[-1].close > last_band.upper
    return RuleResult(
        "close_above_bollinger_upper", ok, weight,
        f"close {candles[-1].close:.2f} {'>' if ok else '<='} upper band {last_band.upper:.2f}",
    )


def _eval_supertrend_flip_up(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 10))
    mult = float(rule.get("multiplier", 3.0))
    within = int(rule.get("within_sessions", 2))
    weight = float(rule.get("weight", 0.0))
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    st = calculate_supertrend(highs, lows, closes, period, mult)
    n = len(closes)
    flipped = False
    for i in range(max(1, n - within), n):
        prev = st[i - 1]
        curr = st[i]
        if prev is None or curr is None:
            continue
        if prev.trend == "down" and curr.trend == "up":
            flipped = True
            break
    return RuleResult("supertrend_flip_up", flipped, weight, "bullish supertrend flip" if flipped else "no supertrend flip")


def _eval_price_above_supertrend(
    candles: List[Candle], rule: Dict[str, Any]
) -> RuleResult:
    period = int(rule.get("period", 10))
    mult = float(rule.get("multiplier", 3.0))
    weight = float(rule.get("weight", 0.0))
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    st = calculate_supertrend(highs, lows, closes, period, mult)
    last = st[-1]
    if last is None:
        return RuleResult("price_above_supertrend", False, weight, "insufficient history")
    ok = last.trend == "up" and closes[-1] > last.value
    return RuleResult(
        "price_above_supertrend", ok, weight,
        f"close {closes[-1]:.2f} {'>' if ok else '<='} supertrend {last.value:.2f}",
    )


_RULE_EVALUATORS = {
    "ma_cross_up": _eval_ma_cross_up,
    "ma_stack": _eval_ma_stack,
    "price_above_ma": _eval_price_above_ma,
    "volume_above_avg": _eval_volume_above_avg,
    "close_above_max_high": _eval_close_above_max_high,
    "strong_close": _eval_strong_close,
    "macd_above_zero": _eval_macd_above_zero,
    "rsi_recover": _eval_rsi_recover,
    "close_up": _eval_close_up,
    "bollinger_squeeze": _eval_bollinger_squeeze,
    "close_above_bollinger_upper": _eval_close_above_bollinger_upper,
    "supertrend_flip_up": _eval_supertrend_flip_up,
    "price_above_supertrend": _eval_price_above_supertrend,
}


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    k = (pct / 100.0) * (len(ordered) - 1)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


# --- scoring + evaluation ----------------------------------------------------


def _action_for_score(score: int) -> str:
    if score >= 70:
        return ACTION_BUY
    if score >= 45:
        return ACTION_HOLD
    return ACTION_AVOID


def _evaluate_template(
    candles: List[Candle], template: Dict[str, Any]
) -> tuple:
    results: List[RuleResult] = []
    for rule in template.get("rules", []):
        kind = rule.get("kind")
        evaluator = _RULE_EVALUATORS.get(kind)
        if evaluator is None:
            logger.warning("unknown_strategy_rule", kind=kind)
            continue
        results.append(evaluator(candles, rule))

    total_weight = sum(r.weight for r in results) or 1.0
    matched_weight = sum(r.weight for r in results if r.matched)
    coverage = matched_weight / total_weight

    scoring = template.get("scoring", {})
    base = int(scoring.get("base", 55))
    bonus = 0
    for _key, value in scoring.items():
        if _key == "base":
            continue
        bonus += int(value)
    score = int(round(base + coverage * bonus))
    score = max(0, min(100, score))

    reasons = [r.detail for r in results if r.matched]
    return score, coverage, reasons


def _levels_for(candles: List[Candle], template: Dict[str, Any], score: int) -> tuple:
    risk = template.get("risk", {})
    sl_pct = float(risk.get("stop_loss_pct", 0.03))
    tgt_pct = float(risk.get("target_pct", 0.06))
    price = candles[-1].close
    if score >= 70:
        entry = round(price, 2)
        stop_loss = round(price * (1 - sl_pct), 2)
        target = round(price * (1 + tgt_pct), 2)
    elif score >= 45:
        entry = round(price, 2)
        stop_loss = round(price * (1 - sl_pct), 2)
        target = round(price * (1 + tgt_pct * 0.5), 2)
    else:
        entry = round(price, 2)
        stop_loss = None
        target = None
    return entry, stop_loss, target


def evaluate_symbol(
    symbol: str, name: Optional[str], base: float, template: Dict[str, Any]
) -> StrategyEval:
    # Real OHLCV via the unified resolver; falls back to synthetic ONLY when
    # the explicit mock/dev provider is active. A real-data failure returns
    # None (no fabricated signal) — handled by callers.
    from app.services.screener_engine import candles_for

    candles, _src = candles_for(symbol)
    if not candles:
        return _unavailable_eval(symbol, name, template)
    score, coverage, reasons = _evaluate_template(candles, template)
    entry, stop_loss, target = _levels_for(candles, template, score)
    action = _action_for_score(score)
    confidence = round(coverage, 2)
    return StrategyEval(
        symbol=symbol,
        name=name,
        strategy=template["name"],
        display_name=template.get("display_name", template["name"]),
        category=template.get("category", "unknown"),
        action=action,
        score=score,
        confidence=confidence,
        entry=entry,
        stop_loss=stop_loss,
        target=target,
        horizon=HORIZON_SWING,
        reasons=reasons,
        timestamp=datetime.utcnow(),
    )


def _unavailable_eval(symbol: str, name: Optional[str], template: Dict[str, Any]) -> StrategyEval:
    """Truthful unavailable evaluation when real OHLCV could not be fetched."""
    return StrategyEval(
        symbol=symbol,
        name=name,
        strategy=template["name"],
        display_name=template.get("display_name", template["name"]),
        category=template.get("category", "unknown"),
        action="avoid",
        score=0,
        confidence=0.0,
        entry=None,
        stop_loss=None,
        target=None,
        horizon=HORIZON_SWING,
        reasons=["Real market data unavailable for this symbol"],
        timestamp=datetime.utcnow(),
    )


def evaluate_template_universe(
    template: Dict[str, Any], limit: int = 25
) -> List[StrategyEval]:
    rows: List[StrategyEval] = []
    for meta in _UNIVERSE:
        rows.append(evaluate_symbol(meta["symbol"], meta.get("name"), meta["base"], template))
        if len(rows) >= limit:
            break
    rows.sort(key=lambda r: r.score, reverse=True)
    return rows


def evaluate_all(limit_per_template: int = 25) -> List[StrategyEval]:
    rows: List[StrategyEval] = []
    for slug, template in load_all_templates().items():
        rows.extend(evaluate_template_universe(template, limit=limit_per_template))
    rows.sort(key=lambda r: r.score, reverse=True)
    return rows
