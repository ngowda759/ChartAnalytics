from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
import random
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
)
from app.services.nse_service import (
    build_nse_dashboard,
    get_nr7_breakout_candidates,
    get_potential_breakouts,
)
from datetime import datetime as _dt

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[ScanResult])
async def scan_market(
    scan_types: Optional[str] = Query(None, description="Comma-separated scan types"),
    min_confidence: float = Query(60.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
):
    """Scan market for trading opportunities"""
    logger.info("scanning_market", scan_types=scan_types, min_confidence=min_confidence)

    if scan_types:
        types = [ScanType(t.strip()) for t in scan_types.split(",")]
    else:
        types = list(ScanType)

    symbols = [
        {"symbol": "NIFTY", "name": "NIFTY 50", "price": 24567.85},
        {"symbol": "BANKNIFTY", "name": "NIFTY Bank", "price": 52456.70},
        {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2967.50},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "price": 1689.30},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "price": 1124.75},
        {"symbol": "INFOSYS", "name": "Infosys", "price": 1834.20},
        {"symbol": "TCS", "name": "TCS", "price": 4123.45},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "price": 1789.60},
        {"symbol": "SBIN", "name": "State Bank of India", "price": 823.45},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "price": 1456.30},
    ]

    results = []

    for sym in symbols:
        for scan_type in types:
            confidence = random.uniform(55, 95)
            if confidence < min_confidence:
                continue

            direction = random.choice(
                [
                    SignalDirection.BULLISH,
                    SignalDirection.BEARISH,
                    SignalDirection.NEUTRAL,
                ]
            )

            results.append(
                ScanResult(
                    id=f"{sym['symbol']}_{scan_type.value}_{len(results)}",
                    symbol=sym["symbol"],
                    name=sym["name"],
                    scan_type=scan_type,
                    direction=direction,
                    confidence=round(confidence, 1),
                    price=round(sym["price"] * (1 + random.uniform(-0.02, 0.02)), 2),
                    change_percent=round(random.uniform(-3, 3), 2),
                    volume_ratio=round(random.uniform(1.2, 3.5), 2),
                    details={
                        "atr": round(sym["price"] * 0.015, 2),
                        "rsi": round(random.uniform(30, 70), 2),
                        "ema_20": round(
                            sym["price"] * (1 + random.uniform(-0.02, 0.02)), 2
                        ),
                    },
                    timestamp=datetime.utcnow(),
                )
            )

    # Sort by confidence
    results.sort(key=lambda x: x.confidence, reverse=True)

    return results[:limit]


@router.get("/summary", response_model=ScanSummary)
async def get_scan_summary(
    scan_types: Optional[str] = Query(None),
):
    """Get summary of scan results"""
    logger.info("getting_scan_summary")

    results = await scan_market(scan_types=scan_types, limit=100)

    bullish = sum(1 for r in results if r.direction == SignalDirection.BULLISH)
    bearish = sum(1 for r in results if r.direction == SignalDirection.BEARISH)
    neutral = sum(1 for r in results if r.direction == SignalDirection.NEUTRAL)

    by_type = {}
    for r in results:
        by_type[r.scan_type.value] = by_type.get(r.scan_type.value, 0) + 1

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
    """Scan for breakout opportunities"""
    logger.info("scanning_breakouts")

    symbols = [
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
        {"symbol": "ICICIBANK", "price": 1124.75},
        {"symbol": "INFOSYS", "price": 1834.20},
        {"symbol": "TCS", "price": 4123.45},
    ]

    results = []
    for sym in symbols:
        breakout_price = sym["price"] * (1 + random.uniform(0.005, 0.02))
        current_price = sym["price"] * (1 + random.uniform(-0.01, 0.01))

        results.append(
            BreakoutSignal(
                symbol=sym["symbol"],
                type=random.choice(["resistance", "support"]),
                breakout_price=round(breakout_price, 2),
                current_price=round(current_price, 2),
                distance_percent=round(
                    ((current_price - breakout_price) / breakout_price) * 100, 2
                ),
                volume_ratio=round(random.uniform(1.5, 3.0), 2),
                atr=round(sym["price"] * 0.015, 2),
                confidence=round(random.uniform(60, 85), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]


@router.get("/ema-crosses", response_model=List[EMACrossSignal])
async def scan_ema_crosses(limit: int = Query(20, ge=1, le=50)):
    """Scan for EMA crossover signals"""
    logger.info("scanning_ema_crosses")

    symbols = [
        {"symbol": "NIFTY", "price": 24567.85},
        {"symbol": "BANKNIFTY", "price": 52456.70},
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
    ]

    results = []
    for sym in symbols:
        fast_ema = sym["price"] * (1 + random.uniform(-0.01, 0.01))
        slow_ema = sym["price"] * (1 + random.uniform(-0.02, 0.02))

        results.append(
            EMACrossSignal(
                symbol=sym["symbol"],
                cross_type=random.choice(["golden_cross", "death_cross"]),
                fast_ema=round(fast_ema, 2),
                slow_ema=round(slow_ema, 2),
                price=round(sym["price"], 2),
                distance_from_cross=round(random.uniform(-1, 1), 2),
                rsi=round(random.uniform(40, 65), 2),
                volume_ratio=round(random.uniform(1.2, 2.5), 2),
                confidence=round(random.uniform(55, 80), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]


@router.get("/volume", response_model=List[VolumeSignal])
async def scan_volume_spikes(limit: int = Query(20, ge=1, le=50)):
    """Scan for unusual volume activity"""
    logger.info("scanning_volume_spikes")

    symbols = [
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "TATASTEEL", "price": 156.80},
        {"symbol": "ADANIPORTS", "price": 1289.45},
        {"symbol": "SBIN", "price": 823.45},
        {"symbol": "BHARTIARTL", "price": 1456.30},
    ]

    results = []
    for sym in symbols:
        avg_volume = random.randint(5000000, 20000000)
        current_volume = int(avg_volume * random.uniform(1.5, 4.0))

        results.append(
            VolumeSignal(
                symbol=sym["symbol"],
                type=random.choice(["spike_up", "spike_down"]),
                current_volume=current_volume,
                avg_volume=avg_volume,
                volume_ratio=round(current_volume / avg_volume, 2),
                price_change=round(random.uniform(-3, 3), 2),
                delivery_percent=round(random.uniform(50, 85), 2),
                confidence=round(random.uniform(60, 85), 1),
            )
        )

    return sorted(results, key=lambda x: x.volume_ratio, reverse=True)[:limit]


@router.get("/oi-buildup", response_model=List[OISignal])
async def scan_oi_buildup(limit: int = Query(20, ge=1, le=50)):
    """Scan for OI buildup"""
    logger.info("scanning_oi_buildup")

    symbols = [
        {"symbol": "NIFTY", "price": 24567.85},
        {"symbol": "BANKNIFTY", "price": 52456.70},
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
    ]

    results = []
    for sym in symbols:
        change_call = random.randint(-50000, 100000)
        change_put = random.randint(-50000, 100000)

        if change_call > 0 and change_put > 0:
            oi_type = "buildup"
        elif change_call < 0 and change_put < 0:
            oi_type = "unwinding"
        else:
            oi_type = random.choice(["buildup", "unwinding"])

        results.append(
            OISignal(
                symbol=sym["symbol"],
                type=oi_type,
                change_call_oi=change_call,
                change_put_oi=change_put,
                price_change=round(random.uniform(-2, 2), 2),
                pcr=round(random.uniform(0.7, 1.3), 2),
                interpretation=(
                    "Bullish buildup" if change_call > change_put else "Bearish buildup"
                ),
                confidence=round(random.uniform(55, 80), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Chartink-style multi-widget scan dashboard
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

_STOCK_UNIVERSE = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "base": 2967.0},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "base": 1689.0},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "base": 1124.0},
    {"symbol": "INFY", "name": "Infosys", "base": 1834.0},
    {"symbol": "TCS", "name": "Tata Consultancy", "base": 4123.0},
    {"symbol": "SBIN", "name": "State Bank of India", "base": 823.0},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "base": 1456.0},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "base": 156.0},
    {"symbol": "ADANIPORTS", "name": "Adani Ports", "base": 1289.0},
    {"symbol": "PAYTM", "name": "Paytm (One97)", "base": 432.0},
    {"symbol": "NAUKRI", "name": "Info Edge", "base": 5870.0},
    {"symbol": "TITAN", "name": "Titan Company", "base": 3450.0},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam", "base": 1620.0},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "base": 7850.0},
    {"symbol": "JSWENERGY", "name": "JSW Energy", "base": 645.0},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance", "base": 2980.0},
    {"symbol": "PFC", "name": "Power Finance", "base": 478.0},
    {"symbol": "BHARATFORG", "name": "Bharat Forge", "base": 1342.0},
    {"symbol": "RECLTD", "name": "REC Limited", "base": 512.0},
    {"symbol": "INDUSTOWER", "name": "Indus Towers", "base": 398.0},
    {"symbol": "KAYNES", "name": "Kaynes Technology", "base": 4120.0},
    {"symbol": "BANKINDIA", "name": "Bank of India", "base": 118.0},
    {"symbol": "LICI", "name": "LIC India", "base": 845.0},
    {"symbol": "TMPV", "name": "Thomas Cook (TMPV)", "base": 232.0},
    {"symbol": "PREMIERENE", "name": "Premier Energies", "base": 478.0},
    {"symbol": "SYRMA", "name": "Syrma SGS", "base": 542.0},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "base": 12800.0},
    {"symbol": "KOTAKBANK", "name": "Kotak Bank", "base": 1780.0},
    {"symbol": "LT", "name": "Larsen & Toubro", "base": 3650.0},
    {"symbol": "NESTLEIND", "name": "Nestle India", "base": 2450.0},
]


def _perturbed_price(base: float) -> float:
    return round(base * (1 + random.uniform(-0.06, 0.06)), 2)


def _change_percent(bias: float = 0.0) -> float:
    return round(random.uniform(-4.5, 4.5) + bias, 2)


def _volume(base_price: float) -> int:
    return random.randint(500_000, 25_000_000)


def _rows(universe, n, *, change_filter=None, sort_key=None, extra_fn=None):
    picked = random.sample(universe, min(n, len(universe)))
    rows = []
    for item in picked:
        pct = _change_percent()
        if change_filter and not change_filter(pct):
            continue
        row = ScreenerRow(
            symbol=item["symbol"],
            name=item.get("name"),
            ltp=_perturbed_price(item["base"]),
            change_percent=pct,
            volume=_volume(item["base"]),
            extra=extra_fn(item) if extra_fn else None,
        )
        rows.append(row)
    if sort_key:
        rows.sort(key=sort_key, reverse=True)
    return rows


def _build_dashboard(dashboard_id: str) -> ScreenerDashboard:
    now = datetime.utcnow()

    indices_momentum = _rows(
        _INDEX_UNIVERSE, 6, sort_key=lambda r: abs(r.change_percent or 0)
    )
    sectoral_winners = _rows(
        _INDEX_UNIVERSE,
        6,
        change_filter=lambda pct: pct > 0,
        sort_key=lambda r: r.change_percent or 0,
    )

    top_gainers = _rows(
        _STOCK_UNIVERSE,
        8,
        change_filter=lambda pct: pct > 1.0,
        sort_key=lambda r: r.change_percent or 0,
    )
    top_losers = _rows(
        _STOCK_UNIVERSE,
        8,
        change_filter=lambda pct: pct < -1.0,
        sort_key=lambda r: r.change_percent or 0,
    )
    volume_surge = _rows(
        _STOCK_UNIVERSE,
        8,
        sort_key=lambda r: r.volume or 0,
        extra_fn=lambda item: {
            "volume_factor": round(random.uniform(1.5, 6.0), 2),
            "vwap": _perturbed_price(item["base"]),
        },
    )

    def rsi_extra(item):
        rsi = round(random.uniform(5, 95), 2)
        return {"rsi": rsi, "ema20": _perturbed_price(item["base"])}

    rsi_oversold = _rows(
        _STOCK_UNIVERSE, 6, extra_fn=rsi_extra, sort_key=lambda r: (r.extra or {}).get("rsi", 50)
    )
    rsi_oversold = [r for r in rsi_oversold if (r.extra or {}).get("rsi", 50) < 35][:6]

    rsi_overbought = _rows(
        _STOCK_UNIVERSE, 6, extra_fn=rsi_extra, sort_key=lambda r: (r.extra or {}).get("rsi", 50)
    )
    rsi_overbought = [r for r in rsi_overbought if (r.extra or {}).get("rsi", 50) > 65][:6]

    def high_extra(item):
        return {"pct_from_high": round(random.uniform(0.0, 2.0), 2)}

    fifty_two_week_high = _rows(
        _STOCK_UNIVERSE,
        8,
        extra_fn=high_extra,
        sort_key=lambda r: r.change_percent or 0,
    )

    intraday_breakout = _rows(
        _STOCK_UNIVERSE,
        6,
        change_filter=lambda pct: pct > 0.5,
        sort_key=lambda r: r.change_percent or 0,
    )

    widgets = [
        ScreenerWidget(
            id="indices_momentum",
            title="Indices Momentum",
            description="Sectoral indices ranked by absolute % change",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp"],
            rows=indices_momentum,
            last_updated=now,
        ),
        ScreenerWidget(
            id="sectoral_winners",
            title="Sectoral Winners",
            description="Sectoral indices trading positive today",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp"],
            rows=sectoral_winners,
            last_updated=now,
        ),
        ScreenerWidget(
            id="top_gainers",
            title="Top Gainers",
            description="Stocks with the highest % change today",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "volume"],
            rows=top_gainers,
            last_updated=now,
        ),
        ScreenerWidget(
            id="top_losers",
            title="Top Losers",
            description="Stocks with the most negative % change today",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "volume"],
            rows=top_losers,
            last_updated=now,
        ),
        ScreenerWidget(
            id="volume_surge",
            title="Volume Surge",
            description="Unusual volume activity with volume factor",
            timeframe="daily",
            columns=["symbol", "change_percent", "volume", "extra.volume_factor", "extra.vwap"],
            rows=volume_surge,
            last_updated=now,
        ),
        ScreenerWidget(
            id="rsi_oversold",
            title="RSI Oversold",
            description="Stocks with RSI below 35 - potential bounce candidates",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.rsi"],
            rows=rsi_oversold,
            last_updated=now,
        ),
        ScreenerWidget(
            id="rsi_overbought",
            title="RSI Overbought",
            description="Stocks with RSI above 65 - potential pullback candidates",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.rsi"],
            rows=rsi_overbought,
            last_updated=now,
        ),
        ScreenerWidget(
            id="fifty_two_week_high",
            title="Near 52-Week High",
            description="Stocks trading close to their 52-week high",
            timeframe="daily",
            columns=["symbol", "change_percent", "ltp", "extra.pct_from_high", "volume"],
            rows=fifty_two_week_high,
            last_updated=now,
        ),
        ScreenerWidget(
            id="intraday_breakout",
            title="Intraday Breakout",
            description="15-minute timeframe stocks breaking out intraday",
            timeframe="15_minute",
            columns=["symbol", "change_percent", "ltp", "volume"],
            rows=intraday_breakout,
            last_updated=now,
        ),
    ]

    return ScreenerDashboard(
        id=dashboard_id,
        name="System",
        author="Gautam Pandey",
        description="Multi-widget market scan dashboard (Chartink-style)",
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
