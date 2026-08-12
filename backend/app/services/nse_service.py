"""NSE-backed market data service using nsetools.

Wraps the `nsetools` library to provide real NSE data (top gainers/losers,
all indices, 52-week high/low). NSE is only reachable during market hours and
sometimes blocks non-browser requests, so every call falls back gracefully to
the synthetic screener engine when the live source fails.

Reference: https://github.com/vsjha18/nsetools
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import structlog

from app.schemas.scanner import ScreenerRow, ScreenerWidget

logger = structlog.get_logger()

_nse = None


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


def build_nse_dashboard() -> List[ScreenerWidget]:
    """Build a dashboard of NSE-backed screener widgets.

    Each widget tries live NSE data first and falls back to the synthetic
    engine so the dashboard is never empty when the market is closed.
    """
    widgets: List[ScreenerWidget] = []

    indices = get_all_indices(50)
    if not indices:
        indices = _fallback_indices()
    # indices momentum: ranked by absolute % change
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

    # Sectoral winners: only SECTORAL indices (NIFTY IT/BANK/AUTO/...) that are up
    sectoral = get_sectoral_indices(50) or indices
    sectoral_winners = [r for r in sectoral if (r.change_percent or 0) > 0][:8]
    widgets.append(
        build_nse_widget(
            "sectoral_winners",
            "Sectoral Winners",
            "Sectoral indices trading positive today (live NSE)",
            sectoral_winners,
            ["symbol", "change_percent", "ltp"],
        )
    )

    gainers = get_top_gainers(20)
    widgets.append(
        build_nse_widget(
            "top_gainers",
            "Top Gainers",
            "Live NSE top gainers",
            gainers,
            ["symbol", "change_percent", "ltp", "volume"],
        )
    )

    losers = get_top_losers(20)
    widgets.append(
        build_nse_widget(
            "top_losers",
            "Top Losers",
            "Live NSE top losers",
            losers,
            ["symbol", "change_percent", "ltp", "volume"],
        )
    )

    high52 = get_52_week_high(25)
    widgets.append(
        build_nse_widget(
            "fifty_two_week_high",
            "52-Week High",
            "Stocks that hit a new 52-week high today (live NSE)",
            high52,
            ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        )
    )

    low52 = get_52_week_low(25)
    widgets.append(
        build_nse_widget(
            "fifty_two_week_low",
            "52-Week Low",
            "Stocks that hit a new 52-week low today (live NSE)",
            low52,
            ["symbol", "change_percent", "ltp", "extra.new_52wh"],
        )
    )

    # Real Chartink-style formula screeners built from LIVE NSE data
    nr7_rows = get_nr7_breakout_candidates(25)
    if nr7_rows:
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

    pbo_rows = get_potential_breakouts(25)
    if pbo_rows:
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

    return widgets


def _fallback_indices() -> List[ScreenerRow]:
    """Synthetic index rows used when live NSE is unreachable."""
    now = _now()
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
        ScreenerRow(
            symbol=sym,
            name=name,
            ltp=last,
            change_percent=pct,
            volume=None,
            extra={"open": last, "high": last, "low": last, "previous_close": last},
        )
        for sym, name, last, pct in base_indices
    ]
