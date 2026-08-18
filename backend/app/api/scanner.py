from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
import time
import structlog

from app.schemas.scanner import (
    ScanResult,
    ScanSummary,
    ScanType,
    SignalDirection,
    ScanFilters,
    BreakoutSignal,
    EMACrossSignal,
    VolumeSignal,
    OISignal,
    ScreenerDashboard,
    ScreenerDashboardResponse,
    ScreenerWidget,
    ScreenerRow,
)
from app.services.screener_engine import (
    build_screener_widget,
    list_screener_slugs,
    candles_for,
    _UNIVERSE,
)
from app.services.scanner_engine import (
    scan_market as _scan_market,
    scan_breakouts as _scan_breakouts,
    scan_ema_crosses as _scan_ema_crosses,
    scan_volume_spikes as _scan_volume_spikes,
    scan_oi_buildup as _scan_oi_buildup,
)
from app.services.nse_service import (
    build_nse_dashboard,
    get_nr7_breakout_candidates,
    get_potential_breakouts,
)
from app.services import indicators
from datetime import datetime as _dt

logger = structlog.get_logger()
router = APIRouter()

# Scanner results are deterministic (computed from seeded OHLC + indicators)
# but the computation is non-trivial; cache for a short window so repeated
# dashboard refreshes don't recompute the whole universe.
from app.services.cache import TTLCache

_SCAN_CACHE: TTLCache = TTLCache(ttl=60)


def _log_scan(scanner: str, provider: str, started: float, source: str,
              row_count: int, status: str = "success", error: str = ""):
    logger.info(
        "scanner_request",
        scanner=scanner,
        provider=provider,
        duration_ms=round((time.time() - started) * 1000, 1),
        source=source,
        row_count=row_count,
        status=status,
        error=error,
    )


def _active_source() -> str:
    """Active market-data source label for scan logging."""
    from app.services import market_data

    return market_data.get_market_data_provider()


@router.get("", response_model=List[ScanResult])
async def scan_market(
    scan_types: Optional[str] = Query(None, description="Comma-separated scan types"),
    min_confidence: float = Query(60.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
):
    """Scan market for trading opportunities.

    Signals are computed deterministically from the screener engine's OHLC
    history + real technical indicators (EMA, RSI, ATR, volume). No random
    market values are used; a symbol only appears when a real condition is met.
    """
    started = time.time()
    logger.info("scanning_market", scan_types=scan_types, min_confidence=min_confidence)

    if scan_types:
        types = [ScanType(t.strip()) for t in scan_types.split(",")]
    else:
        types = list(ScanType)

    cache_key = ("scan_market", tuple(t.value for t in types), min_confidence, limit)
    results = _SCAN_CACHE.get(cache_key)
    if results is None:
        results = _scan_market(scan_types=types, min_confidence=min_confidence, limit=limit)
        _SCAN_CACHE.set(cache_key, results)

    _log_scan("scan_market", "screener_engine", started, _active_source(), len(results))
    return results


@router.get("/summary", response_model=ScanSummary)
async def get_scan_summary(
    scan_types: Optional[str] = Query(None),
):
    """Get summary of scan results (deterministic)."""
    started = time.time()
    logger.info("getting_scan_summary")

    if scan_types:
        types = [ScanType(t.strip()) for t in scan_types.split(",")]
    else:
        types = None

    results = _scan_market(scan_types=types, min_confidence=0.0, limit=200)

    bullish = sum(1 for r in results if r.direction == SignalDirection.BULLISH)
    bearish = sum(1 for r in results if r.direction == SignalDirection.BEARISH)
    neutral = sum(1 for r in results if r.direction == SignalDirection.NEUTRAL)

    by_type = {}
    for r in results:
        by_type[r.scan_type.value] = by_type.get(r.scan_type.value, 0) + 1

    _log_scan("scan_summary", "screener_engine", started, _active_source(), len(results))
    return ScanSummary(
        total_results=len(results),
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        top_signals=results[:10],
        by_type=by_type,
    )


@router.get("/breakouts", response_model=List[BreakoutSignal])
async def scan_breakouts(limit: int = Query(20, ge=1, le=50)):
    """Scan for breakout opportunities (deterministic 20-day high/low break)."""
    started = time.time()
    logger.info("scanning_breakouts")
    results = _scan_breakouts(limit=limit)
    _log_scan("breakouts", "screener_engine", started, _active_source(), len(results))
    return results


@router.get("/ema-crosses", response_model=List[EMACrossSignal])
async def scan_ema_crosses(limit: int = Query(20, ge=1, le=50)):
    """Scan for EMA crossover signals (deterministic 9/21 EMA)."""
    started = time.time()
    logger.info("scanning_ema_crosses")
    results = _scan_ema_crosses(limit=limit)
    _log_scan("ema_crosses", "screener_engine", started, _active_source(), len(results))
    return results


@router.get("/volume", response_model=List[VolumeSignal])
async def scan_volume_spikes(limit: int = Query(20, ge=1, le=50)):
    """Scan for unusual volume activity (deterministic 2x 20-day avg)."""
    started = time.time()
    logger.info("scanning_volume_spikes")
    results = _scan_volume_spikes(limit=limit)
    _log_scan("volume_spikes", "screener_engine", started, _active_source(), len(results))
    return results


@router.get("/oi-buildup", response_model=List[OISignal])
async def scan_oi_buildup(limit: int = Query(20, ge=1, le=50)):
    """Scan for OI buildup (deterministic price+volume proxy; clearly labelled)."""
    started = time.time()
    logger.info("scanning_oi_buildup")
    results = _scan_oi_buildup(limit=limit)
    _log_scan("oi_buildup", "screener_engine", started, _active_source(), len(results))
    return results


# ---------------------------------------------------------------------------
# Chartink-style multi-widget scan dashboard (deterministic)
# ---------------------------------------------------------------------------

_INDEX_UNIVERSE = [
    {"symbol": "CNXREALTY", "name": "Nifty Realty", "base": 1050.0},
    {"symbol": "NIFTYPSE", "name": "Nifty PSE", "base": 4320.0},
    {"symbol": "NIFTYPSUBANK", "name": "Nifty PSU Bank", "base": 6120.0},
    {"symbol": "NIFTYINDDEFENCE", "name": "Nifty India Defence", "base": 2340.0},
    {"symbol": "NIFTYMETAL", "name": "Nifty Metal", "base": 9120.0},
    {"symbol": "NIFTYENERGY", "name": "Nifty Energy", "base": 41800.0},
    {"symbol": "NIFTYMIDCAP100", "name": "Nifty Midcap 100", "base": 56200.0},
    {"symbol": "INDIAVIX", "name": "India VIX", "base": 14.5},
]


def _det_row(meta: dict, candles) -> ScreenerRow:
    """Build a ScreenerRow from deterministic OHLC (no random values)."""
    last = candles[-1]
    prev = candles[-2]
    change_percent = round(((last.close - prev.close) / prev.close) * 100, 2) if prev.close else 0.0
    return ScreenerRow(
        symbol=meta["symbol"],
        name=meta.get("name"),
        ltp=round(last.close, 2),
        change_percent=change_percent,
        volume=last.volume,
    )


def _det_index_row(meta: dict) -> ScreenerRow:
    """Index row from REAL OHLC (yfinance index) via the unified resolver."""
    candles, _src = candles_for(meta["symbol"])
    if not candles or len(candles) < 2:
        return ScreenerRow(symbol=meta["symbol"], name=meta.get("name"))
    return _det_row(meta, candles)


def _det_stock_rows(universe, n, *, change_filter=None, sort_key=None, extra_fn=None):
    """Pick the top-n stock rows matching a filter, computed from REAL OHLC."""
    rows = []
    for meta in universe:
        candles, _src = candles_for(meta["symbol"])
        if not candles or len(candles) < 2:
            continue
        row = _det_row(meta, candles)
        if extra_fn:
            extra = extra_fn(meta, candles)
            row.extra = {**(row.extra or {}), **extra}
        if change_filter and not change_filter(row.change_percent or 0):
            continue
        rows.append(row)
    if sort_key:
        rows.sort(key=sort_key, reverse=True)
    return rows[:n]


def _build_dashboard(dashboard_id: str) -> ScreenerDashboard:
    """Deterministic multi-widget dashboard computed from seeded OHLC + indicators."""
    now = datetime.utcnow()

    index_rows = [_det_index_row(m) for m in _INDEX_UNIVERSE]
    indices_momentum = sorted(index_rows, key=lambda r: abs(r.change_percent or 0), reverse=True)[:6]
    sectoral_winners = [r for r in index_rows if (r.change_percent or 0) > 0][:6]

    top_gainers = _det_stock_rows(
        _UNIVERSE, 8,
        change_filter=lambda pct: pct > 0.5,
        sort_key=lambda r: r.change_percent or 0,
    )
    top_losers = _det_stock_rows(
        _UNIVERSE, 8,
        change_filter=lambda pct: pct < -0.5,
        sort_key=lambda r: r.change_percent or 0,
    )

    def volume_extra(meta, candles):
        if len(candles) < 21:
            return {"volume_factor": 1.0, "vwap": round(candles[-1].close, 2)}
        recent = candles[-21:-1]
        avg = sum(c.volume for c in recent) / 20 if recent else 0
        factor = round(candles[-1].volume / avg, 2) if avg else 1.0
        typical = sum((c.high + c.low + c.close) / 3 * c.volume for c in candles[-20:]) / max(
            1, sum(c.volume for c in candles[-20:])
        )
        return {"volume_factor": factor, "vwap": round(typical, 2)}

    volume_surge = _det_stock_rows(
        _UNIVERSE, 8,
        sort_key=lambda r: (r.extra or {}).get("volume_factor", 0),
        extra_fn=volume_extra,
    )

    def rsi_extra(meta, candles):
        closes = [c.close for c in candles]
        rsi_series = indicators.calculate_rsi(closes, 14)
        rsi = rsi_series[-1] if rsi_series and rsi_series[-1] is not None else 50.0
        ema20 = indicators.calculate_ema(closes, 20)
        ema = ema20[-1] if ema20 and ema20[-1] is not None else candles[-1].close
        return {"rsi": round(rsi, 2), "ema20": round(ema, 2)}

    all_rsi = _det_stock_rows(_UNIVERSE, len(_UNIVERSE), extra_fn=rsi_extra)
    rsi_oversold = [r for r in all_rsi if (r.extra or {}).get("rsi", 50) < 35][:6]
    rsi_overbought = [r for r in all_rsi if (r.extra or {}).get("rsi", 50) > 65][:6]

    def high_extra(meta, candles):
        if len(candles) < 200:
            return {"pct_from_high": 0.0}
        max200 = max(c.high for c in candles[-200:])
        pct = ((max200 - candles[-1].close) / max200) * 100 if max200 else 0.0
        return {"pct_from_high": round(pct, 2)}

    fifty_two_week_high = _det_stock_rows(
        _UNIVERSE, 8,
        extra_fn=high_extra,
        sort_key=lambda r: (r.extra or {}).get("pct_from_high", 999),
    )

    intraday_breakout = _det_stock_rows(
        _UNIVERSE, 6,
        change_filter=lambda pct: pct > 0.3,
        sort_key=lambda r: r.change_percent or 0,
    )

    widgets = [
        ScreenerWidget(
            id="indices_momentum", title="Indices Momentum",
            description="Sectoral indices ranked by absolute % change (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp"],
            rows=indices_momentum, last_updated=now,
        ),
        ScreenerWidget(
            id="sectoral_winners", title="Sectoral Winners",
            description="Sectoral indices trading positive (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp"],
            rows=sectoral_winners, last_updated=now,
        ),
        ScreenerWidget(
            id="top_gainers", title="Top Gainers",
            description="Stocks with the highest % change (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp", "volume"],
            rows=top_gainers, last_updated=now,
        ),
        ScreenerWidget(
            id="top_losers", title="Top Losers",
            description="Stocks with the most negative % change (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp", "volume"],
            rows=top_losers, last_updated=now,
        ),
        ScreenerWidget(
            id="volume_surge", title="Volume Surge",
            description="Unusual volume activity with volume factor (deterministic)",
            timeframe="daily",
            columns=["symbol", "change_percent", "volume", "extra.volume_factor", "extra.vwap"],
            rows=volume_surge, last_updated=now,
        ),
        ScreenerWidget(
            id="rsi_oversold", title="RSI Oversold",
            description="Stocks with RSI below 35 (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp", "extra.rsi"],
            rows=rsi_oversold, last_updated=now,
        ),
        ScreenerWidget(
            id="rsi_overbought", title="RSI Overbought",
            description="Stocks with RSI above 65 (deterministic)",
            timeframe="daily", columns=["symbol", "change_percent", "ltp", "extra.rsi"],
            rows=rsi_overbought, last_updated=now,
        ),
        ScreenerWidget(
            id="fifty_two_week_high", title="Near 52-Week High",
            description="Stocks trading close to their 52-week high (deterministic)",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.pct_from_high", "volume"],
            rows=fifty_two_week_high, last_updated=now,
        ),
        ScreenerWidget(
            id="intraday_breakout", title="Intraday Breakout",
            description="Stocks with the strongest up-move today (deterministic)",
            timeframe="15_minute", columns=["symbol", "change_percent", "ltp", "volume"],
            rows=intraday_breakout, last_updated=now,
        ),
    ]

    return ScreenerDashboard(
        id=dashboard_id,
        name="System",
        author="ChartAnalytics",
        description="Multi-widget market scan dashboard (deterministic, Chartink-style)",
        widgets=widgets,
    )


@router.get("/dashboard/{dashboard_id}", response_model=ScreenerDashboard)
async def get_scan_dashboard(dashboard_id: str):
    """Return a Chartink-style multi-widget scan dashboard.

    Aggregates several screener widgets (indices momentum, top gainers/losers,
    volume surge, RSI extremes, 52-week highs, intraday breakouts) so the
    frontend can render them side-by-side like chartink.com/dashboard/<id>.
    """
    logger.info("fetching_scan_dashboard", dashboard_id=dashboard_id)
    return _build_dashboard(dashboard_id)


@router.get("/screeners", response_model=List[str])
async def get_screener_slugs():
    """List available Chartink-style screener slugs."""
    logger.info("listing_screeners")
    return list_screener_slugs()


@router.get("/screener/{slug}", response_model=ScreenerWidget)
async def run_screener(slug: str, limit: int = Query(25, ge=1, le=100)):
    """Run a Chartink-style screener by slug and return matching rows.

    The two headline screeners (NR7 breakout, potential breakouts) are built
    from LIVE NSE data; any other slug falls back to the synthetic engine.
    """
    logger.info("running_screener", slug=slug, limit=limit)

    if slug == "copy-morning-scanner-for-buy-nr7-based-breakout-8":
        rows = get_nr7_breakout_candidates(limit=limit)
        return ScreenerWidget(
            id=slug,
            title="Morning Scanner - NR7 Breakout (Buy)",
            description=(
                "Today's advancing stocks with the tightest intraday range "
                "(NR7 proxy) and a close near the day high. Live NSE data."
            ),
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "volume", "extra.range_pct"],
            rows=rows,
            last_updated=_dt.utcnow(),
        )

    if slug == "potential-breakouts":
        rows = get_potential_breakouts(limit=limit)
        return ScreenerWidget(
            id=slug,
            title="Potential Breakouts",
            description=(
                "Stocks that printed a new 52-week high today (live NSE), "
                "ranked by % change."
            ),
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.new_52wh", "extra.distance_from_high_pct"],
            rows=rows,
            last_updated=_dt.utcnow(),
        )

    widget = build_screener_widget(slug, limit=limit)
    if widget is None:
        raise HTTPException(status_code=404, detail=f"Screener '{slug}' not found")
    return widget


@router.get("/nse-dashboard", response_model=ScreenerDashboardResponse)
async def get_nse_dashboard():
    """Live NSE-backed scan dashboard (Chartink-style).

    Combines live nsetools data (top gainers/losers, all indices, 52-week
    high/low) with the real-formula Chartink screeners (NR7 breakout,
    potential breakouts). Each NSE dataset is fetched with a bounded timeout and
    falls back to clearly-labelled synthetic data when NSE is unreachable, so the
    endpoint always returns a valid response. ``source`` and ``warnings`` tell the
    UI exactly how much of the data is live.
    """
    logger.info("fetching_nse_dashboard")
    widgets, source, warnings = await build_nse_dashboard()
    dashboard = ScreenerDashboard(
        id="nse-system",
        name="System (NSE Live)" if source == "live" else "System (NSE Fallback)",
        author="ChartAnalytics",
        description="Live NSE data via nsetools + Chartink-style formula screeners",
        widgets=widgets,
    )
    return ScreenerDashboardResponse(
        success=True,
        source=source,
        data=dashboard,
        warnings=warnings,
        generated_at=_dt.utcnow(),
        data_timestamp=_dt.utcnow(),
        is_stale=False,
    )
