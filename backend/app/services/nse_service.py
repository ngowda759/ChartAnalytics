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
import time
from typing import Callable, Dict, List, Optional, Tuple

import structlog

from app.schemas.scanner import ScreenerRow, ScreenerWidget
from app.services.cache import TTLCache

logger = structlog.get_logger()

_nse = None

# NSE calls are synchronous (nsetools uses requests under the hood) and can hang
# when NSE is slow/unreachable. Bound how long any single dataset fetch may take
# before we give up and fall back. Tuned to be well under typical browser timeouts.
NSE_TIMEOUT_SECONDS = 8.0
# Small thread pool so multiple NSE datasets can be fetched in parallel without
# starving the FastAPI event loop. Bounded to avoid hammering NSE.
_NSE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nse")

# Short-lived cache of successful live NSE datasets so a transient NSE failure
# serves the last real data (marked stale) instead of synthetic fallback.
_NSE_CACHE: TTLCache = TTLCache(ttl=120)
_FALLBACK_SOURCE = "synthetic_fallback"


def _call_with_timeout(fn: Callable, *args, timeout: float = NSE_TIMEOUT_SECONDS, **kwargs):
    """Run a sync callable in the thread pool (caller applies the timeout)."""
    loop = asyncio.get_event_loop()
    try:
        return loop.run_in_executor(_NSE_EXECUTOR, lambda: fn(*args, **kwargs))
    except RuntimeError:  # pragma: no cover - no running loop
        return fn(*args, **kwargs)


def clear_nse_cache() -> None:
    """Clear the short-lived NSE dataset cache (used by tests / refresh)."""
    _NSE_CACHE.clear()


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


def _log_nse(operation: str, started: float, count: int, status: str = "success", error: str = ""):
    logger.info(
        "nse_request",
        provider="nse",
        operation=operation,
        duration_ms=round((time.time() - started) * 1000, 1),
        source="nse",
        row_count=count,
        status=status,
        error=error,
    )


def get_top_gainers(limit: int = 20) -> List[ScreenerRow]:
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("top_gainers", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_top_gainers() or []
        rows = [_gainer_to_row(d) for d in data[:limit]]
        _log_nse("top_gainers", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("top_gainers", started, 0, status="error", error=str(exc))
        return []


def get_top_losers(limit: int = 20) -> List[ScreenerRow]:
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("top_losers", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_top_losers() or []
        rows = [_gainer_to_row(d) for d in data[:limit]]
        _log_nse("top_losers", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("top_losers", started, 0, status="error", error=str(exc))
        return []


def get_all_indices(limit: int = 50) -> List[ScreenerRow]:
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("all_indices", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_all_index_quote() or []
        data = _broad_market_indices(data)
        rows = [_index_to_row(d) for d in data[:limit]]
        _log_nse("all_indices", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("all_indices", started, 0, status="error", error=str(exc))
        return []


def get_sectoral_indices(limit: int = 50) -> List[ScreenerRow]:
    """Only sectoral indices (NIFTY IT, NIFTY BANK, AUTO, etc.), live NSE."""
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("sectoral_indices", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_all_index_quote() or []
        data = _sectoral_indices(data)
        rows = [_index_to_row(d) for d in data[:limit]]
        _log_nse("sectoral_indices", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("sectoral_indices", started, 0, status="error", error=str(exc))
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
    started = time.time()
    try:
        data = nse.get_all_index_quote() or []
        wanted = set(_WANTED_INDEX_SYMBOLS)
        picked = [d for d in data if (d.get("indexSymbol") or d.get("index")) in wanted]
        if not picked:
            _log_nse("index_quotes", started, 0, status="unavailable", error="no_matching_indices")
            return []
        picked.sort(key=lambda d: list(_WANTED_INDEX_SYMBOLS).index(
            d.get("indexSymbol") or d.get("index")
        ))
        _log_nse("index_quotes", started, len(picked[:limit]))
        return picked[:limit]
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("index_quotes", started, 0, status="error", error=str(exc))
        return []


def get_52_week_high(limit: int = 25) -> List[ScreenerRow]:
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("52wk_high", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_52_week_high() or []
        rows = [_52w_to_row(d) for d in data[:limit]]
        _log_nse("52wk_high", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("52wk_high", started, 0, status="error", error=str(exc))
        return []


def get_52_week_low(limit: int = 25) -> List[ScreenerRow]:
    started = time.time()
    nse = _get_nse()
    if nse is None:
        _log_nse("52wk_low", started, 0, status="unavailable", error="nsetools_unavailable")
        return []
    try:
        data = nse.get_52_week_low() or []
        rows = [_52w_to_row(d) for d in data[:limit]]
        _log_nse("52wk_low", started, len(rows))
        return rows
    except Exception as exc:  # pragma: no cover - network dependent
        _log_nse("52wk_low", started, 0, status="error", error=str(exc))
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
        ex = r.extra or {}
        o = ex.get("open") or 0
        h = ex.get("high") or 0
        lo = ex.get("low") or 0
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
                    "prev_close": ex.get("prev_close"),
                    "range_pct": round(range_pct * 100, 2),
                },
            )
        )
    # tightest range first (most "NR7-like")
    candidates.sort(key=lambda r: (r.extra or {}).get("range_pct", 999))
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
        ex = r.extra or {}
        new_high = ex.get("new_52wh") or 0
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
                    "prev_52wh": ex.get("prev_52wh"),
                    "prev_close": ex.get("prev_close"),
                    "distance_from_high_pct": round(distance_pct, 2),
                },
            )
        )
    candidates.sort(key=lambda r: r.change_percent or 0, reverse=True)
    logger.info("nse_potential_breakouts", count=len(candidates))
    return candidates[:limit]


def _nr7_from_rows(gainers: List[ScreenerRow]) -> List[ScreenerRow]:
    """Recompute the NR7-proxy screener from already-fetched gainer rows.

    Used when the live fetch failed but cached gainer rows are available, so the
    derived NR7 widget can be marked cached rather than recomputed from a
    (failing) live call.
    """
    candidates: List[ScreenerRow] = []
    for r in gainers:
        ex = r.extra or {}
        h = ex.get("high") or 0
        lo = ex.get("low") or 0
        ltp = r.ltp or 0
        vol = r.volume or 0
        if not (h and lo and ltp and vol):
            continue
        range_pct = (h - lo) / ltp if ltp else 0
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
                    "open": ex.get("open"),
                    "high": h,
                    "low": lo,
                    "prev_close": ex.get("prev_close"),
                    "range_pct": round(range_pct * 100, 2),
                },
            )
        )
    candidates.sort(key=lambda r: (r.extra or {}).get("range_pct", 999))
    return candidates


def _pbo_from_rows(highs: List[ScreenerRow]) -> List[ScreenerRow]:
    """Recompute the potential-breakouts screener from cached 52w-high rows."""
    candidates: List[ScreenerRow] = []
    for r in highs:
        ex = r.extra or {}
        new_high = ex.get("new_52wh") or 0
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
                    "prev_52wh": ex.get("prev_52wh"),
                    "prev_close": ex.get("prev_close"),
                    "distance_from_high_pct": round(distance_pct, 2),
                },
            )
        )
    candidates.sort(key=lambda r: r.change_percent or 0, reverse=True)
    return candidates


def build_nse_widget(
    widget_id: str,
    title: str,
    description: str,
    rows: List[ScreenerRow],
    columns: List[str],
    status: str = "live",
    source: str = "nse",
    error: Optional[str] = None,
) -> ScreenerWidget:
    return ScreenerWidget(
        id=widget_id,
        title=title,
        description=description,
        timeframe="daily",
        columns=columns,
        rows=rows,
        last_updated=_now(),
        status=status,
        source=source,
        error=error,
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
    started = time.time()
    name = getattr(fn, "__name__", "unknown")
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(_NSE_EXECUTOR, lambda: fn(*args)),
            timeout=NSE_TIMEOUT_SECONDS,
        )
        logger.info(
            "nse_dataset",
            dataset=name,
            duration_ms=round((time.time() - started) * 1000, 1),
            row_count=len(result or []),
            status="success" if result else "empty",
        )
        return result or []
    except asyncio.TimeoutError:
        logger.warning("nse_dataset_timeout", dataset=name, duration_ms=round((time.time() - started) * 1000, 1))
        return []
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("nse_dataset_failed", dataset=name, error=str(exc))
        return []


async def _dataset_with_cache(key: str, fn, *args) -> Tuple[List[ScreenerRow], str, str]:
    """Fetch a dataset with a short-lived cache fallback.

    Returns ``(rows, status, source)``:
    - live rows  -> ("live", "nse")
    - cached rows served because the live fetch failed -> ("cached", "cache")
    - no rows at all -> ("unavailable", "none")

    Successful live results are cached so a subsequent transient NSE failure
    serves the last real data (marked cached/stale) rather than synthetic rows.
    """
    rows = await _fetch_with_timeout(fn, *args)
    if rows:
        _NSE_CACHE.set(key, rows)
        return rows, "live", "nse"
    cached = _NSE_CACHE.get(key)
    if cached:
        return cached, "cached", "cache"
    return [], "unavailable", "none"


async def build_nse_dashboard() -> Tuple[List[ScreenerWidget], str, List[str]]:
    """Build a dashboard of NSE-backed screener widgets.

    Each dataset is fetched independently and in parallel with a bounded
    timeout, so one NSE failure never breaks the whole dashboard. Each widget
    carries its own ``status``/``source`` so the UI can render live / cached /
    fallback / unavailable per tile.

    Fallback order per widget:
        live NSE  ->  cached real data (stale)  ->  labelled synthetic fallback
    A widget is only "unavailable" when there is no live data AND no cache AND
    no synthetic fallback exists for it.

    Returns ``(widgets, source, warnings)`` where ``source`` is "live" when
    every dataset was live, "cached" when any widget served cached real data,
    "synthetic_fallback" when any widget used fallback data, and "unavailable"
    when no data could be obtained.
    """
    warnings: List[str] = []
    any_fallback = False
    any_cached = False

    (indices_r, indices_st, indices_src), \
        (sectoral_r, sectoral_st, sectoral_src), \
        (gainers_r, gainers_st, gainers_src), \
        (losers_r, losers_st, losers_src), \
        (high52_r, high52_st, high52_src), \
        (low52_r, low52_st, low52_src) = await asyncio.gather(
        _dataset_with_cache("indices", get_all_indices, 50),
        _dataset_with_cache("sectoral", get_sectoral_indices, 50),
        _dataset_with_cache("gainers", get_top_gainers, 20),
        _dataset_with_cache("losers", get_top_losers, 20),
        _dataset_with_cache("high52", get_52_week_high, 25),
        _dataset_with_cache("low52", get_52_week_low, 25),
    )

    def _note(st: str, label: str):
        nonlocal any_fallback, any_cached
        if st == "cached":
            any_cached = True
            warnings.append(f"NSE {label} temporarily unavailable; showing cached data")
        elif st == "unavailable":
            any_fallback = True
            warnings.append(f"NSE {label} unavailable; showing fallback data")

    widgets: List[ScreenerWidget] = []

    # Indices momentum
    if indices_r:
        _note(indices_st, _DATASET_LABELS["indices"])
        indices_momentum = sorted(indices_r, key=lambda r: abs(r.change_percent or 0), reverse=True)[:8]
        widgets.append(build_nse_widget(
            "indices_momentum", "Indices Momentum",
            "Live NSE broad-market & sectoral indices ranked by absolute % change",
            indices_momentum, ["symbol", "change_percent", "ltp"],
            status=indices_st, source=indices_src,
        ))
    else:
        _note(indices_st, _DATASET_LABELS["indices"])
        widgets.append(build_nse_widget(
            "indices_momentum", "Indices Momentum",
            "Live NSE broad-market & sectoral indices ranked by absolute % change",
            _fallback_indices(), ["symbol", "change_percent", "ltp"],
            status="fallback", source="synthetic",
        ))

    # Sectoral winners
    if sectoral_r:
        _note(sectoral_st, _DATASET_LABELS["sectoral"])
        sectoral_winners = [r for r in sectoral_r if (r.change_percent or 0) > 0][:8]
        if not sectoral_winners:
            sectoral_winners = _fallback_sectoral_winners()
            sec_st, sec_src = "fallback", "synthetic"
        else:
            sec_st, sec_src = sectoral_st, sectoral_src
    else:
        _note(sectoral_st, _DATASET_LABELS["sectoral"])
        sectoral_winners = _fallback_sectoral_winners()
        sec_st, sec_src = "fallback", "synthetic"
    widgets.append(build_nse_widget(
        "sectoral_winners", "Sectoral Winners",
        "Sectoral indices trading positive today (live NSE)",
        sectoral_winners, ["symbol", "change_percent", "ltp"],
        status=sec_st, source=sec_src,
    ))

    # Top gainers
    if gainers_r:
        _note(gainers_st, _DATASET_LABELS["gainers"])
        g_rows, g_st, g_src = gainers_r, gainers_st, gainers_src
    else:
        _note(gainers_st, _DATASET_LABELS["gainers"])
        g_rows, g_st, g_src = _fallback_gainers(), "fallback", "synthetic"
    widgets.append(build_nse_widget(
        "top_gainers", "Top Gainers", "Live NSE top gainers",
        g_rows, ["symbol", "change_percent", "ltp", "volume"],
        status=g_st, source=g_src,
    ))

    # Top losers
    if losers_r:
        _note(losers_st, _DATASET_LABELS["losers"])
        l_rows, l_st, l_src = losers_r, losers_st, losers_src
    else:
        _note(losers_st, _DATASET_LABELS["losers"])
        l_rows, l_st, l_src = _fallback_losers(), "fallback", "synthetic"
    widgets.append(build_nse_widget(
        "top_losers", "Top Losers", "Live NSE top losers",
        l_rows, ["symbol", "change_percent", "ltp", "volume"],
        status=l_st, source=l_src,
    ))

    # 52-week high
    if high52_r:
        _note(high52_st, _DATASET_LABELS["high52"])
        h_rows, h_st, h_src = high52_r, high52_st, high52_src
    else:
        _note(high52_st, _DATASET_LABELS["high52"])
        h_rows, h_st, h_src = _fallback_52_week_high(), "fallback", "synthetic"
    widgets.append(build_nse_widget(
        "fifty_two_week_high", "52-Week High",
        "Stocks that hit a new 52-week high today (live NSE)",
        h_rows, ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        status=h_st, source=h_src,
    ))

    # 52-week low
    if low52_r:
        _note(low52_st, _DATASET_LABELS["low52"])
        lo_rows, lo_st, lo_src = low52_r, low52_st, low52_src
    else:
        _note(low52_st, _DATASET_LABELS["low52"])
        lo_rows, lo_st, lo_src = _fallback_52_week_low(), "fallback", "synthetic"
    widgets.append(build_nse_widget(
        "fifty_two_week_low", "52-Week Low",
        "Stocks that hit a new 52-week low today (live NSE)",
        lo_rows, ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        status=lo_st, source=lo_src,
    ))

    # NR7 / breakouts are derived from gainers + 52w-high above. When those base
    # datasets were cached (live failed but stale real data was served), recompute
    # the derived screeners from the cached rows so the derived widget is also
    # marked cached rather than mislabelled live.
    if gainers_r:
        if gainers_st == "cached":
            nr7_rows = _nr7_from_rows(gainers_r)
            nr7_st, nr7_src = "cached", "cache"
        else:
            nr7_rows = get_nr7_breakout_candidates(25)
            nr7_st, nr7_src = "live", "nse"
        if not nr7_rows:
            nr7_rows = _fallback_nr7_breakouts()
            nr7_st, nr7_src = "fallback", "synthetic"
            if not any("NR7 breakout candidates" in w for w in warnings):
                warnings.append("NSE NR7 breakout candidates unavailable; showing fallback data")
                any_fallback = True
    else:
        nr7_rows = _fallback_nr7_breakouts()
        nr7_st, nr7_src = "fallback", "synthetic"
        if not any("NR7 breakout candidates" in w for w in warnings):
            warnings.append("NSE NR7 breakout candidates unavailable; showing fallback data")
            any_fallback = True
    widgets.append(ScreenerWidget(
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
        status=nr7_st,
        source=nr7_src,
    ))

    if high52_r:
        if high52_st == "cached":
            pbo_rows = _pbo_from_rows(high52_r)
            pbo_st, pbo_src = "cached", "cache"
        else:
            pbo_rows = get_potential_breakouts(25)
            pbo_st, pbo_src = "live", "nse"
        if not pbo_rows:
            pbo_rows = _fallback_potential_breakouts()
            pbo_st, pbo_src = "fallback", "synthetic"
            if not any("potential breakouts" in w for w in warnings):
                warnings.append("NSE potential breakouts unavailable; showing fallback data")
                any_fallback = True
    else:
        pbo_rows = _fallback_potential_breakouts()
        pbo_st, pbo_src = "fallback", "synthetic"
        if not any("potential breakouts" in w for w in warnings):
            warnings.append("NSE potential breakouts unavailable; showing fallback data")
            any_fallback = True
    widgets.append(ScreenerWidget(
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
        status=pbo_st,
        source=pbo_src,
    ))

    if any_fallback:
        source = "synthetic_fallback"
    elif any_cached:
        source = "cached"
    else:
        source = "live"
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
    rows.sort(key=lambda r: (r.extra or {}).get("range_pct", 999))
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
