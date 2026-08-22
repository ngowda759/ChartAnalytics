"""Chartink-style screener engine.

Generates deterministic synthetic OHLC history per symbol and evaluates
real screener formulas (NR7 breakout, potential breakouts) so results are
genuine computations rather than random noise. The universe and parameters
mirror popular Chartink screeners.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

import math
import random

from app.schemas.scanner import ScreenerRow, ScreenerWidget


@dataclass
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


_UNIVERSE = [
    {"symbol": "PAYTM", "name": "One 97 Communications Ltd", "base": 432.0},
    {"symbol": "NAUKRI", "name": "Info Edge (India) Limited", "base": 5870.0},
    {"symbol": "TITAN", "name": "Titan Company Limited", "base": 3450.0},
    {"symbol": "UNITDSPR", "name": "United Spirits Ltd", "base": 1520.0},
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "base": 2967.0},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "base": 1689.0},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "base": 1124.0},
    {"symbol": "INFY", "name": "Infosys Ltd", "base": 1834.0},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "base": 4123.0},
    {"symbol": "SBIN", "name": "State Bank of India", "base": 823.0},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "base": 1456.0},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "base": 156.0},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ", "base": 1289.0},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "base": 7850.0},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "base": 12800.0},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "base": 1780.0},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "base": 3650.0},
    {"symbol": "APARINDS", "name": "Apar Industries Ltd", "base": 9800.0},
    {"symbol": "KOVAI", "name": "Kovai Medical Center", "base": 2100.0},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment", "base": 1620.0},
    {"symbol": "JSWENERGY", "name": "JSW Energy Ltd", "base": 645.0},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance Ltd", "base": 2980.0},
    {"symbol": "PFC", "name": "Power Finance Corp", "base": 478.0},
    {"symbol": "RECLTD", "name": "REC Limited", "base": 512.0},
    {"symbol": "INDUSTOWER", "name": "Indus Towers Ltd", "base": 398.0},
    {"symbol": "KAYNES", "name": "Kaynes Technology", "base": 4120.0},
    {"symbol": "LICI", "name": "Life Insurance Corp", "base": 845.0},
    {"symbol": "SYRMA", "name": "Syrma SGS Technology", "base": 542.0},
    {"symbol": "PREMIERENE", "name": "Premier Energies Ltd", "base": 478.0},
    {"symbol": "BHARATFORG", "name": "Bharat Forge Ltd", "base": 1342.0},
]


def _seed_for(symbol: str) -> int:
    """Stable per-symbol seed, refreshed hourly so auto-refresh shows drift."""
    hour_salt = datetime.utcnow().strftime("%Y%m%d%H")
    return abs(hash(f"{symbol}:{hour_salt}")) % (2**31)


def _generate_ohlc(symbol: str, base: float, days: int = 260) -> List[Candle]:
    """Deterministic synthetic daily candles seeded by symbol + hour.

    DEV/TEST ONLY. Production never calls this directly; it goes through
    ``market_data.get_real_candles`` which fetches real OHLCV. Kept here so the
    explicit ``MARKET_DATA_PROVIDER=mock`` mode and the unit tests that assert
    deterministic scanner math over a known series still work.
    """
    rng = random.Random(_seed_for(symbol))
    candles: List[Candle] = []
    price = base * (1 + rng.uniform(-0.15, 0.05))
    start = datetime.utcnow() - timedelta(days=days)

    # gentle uptrend bias with noise so MA stacks and breakouts occur naturally
    drift = rng.uniform(0.0004, 0.0016)
    vol = base * 0.018

    for i in range(days):
        date = start + timedelta(days=i)
        open_ = price
        change = rng.gauss(drift, 1) * vol
        close = max(1.0, open_ + change)
        high = max(open_, close) + rng.uniform(0, vol * 0.8)
        low = min(open_, close) - rng.uniform(0, vol * 0.8)
        low = max(1.0, low)
        volume = int(rng.uniform(0.4, 3.0) * base * 1000)
        candles.append(Candle(date, round(open_, 2), round(high, 2), round(low, 2), round(close, 2), volume))
        price = close

    return candles


def _meta_for(symbol: str) -> Optional[Dict]:
    return next((m for m in _UNIVERSE if m["symbol"] == symbol), None)


def _sanitize_candles(candles: Optional[List[Candle]]) -> Optional[List[Candle]]:
    """Drop rows with missing/NaN closes (halted sessions, bad provider rows).

    Providers occasionally emit OHLCV rows whose close is NaN; letting them
    through propagates NaN into every downstream computation (indicators,
    scanner prices, agent-analyst scores) and eventually crashes pydantic
    serialization or raises ``ValueError: cannot convert float NaN to
    integer``. Sanitizing here — the single resolver every surface reads
    through — guarantees all consumers see only finite closes.
    """
    valid = [c for c in (candles or []) if c.close is not None and math.isfinite(c.close)]
    return valid or None


def candles_for(symbol: str, interval: str = "1d", limit: int = 260) -> Tuple[Optional[List[Candle]], str]:
    """Unified candle resolver used by every scanner/signal/agent.

    Returns ``(candles, source)``. Real OHLCV is fetched through the unified
    market-data service; only the explicit mock/dev provider returns synthetic
    candles. On a real-data failure returns ``(None, "unavailable")`` so the
    caller surfaces a truthful state instead of fabricating a series. Rows
    with missing/NaN closes are dropped before returning.
    """
    from app.services import market_data

    if market_data.is_mock_mode():
        meta = _meta_for(symbol)
        base = meta["base"] if meta else 1000.0
        return _generate_ohlc(symbol, base, days=limit), market_data.SOURCE_MOCK
    candles, src = market_data.get_real_candles(symbol, interval=interval, limit=limit)
    return _sanitize_candles(candles), src


def _sma(values: List[float], period: int, idx: int) -> Optional[float]:
    if idx + 1 < period:
        return None
    window = values[idx + 1 - period: idx + 1]
    return sum(window) / period


def _max_high(candles: List[Candle], period: int, idx: int) -> Optional[float]:
    if idx + 1 < period:
        return None
    window = candles[idx + 1 - period: idx + 1]
    return max(c.high for c in window)


def _weekly_close(candles: List[Candle]) -> float:
    # approximate latest weekly close as close 5 days ago
    return candles[-5].close if len(candles) >= 5 else candles[-1].close


def _monthly_closes(candles: List[Candle]) -> tuple:
    # approximate monthly close/open using ~22 trading days
    n = len(candles)
    monthly_close = candles[-1].close
    monthly_open = candles[-22].open if n >= 22 else candles[0].open
    return monthly_open, monthly_close


def _passes_nr7_breakout(c: List[Candle]) -> bool:
    if len(c) < 65:
        return False
    today_range = c[-1].high - c[-1].low
    # NR7: today's range is the narrowest of the last 7 days
    last7 = [c[i].high - c[i].low for i in range(-7, 0)]
    if today_range >= min(last7[:-1]) or today_range <= 0:
        return False
    # Weekly uptrend
    if c[-1].close <= _weekly_close(c):
        return False
    # Monthly uptrend: close > monthly close > monthly open
    m_open, m_close = _monthly_closes(c)
    if not (c[-1].close > m_close > m_open):
        return False
    # Volume baseline
    if c[-2].volume <= 10000:
        return False
    # MA stack: sma20 > sma40 > sma60
    closes = [k.close for k in c]
    s20 = _sma(closes, 20, len(closes) - 1)
    s40 = _sma(closes, 40, len(closes) - 1)
    s60 = _sma(closes, 60, len(closes) - 1)
    if None in (s20, s40, s60):
        return False
    if not (s20 > s40 > s60):
        return False
    # Volume surge: today > 1.25 * yesterday
    if c[-1].volume <= 1.25 * c[-2].volume:
        return False
    return True


def _passes_potential_breakout(c: List[Candle]) -> bool:
    if len(c) < 200:
        return False
    closes = [k.close for k in c]
    last = c[-1]
    # Within 5% of 200-day high
    max200 = _max_high(c, 200, len(c) - 1)
    if max200 is None or last.close * 1.05 <= max200:
        return False
    # Consolidation: 30-day high <= 8-day high as of 30 days ago
    max30 = _max_high(c, 30, len(c) - 1)
    if len(c) < 38 or max30 is None:
        return False
    max8_at_30 = _max_high(c, 8, len(c) - 31)
    if max8_at_30 is None or max30 > max8_at_30:
        return False
    # Volume above 50-day average volume
    vols = [k.volume for k in c]
    vol_sma = _sma([float(v) for v in vols], 50, len(vols) - 1)
    if vol_sma is None or last.volume <= vol_sma:
        return False
    # Price above 90
    if last.close <= 90:
        return False
    return True


def _to_row(meta: Dict, candles: List[Candle]) -> ScreenerRow:
    last = candles[-1]
    prev = candles[-2]
    change_percent = round(((last.close - prev.close) / prev.close) * 100, 2)
    return ScreenerRow(
        symbol=meta["symbol"],
        name=meta.get("name"),
        ltp=last.close,
        change_percent=change_percent,
        volume=last.volume,
        extra=_prediction_extra(meta["symbol"]),
    )


def _prediction_extra(symbol: str) -> Dict:
    """MiroFish swarm prediction fields merged into the screener row's extra."""
    from app.services import mirofish

    p = mirofish.predict_symbol(symbol)
    return {
        "prediction_direction": p.direction.value,
        "predicted_change_pct": p.predicted_change_percent,
        "prediction_conviction": p.conviction,
        "prediction_target": p.target_price,
    }


def _run_scan(predicate: Callable[[List[Candle]], bool], limit: int = 25) -> List[ScreenerRow]:
    rows: List[ScreenerRow] = []
    for meta in _UNIVERSE:
        candles, _src = candles_for(meta["symbol"])
        if candles and predicate(candles):
            rows.append(_to_row(meta, candles))
        if len(rows) >= limit:
            break
    return rows


_SCREENERS = {
    "copy-morning-scanner-for-buy-nr7-based-breakout-8": {
        "title": "Morning Scanner - NR7 Breakout (Buy)",
        "description": (
            "NR7 (narrowest 7-day range) with weekly + monthly uptrend, "
            "SMA 20>40>60 stack and volume surge > 1.25x"
        ),
        "predicate": _passes_nr7_breakout,
        "timeframe": "daily",
    },
    "potential-breakouts": {
        "title": "Potential Breakouts",
        "description": (
            "Close within 5% of 200-day high after a consolidation, "
            "with volume above its 50-day average"
        ),
        "predicate": _passes_potential_breakout,
        "timeframe": "daily",
    },
}


def list_screener_slugs() -> List[str]:
    return list(_SCREENERS.keys())


def build_screener_widget(slug: str, limit: int = 25) -> Optional[ScreenerWidget]:
    spec = _SCREENERS.get(slug)
    if not spec:
        return None
    rows = _run_scan(spec["predicate"], limit=limit)
    rows.sort(key=lambda r: r.change_percent or 0, reverse=True)
    return ScreenerWidget(
        id=slug,
        title=spec["title"],
        description=spec["description"],
        timeframe=spec["timeframe"],
        columns=[
            "symbol",
            "change_percent",
            "ltp",
            "volume",
            "extra.prediction_direction",
            "extra.predicted_change_pct",
            "extra.prediction_conviction",
        ],
        rows=rows,
        last_updated=datetime.utcnow(),
    )
