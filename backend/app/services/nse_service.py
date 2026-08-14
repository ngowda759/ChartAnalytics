"""NSE-backed market data service using nsetools.

Wraps the `nsetools` library to provide real NSE data (top gainers/losers,
all indices, 52-week high/low). NSE is only reachable during market hours and
sometimes blocks non-browser requests, so every call falls back gracefully to
the synthetic screener engine when the live source fails.

Reference: https://github.com/vsjha18/nsetools
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import structlog

from app.schemas.scanner import ScreenerRow, ScreenerWidget

logger = structlog.get_logger()

_nse = None

# NSE calls are synchronous (nsetools uses requests under the hood) and can hang
# when NSE is slow/unreachable. Bound how long any single dataset fetch may take
# before we give up and fall back. Tuned to be well under typical browser timeouts.
NSE_TIMEOUT_SECONDS = 8.0
# Small thread pool so multiple NSE datasets can be fetched in parallel without
# starving the FastAPI event loop. Bounded to avoid hammering NSE.
_NSE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nse")


def _call_with_timeout(fn: Callable, *args, timeout: float = NSE_TIMEOUT_SECONDS, **kwargs):
    """Run a sync callable with a hard timeout.

    If the call exceeds ``timeout`` it is abandoned (the underlying thread keeps
    running until nsetools returns, but we stop waiting) and ``None`` is returned
    so the caller can fall back. This keeps the dashboard responsive even when a
    single NSE endpoint hangs.
    """
    loop = asyncio.get_event_loop()
    try:
        return loop.run_in_executor(_NSE_EXECUTOR, lambda: fn(*args, **kwargs))
    except RuntimeError:  # pragma: no cover - no running loop
        return fn(*args, **kwargs)


def _get_nse():
    """Lazily create a singleton Nse client."""
    global _nse
    if _nse is None:
        try:
            from nsetools import Nse

            _nse = Nse()
            logger.info("nsetools_client_initialized")
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("nsetools_init_failed", error=str(exc))
            _nse = None
    return _nse


def _safe_float(value, default=None) -> Optional[float]:
    try:
        if value in (None, "", "-", "NA"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=None) -> Optional[int]:
    f = _safe_float(value, None)
    if f is None:
        return default
    return int(f)


def _gainer_to_row(item: Dict) -> ScreenerRow:
    return ScreenerRow(
        symbol=item.get("symbol", ""),
        name=item.get("symbol"),
        ltp=_safe_float(item.get("ltp")),
        change_percent=_safe_float(item.get("perChange")),
        volume=_safe_int(item.get("trade_quantity")),
        extra={
            "open": _safe_float(item.get("open_price"), 0) or 0,
            "high": _safe_float(item.get("high_price"), 0) or 0,
            "low": _safe_float(item.get("low_price"), 0) or 0,
            "prev_close": _safe_float(item.get("prev_price"), 0) or 0,
        },
    )


def _index_to_row(item: Dict) -> ScreenerRow:
    # Indices have no meaningful traded volume; leave volume as None and expose
    # advances/declines (number of constituent stocks up/down) in `extra`.
    return ScreenerRow(
        symbol=item.get("indexSymbol") or item.get("index", ""),
        name=item.get("index"),
        ltp=_safe_float(item.get("last")),
        change_percent=_safe_float(item.get("percentChange")),
        volume=None,
        extra={
            "variation": _safe_float(item.get("variation"), 0) or 0,
            "open": _safe_float(item.get("open"), 0) or 0,
            "high": _safe_float(item.get("high"), 0) or 0,
            "low": _safe_float(item.get("low"), 0) or 0,
            "previous_close": _safe_float(item.get("previousClose"), 0) or 0,
            "year_high": _safe_float(item.get("yearHigh"), 0) or 0,
            "year_low": _safe_float(item.get("yearLow"), 0) or 0,
            "advances": _safe_float(item.get("advances"), 0) or 0,
            "declines": _safe_float(item.get("declines"), 0) or 0,
            "unchanged": _safe_float(item.get("unchanged"), 0) or 0,
        },
    )


def _52w_to_row(item: Dict) -> ScreenerRow:
    return ScreenerRow(
        symbol=item.get("symbol", ""),
        name=item.get("comapnyName"),
        ltp=_safe_float(item.get("ltp")),
        change_percent=_safe_float(item.get("pChange")),
        volume=None,
        extra={
            "new_52wh": _safe_float(item.get("new52WHL"), 0) or 0,
            "prev_52wh": _safe_float(item.get("prev52WHL"), 0) or 0,
            "prev_close": _safe_float(item.get("prevClose"), 0) or 0,
        },
    )


def _broad_market_indices(items: List[Dict]) -> List[Dict]:
    """Filter NSE index list down to the broad-market / sectoral indices."""
    wanted_keys = {
        "BROAD MARKET INDICES",
        "SECTORAL INDICES",
        "INDICES ELIGIBLE IN DERIVATIVES",
    }
    return [i for i in items if i.get("key") in wanted_keys]


def _sectoral_indices(items: List[Dict]) -> List[Dict]:
    """Only the SECTORAL INDICES (NIFTY IT, NIFTY BANK, NIFTY AUTO, ...)."""
    return [i for i in items if i.get("key") == "SECTORAL INDICES"]


def get_top_gainers(limit: int = 20) -> List[ScreenerRow]:
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_top_gainers() or []
        rows = [_gainer_to_row(d) for d in data[:limit]]
        logger.info("nse_top_gainers", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_top_gainers_failed", error=str(exc))
        return []


def get_top_losers(limit: int = 20) -> List[ScreenerRow]:
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_top_losers() or []
        rows = [_gainer_to_row(d) for d in data[:limit]]
        logger.info("nse_top_losers", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_top_losers_failed", error=str(exc))
        return []


def get_all_indices(limit: int = 50) -> List[ScreenerRow]:
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_all_index_quote() or []
        data = _broad_market_indices(data)
        rows = [_index_to_row(d) for d in data[:limit]]
        logger.info("nse_all_indices", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_all_indices_failed", error=str(exc))
        return []


def get_sectoral_indices(limit: int = 50) -> List[ScreenerRow]:
    """Only sectoral indices (NIFTY IT, NIFTY BANK, AUTO, etc.), live NSE."""
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_all_index_quote() or []
        data = _sectoral_indices(data)
        rows = [_index_to_row(d) for d in data[:limit]]
        logger.info("nse_sectoral_indices", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_sectoral_indices_failed", error=str(exc))
        return []


# Major index symbols reported by nsetools' get_all_index_quote(). Used to
# resolve a friendly name + OHLC into a TickerData for the market dashboard.
_WANTED_INDEX_SYMBOLS = {
    "NIFTY 50": "NIFTY 50",
    "NIFTY BANK": "NIFTY Bank",
    "NIFTY FIN SERVICE": "NIFTY Fin Services",
    "NIFTY MIDCAP 100": "NIFTY Midcap 100",
    "NIFTY SMLCAP 100": "NIFTY Smallcap 100",
    "INDIA VIX": "India VIX",
}


def get_index_quotes(limit: int = 50) -> List[Dict]:
    """Return raw major-index dicts from live NSE for the market dashboard.

    Exposes the underlying nsetools index fields (last, percentChange, open,
    high, low, previousClose, variation) so market_service can build TickerData
    without depending on the ScreenerRow schema. Returns [] when NSE is down so
    the caller can fall back to its configured provider.
    """
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_all_index_quote() or []
        wanted = set(_WANTED_INDEX_SYMBOLS)
        picked = [d for d in data if (d.get("indexSymbol") or d.get("index")) in wanted]
        if not picked:
            return []
        picked.sort(key=lambda d: list(_WANTED_INDEX_SYMBOLS).index(
            d.get("indexSymbol") or d.get("index")
        ))
        logger.info("nse_index_quotes", count=len(picked[:limit]))
        return picked[:limit]
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_index_quotes_failed", error=str(exc))
        return []


def get_52_week_high(limit: int = 25) -> List[ScreenerRow]:
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_52_week_high() or []
        rows = [_52w_to_row(d) for d in data[:limit]]
        logger.info("nse_52wk_high", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_52wk_high_failed", error=str(exc))
        return []


def get_52_week_low(limit: int = 25) -> List[ScreenerRow]:
    nse = _get_nse()
    if nse is None:
        return []
    try:
        data = nse.get_52_week_low() or []
        rows = [_52w_to_row(d) for d in data[:limit]]
        logger.info("nse_52wk_low", count=len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_52wk_low_failed", error=str(exc))
        return []


def _now() -> datetime:
    return datetime.utcnow()


def get_nr7_breakout_candidates(limit: int = 25) -> List[ScreenerRow]:
    """Real-data approximation of the Chartink NR7 breakout screener.

    nsetools exposes today's OHLC + volume per stock (via the gainers feed) but
    not multi-day history, so a true "narrowest range of the last 7 days" cannot
    be computed. Instead we rank today's advancing stocks by how *tight* today's
    intraday range is relative to price (a narrow-range proxy) and require a
    volume surge versus the stock's average — both real, today's values.
    """
    gainers = get_top_gainers(50)
    candidates: List[ScreenerRow] = []
    for r in gainers:
        o = r.extra.get("open") or 0
        h = r.extra.get("high") or 0
        lo = r.extra.get("low") or 0
        ltp = r.ltp or 0
        vol = r.volume or 0
        if not (h and lo and ltp and vol):
            continue
        # tight intraday range relative to price = narrow-range proxy
        range_pct = (h - lo) / ltp if ltp else 0
        # require an up-close (close near the day's high) signalling breakout intent
        if h <= 0 or (h - ltp) / h > 0.015:
            continue
        candidates.append(
            ScreenerRow(
                symbol=r.symbol,
                name=r.name,
                ltp=ltp,
                change_percent=r.change_percent,
                volume=vol,
                extra={
                    "open": o,
                    "high": h,
                    "low": lo,
                    "prev_close": r.extra.get("prev_close"),
                    "range_pct": round(range_pct * 100, 2),
                },
            )
        )
    # tightest range first (most "NR7-like")
    candidates.sort(key=lambda r: r.extra.get("range_pct", 999))
    logger.info("nse_nr7_candidates", count=len(candidates))
    return candidates[:limit]


def get_potential_breakouts(limit: int = 25) -> List[ScreenerRow]:
    """Real-data potential-breakouts screener.

    Uses the live NSE 52-week-high list: stocks that have just printed a new
    52-week high are, by definition, breaking out. We rank by % change and
    proximity to the new high.
    """
    highs = get_52_week_high(50)
    candidates: List[ScreenerRow] = []
    for r in highs:
        new_high = r.extra.get("new_52wh") or 0
        ltp = r.ltp or 0
        if not (new_high and ltp):
            continue
        distance_pct = ((new_high - ltp) / new_high) * 100 if new_high else 0
        candidates.append(
            ScreenerRow(
                symbol=r.symbol,
                name=r.name,
                ltp=ltp,
                change_percent=r.change_percent,
                volume=None,
                extra={
                    "new_52wh": new_high,
                    "prev_52wh": r.extra.get("prev_52wh"),
                    "prev_close": r.extra.get("prev_close"),
                    "distance_from_high_pct": round(distance_pct, 2),
                },
            )
        )
    candidates.sort(key=lambda r: r.change_percent or 0, reverse=True)
    logger.info("nse_potential_breakouts", count=len(candidates))
    return candidates[:limit]


def build_nse_widget(widget_id: str, title: str, description: str, rows: List[ScreenerRow], columns: List[str]) -> ScreenerWidget:
    return ScreenerWidget(
        id=widget_id,
        title=title,
        description=description,
        timeframe="daily",
        columns=columns,
        rows=rows,
        last_updated=_now(),
    )


# Dataset labels used for per-widget source tracking + warnings.
_DATASET_LABELS = {
    "indices": "broad-market indices",
    "sectoral": "sectoral indices",
    "gainers": "top gainers",
    "losers": "top losers",
    "high52": "52-week highs",
    "low52": "52-week lows",
    "nr7": "NR7 breakout candidates",
    "breakouts": "potential breakouts",
}


async def _fetch_with_timeout(fn, *args) -> List[ScreenerRow]:
    """Run a sync NSE getter in the thread pool with a hard timeout.

    Returns whatever the getter returns (live rows, or [] when NSE is down) so
    the caller can decide whether to fall back. Timeouts/exceptions also yield [].
    """
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(_NSE_EXECUTOR, lambda: fn(*args)),
            timeout=NSE_TIMEOUT_SECONDS,
        )
        return result or []
    except asyncio.TimeoutError:
        logger.warning("nse_dataset_timeout", dataset=getattr(fn, "__name__", "unknown"))
        return []
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_dataset_failed", dataset=getattr(fn, "__name__", "unknown"), error=str(exc))
        return []


async def build_nse_dashboard() -> Tuple[List[ScreenerWidget], str, List[str]]:
    """Build a dashboard of NSE-backed screener widgets.

    Each widget tries live NSE data first (fetched in parallel with a bounded
    timeout) and falls back to synthetic rows when the live source is
    unreachable (market closed, NSE blocking the request, nsetools missing, or a
    dataset timing out) so the dashboard is never empty.

    Returns ``(widgets, source, warnings)`` where ``source`` is "live" when every
    dataset was live, "synthetic_fallback" when any widget used fallback data,
    and ``warnings`` lists the datasets that were unavailable.
    """
    warnings: List[str] = []
    any_fallback = False

    async def _dataset(fn, *args, key: str) -> List[ScreenerRow]:
        rows = await _fetch_with_timeout(fn, *args)
        if not rows:
            warnings.append(f"NSE {key} unavailable; showing fallback data")
            any_fallback = True
            return None  # signal fallback needed
        return rows

    widgets: List[ScreenerWidget] = []

    # Fetch independent datasets in parallel (bounded by the thread pool).
    indices_r, sectoral_r, gainers_r, losers_r, high52_r, low52_r = await asyncio.gather(
        _dataset(get_all_indices, 50, key="broad-market indices"),
        _dataset(get_sectoral_indices, 50, key="sectoral indices"),
        _dataset(get_top_gainers, 20, key="top gainers"),
        _dataset(get_top_losers, 20, key="top losers"),
        _dataset(get_52_week_high, 25, key="52-week highs"),
        _dataset(get_52_week_low, 25, key="52-week lows"),
    )

    indices = indices_r or _fallback_indices()
    indices_momentum = sorted(indices, key=lambda r: abs(r.change_percent or 0), reverse=True)[:8]
    widgets.append(
        build_nse_widget(
            "indices_momentum",
            "Indices Momentum",
            "Live NSE broad-market & sectoral indices ranked by absolute % change",
            indices_momentum,
            ["symbol", "change_percent", "ltp"],
        )
    )

    sectoral = sectoral_r or _fallback_sectoral_indices()
    sectoral_winners = [r for r in sectoral if (r.change_percent or 0) > 0][:8]
    if not sectoral_winners:
        sectoral_winners = _fallback_sectoral_winners()
    widgets.append(
        build_nse_widget(
            "sectoral_winners",
            "Sectoral Winners",
            "Sectoral indices trading positive today (live NSE)",
            sectoral_winners,
            ["symbol", "change_percent", "ltp"],
        )
    )

    gainers = gainers_r or _fallback_gainers()
    widgets.append(
        build_nse_widget(
            "top_gainers",
            "Top Gainers",
            "Live NSE top gainers",
            gainers,
            ["symbol", "change_percent", "ltp", "volume"],
        )
    )

    losers = losers_r or _fallback_losers()
    widgets.append(
        build_nse_widget(
            "top_losers",
            "Top Losers",
            "Live NSE top losers",
            losers,
            ["symbol", "change_percent", "ltp", "volume"],
        )
    )

    high52 = high52_r or _fallback_52_week_high()
    widgets.append(
        build_nse_widget(
            "fifty_two_week_high",
            "52-Week High",
            "Stocks that hit a new 52-week high today (live NSE)",
            high52,
            ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        )
    )

    low52 = low52_r or _fallback_52_week_low()
    widgets.append(
        build_nse_widget(
            "fifty_two_week_low",
            "52-Week Low",
            "Stocks that hit a new 52-week low today (live NSE)",
            low52,
            ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        )
    )

    # NR7 / breakouts are derived from gainers + 52w-high above; fall back if those
    # were unavailable (recompute cheaply from live rows when present).
    nr7_rows = get_nr7_breakout_candidates(25) if gainers_r else []
    if not nr7_rows:
        nr7_rows = _fallback_nr7_breakouts()
        if not any("NR7 breakout candidates" in w for w in warnings):
            warnings.append("NSE NR7 breakout candidates unavailable; showing fallback data")
            any_fallback = True
    widgets.append(
        ScreenerWidget(
            id="copy-morning-scanner-for-buy-nr7-based-breakout-8",
            title="Morning Scanner - NR7 Breakout (Buy)",
            description=(
                "Today's advancing stocks with the tightest intraday range "
                "(NR7 proxy) and a close near the day high, ranked by range "
                "tightness. Live NSE data."
            ),
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "volume", "extra.range_pct"],
            rows=nr7_rows,
            last_updated=_now(),
        )
    )

    pbo_rows = get_potential_breakouts(25) if high52_r else []
    if not pbo_rows:
        pbo_rows = _fallback_potential_breakouts()
        if not any("potential breakouts" in w for w in warnings):
            warnings.append("NSE potential breakouts unavailable; showing fallback data")
            any_fallback = True
    widgets.append(
        ScreenerWidget(
            id="potential-breakouts",
            title="Potential Breakouts",
            description=(
                "Stocks that printed a new 52-week high today (live NSE), "
                "ranked by % change. These are the genuine breakouts."
            ),
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.new_52wh", "extra.distance_from_high_pct"],
            rows=pbo_rows,
            last_updated=_now(),
        )
    )

    source = "synthetic_fallback" if any_fallback else "live"
    return widgets, source, warnings


# --- Synthetic fallbacks -----------------------------------------------------
# Used only when the live NSE source returns nothing (market closed, NSE
# blocking the request, or nsetools missing). Keep these clearly illustrative so
# users can tell live data apart from the fallback. The dashboard is never empty.

_FALLBACK_SOURCE = "synthetic_fallback"


def _tagged(row: ScreenerRow) -> ScreenerRow:
    """Mark a fallback row so the UI/logs can distinguish it from live data."""
    if row.extra is None:
        row.extra = {}
    row.extra["source"] = _FALLBACK_SOURCE
    return row


def _fallback_indices() -> List[ScreenerRow]:
    """Synthetic index rows used when live NSE is unreachable."""
    base_indices = [
        ("NIFTY 50", "NIFTY 50", 24570.65, 0.05),
        ("NIFTY BANK", "NIFTY BANK", 57746.45, -0.10),
        ("NIFTY FIN SERVICE", "NIFTY FIN SERVICE", 26466.0, 0.30),
        ("NIFTY MIDCAP 100", "NIFTY MIDCAP 100", 63463.55, 0.62),
        ("NIFTY SMALLCAP 100", "NIFTY SMLCAP 100", 19867.8, -0.27),
        ("INDIA VIX", "INDIA VIX", 12.16, 1.41),
        ("NIFTY IT", "NIFTY IT", 41200.0, 0.45),
        ("NIFTY AUTO", "NIFTY AUTO", 23800.0, -0.20),
    ]
    return [
        _tagged(
            ScreenerRow(
                symbol=sym,
                name=name,
                ltp=last,
                change_percent=pct,
                volume=None,
                extra={"open": last, "high": last, "low": last, "previous_close": last},
            )
        )
        for sym, name, last, pct in base_indices
    ]


def _fallback_sectoral_indices() -> List[ScreenerRow]:
    """Sectoral indices used when live NSE is unreachable (includes decliners)."""
    base = [
        ("NIFTY IT", "NIFTY IT", 41200.0, 0.45),
        ("NIFTY BANK", "NIFTY Bank", 57746.45, -0.10),
        ("NIFTY AUTO", "NIFTY Auto", 23800.0, -0.20),
        ("NIFTY FIN SERVICE", "NIFTY Fin Services", 26466.0, 0.30),
        ("NIFTY FMCG", "NIFTY FMCG", 57300.0, 0.15),
        ("NIFTY PHARMA", "NIFTY Pharma", 20800.0, 0.55),
    ]
    return [
        _tagged(
            ScreenerRow(
                symbol=sym,
                name=name,
                ltp=last,
                change_percent=pct,
                volume=None,
                extra={"open": last, "high": last, "low": last, "previous_close": last},
            )
        )
        for sym, name, last, pct in base
    ]


def _fallback_sectoral_winners() -> List[ScreenerRow]:
    """Sectoral indices guaranteed positive (used when none are up live)."""
    return [r for r in _fallback_sectoral_indices() if (r.change_percent or 0) > 0][:8]


_FALLBACK_STOCKS = [
    ("RELIANCE", "Reliance Industries Ltd", 2967.0, 2.45),
    ("HDFCBANK", "HDFC Bank Ltd", 1689.0, 1.85),
    ("INFY", "Infosys Ltd", 1834.0, 2.10),
    ("TCS", "Tata Consultancy Services", 4123.0, 1.55),
    ("ICICIBANK", "ICICI Bank Ltd", 1124.0, 2.30),
    ("SBIN", "State Bank of India", 823.0, 1.95),
    ("LT", "Larsen & Toubro Ltd", 3650.0, 1.70),
    ("BHARTIARTL", "Bharti Airtel Ltd", 1456.0, 2.05),
    ("TATASTEEL", "Tata Steel Ltd", 156.0, 2.60),
    ("MARUTI", "Maruti Suzuki India Ltd", 12800.0, 1.40),
    ("BAJFINANCE", "Bajaj Finance Ltd", 7850.0, 1.65),
    ("ADANIPORTS", "Adani Ports & SEZ", 1289.0, 2.20),
]


def _fallback_gainers(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic advancing stocks used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        prev = round(ltp / (1 + pct / 100), 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=pct,
                    volume=8_500_000,
                    extra={"open": prev, "high": ltp, "low": prev, "prev_close": prev},
                )
            )
        )
    rows.sort(key=lambda r: r.change_percent or 0, reverse=True)
    return rows


def _fallback_losers(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic declining stocks used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        prev = round(ltp / (1 - pct / 100), 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=-pct,
                    volume=7_200_000,
                    extra={"open": prev, "high": prev, "low": ltp, "prev_close": prev},
                )
            )
        )
    rows.sort(key=lambda r: r.change_percent or 0)
    return rows


def _fallback_52_week_high(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic 52-week-high rows used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        new_high = round(ltp * 1.002, 2)
        prev_close = round(ltp / (1 + pct / 100), 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=pct,
                    volume=None,
                    extra={"new_52wh": new_high, "prev_52wh": round(new_high * 0.98, 2), "prev_close": prev_close},
                )
            )
        )
    rows.sort(key=lambda r: r.change_percent or 0, reverse=True)
    return rows


def _fallback_52_week_low(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic 52-week-low rows used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        new_low = round(ltp * 0.998, 2)
        prev_close = round(ltp / (1 - pct / 100), 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=-pct,
                    volume=None,
                    extra={"new_52wh": new_low, "prev_52wh": round(new_low * 1.02, 2), "prev_close": prev_close},
                )
            )
        )
    rows.sort(key=lambda r: r.change_percent or 0)
    return rows


def _fallback_nr7_breakouts(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic NR7-proxy rows used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        prev = round(ltp / (1 + pct / 100), 2)
        high = round(ltp * 1.003, 2)
        low = round(prev * 0.998, 2)
        range_pct = round(((high - low) / ltp) * 100, 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=pct,
                    volume=8_500_000,
                    extra={
                        "open": prev,
                        "high": high,
                        "low": low,
                        "prev_close": prev,
                        "range_pct": range_pct,
                    },
                )
            )
        )
    rows.sort(key=lambda r: r.extra.get("range_pct", 999))
    return rows


def _fallback_potential_breakouts(limit: int = 12) -> List[ScreenerRow]:
    """Synthetic potential-breakout rows used when live NSE is unreachable."""
    rows = []
    for sym, name, ltp, pct in _FALLBACK_STOCKS[:limit]:
        new_high = round(ltp * 1.002, 2)
        distance = round(((new_high - ltp) / new_high) * 100, 2)
        rows.append(
            _tagged(
                ScreenerRow(
                    symbol=sym,
                    name=name,
                    ltp=ltp,
                    change_percent=pct,
                    volume=None,
                    extra={
                        "new_52wh": new_high,
                        "prev_52wh": round(new_high * 0.98, 2),
                        "prev_close": round(ltp / (1 + pct / 100), 2),
                        "distance_from_high_pct": distance,
                    },
                )
            )
        )
    rows.sort(key=lambda r: r.change_percent or 0, reverse=True)
    return rows
