"""Unified market-data service (single source of truth).

All scanners, decision signals and agent analysis consume real OHLCV through
this module. The source can be yfinance (credential-free), Angel One, Kite or
the explicit mock/dev mode. Synthetic data is ONLY returned when the provider
is explicitly set to "mock"; otherwise a real-data failure yields ``None`` so
callers surface a truthful "unavailable" state instead of fabricated numbers.

Architecture::

    Provider (yfinance / Angel One / Kite / mock)
        |
        Adapter  -> normalized OHLCVBar / MarketQuote
        |
        Scanner Engine / Decision Signals / Agent Analysis / Dashboard

No caller knows which provider produced the data; it only reads the normalized
``Candle`` list + a ``source`` tag.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import structlog

from app.core.config import settings
from app.services.cache import TTLCache
from app.services.screener_engine import Candle

logger = structlog.get_logger()

# --- provider source labels -------------------------------------------------
SOURCE_YFINANCE = "yfinance"
SOURCE_ANGEL_ONE = "angel_one"
SOURCE_KITE = "kite"
SOURCE_NSE = "nse"
SOURCE_MOCK = "mock"
SOURCE_UNAVAILABLE = "unavailable"


@dataclass
class MarketQuote:
    """Normalized current quote from any provider."""

    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    close: float
    previous_close: float
    volume: int
    timestamp: datetime
    source: str = SOURCE_UNAVAILABLE


@dataclass
class OHLCVBar:
    """Normalized OHLCV bar (provider-agnostic)."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


# --- provider selection -----------------------------------------------------

_PROVIDER_OVERRIDE: Optional[str] = None  # test hook


def override_market_data_provider(name: Optional[str]) -> None:
    """Test-only hook to force a provider without touching env vars."""
    global _PROVIDER_OVERRIDE
    _PROVIDER_OVERRIDE = name


def get_market_data_provider() -> str:
    """Resolve the active provider name (lowercased).

    Priority: test override > settings.MARKET_DATA_PROVIDER.
    "auto" resolves to "yfinance" (no credentials required, verified working)
    unless broker credentials are present.
    """
    name = (_PROVIDER_OVERRIDE or settings.MARKET_DATA_PROVIDER or "auto").lower()
    if name == "auto":
        if settings.KITE_CONNECT_ENABLED and settings.KITE_CONNECT_API_KEY:
            return SOURCE_KITE
        if settings.ANGEL_ONE_ENABLED and settings.ANGEL_ONE_API_KEY:
            return SOURCE_ANGEL_ONE
        return SOURCE_YFINANCE
    return name


def is_mock_mode() -> bool:
    return get_market_data_provider() == SOURCE_MOCK


def mock_allowed_in_production() -> bool:
    """Production must not silently run on mock data."""
    if settings.is_production and is_mock_mode():
        return bool(settings.ALLOW_MOCK_IN_PRODUCTION)
    return True


def provider_display_name() -> str:
    p = get_market_data_provider()
    if p == SOURCE_MOCK:
        return "MOCK (EXPLICIT DEVELOPMENT MODE)"
    return p.upper()


# --- capability-based routing ---------------------------------------------
# Equity/index OHLCV stays on the (verified, credential-free) yfinance pipeline
# unless a broker is explicitly the primary provider. Realtime quotes, options
# and OI — which yfinance cannot supply for Indian markets — route to Angel
# One / Kite when those brokers are configured. This keeps the app fully
# functional without broker credentials while adding realtime/options/OI the
# moment credentials are present. yfinance is NEVER replaced globally.

# Providers capable of realtime ticks (WebSocket) when configured.
_REALTIME_PROVIDERS = (SOURCE_ANGEL_ONE, SOURCE_KITE)
# Providers capable of Indian option chain / OI when configured.
_OPTIONS_PROVIDERS = (SOURCE_ANGEL_ONE, SOURCE_KITE)


def angel_one_configured() -> bool:
    """True when Angel One credentials are present (no secrets exposed)."""
    return bool(
        settings.ANGEL_ONE_ENABLED
        and settings.ANGEL_ONE_API_KEY
        and settings.ANGEL_ONE_CLIENT_CODE
    )


def kite_configured() -> bool:
    """True when Kite Connect credentials are present (no secrets exposed)."""
    return bool(
        settings.KITE_CONNECT_ENABLED
        and settings.KITE_CONNECT_API_KEY
        and settings.KITE_CONNECT_ACCESS_TOKEN
    )


def get_realtime_provider() -> Optional[str]:
    """Resolve the provider used for realtime quotes (Angel One/Kite if set).

    Returns ``None`` when no realtime-capable broker is configured — callers
    then fall back to the yfinance quote snapshot (which is real, just not
    streaming) rather than fabricating a realtime feed.
    """
    primary = get_market_data_provider()
    if primary in _REALTIME_PROVIDERS and _broker_configured(primary):
        return primary
    if angel_one_configured():
        return SOURCE_ANGEL_ONE
    if kite_configured():
        return SOURCE_KITE
    return None


def get_options_provider() -> Optional[str]:
    """Resolve the provider used for options/OI (Angel One/Kite if set).

    Returns ``None`` when no derivatives-capable broker is configured — the
    options/OI endpoints then truthfully report unavailable (never fabricate).
    """
    primary = get_market_data_provider()
    if primary in _OPTIONS_PROVIDERS and _broker_configured(primary):
        return primary
    if angel_one_configured():
        return SOURCE_ANGEL_ONE
    if kite_configured():
        return SOURCE_KITE
    return None


def realtime_candles(symbol: str, interval: str, limit: int = 100):
    """Return candles from a live WebSocket stream when one is active, else None."""
    rt = get_realtime_provider()
    if rt != SOURCE_ANGEL_ONE:
        return None
    try:
        provider_obj = _build_broker(SOURCE_ANGEL_ONE)
    except Exception as exc:
        _last_error["realtime"] = f"angel_one init failed: {exc}"
        return None
    if provider_obj is None:
        return None
    candles = provider_obj.realtime_candles(symbol, interval, limit)
    return candles or None


# --- candles cache ----------------------------------------------------------

_CANDLE_CACHE: TTLCache = TTLCache(ttl=120)
_QUOTE_CACHE: TTLCache = TTLCache(ttl=30)
_last_success: Dict[str, float] = {}
_last_error: Dict[str, str] = {}


def clear_market_data_cache() -> None:
    _CANDLE_CACHE.clear()
    _QUOTE_CACHE.clear()


def last_success_at() -> Optional[datetime]:
    ts = max(_last_success.values()) if _last_success else None
    return datetime.utcfromtimestamp(ts) if ts else None


def last_error_for(op: str) -> Optional[str]:
    return _last_error.get(op)


# --- yfinance adapter -------------------------------------------------------

_YF_INDEX_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY 50": "^NSEI",
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY BANK": "^NSEBANK",
    "BANK NIFTY": "^NSEBANK",
    "FINNIFTY": "^CNXFIN",
    "NIFTY FIN SERVICE": "^CNXFIN",
    "NIFTY FIN SERVICES": "^CNXFIN",
    "NIFTY IT": "^CNXIT",
    "NIFTY MIDCAP": "^CNXMIDCAP",
    "INDIA VIX": "^INDIAVIX",
    "SENSEX": "^BSESN",
}

_YF_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "1d": "1d",
    "1w": "1wk",
}
_INTRADAY_INTERVALS = {"1m", "5m", "15m", "30m", "1h"}


def _yf_ticker(symbol: str) -> Optional[str]:
    key = symbol.strip().upper()
    if key in _YF_INDEX_MAP:
        return _YF_INDEX_MAP[key]
    if key and not key.startswith("^"):
        return f"{key}.NS"
    return None


def _yf_interval(interval: str) -> Optional[str]:
    i = interval.lower()
    return _YF_INTERVAL_MAP.get(i)


def _period_for(interval: str, limit: int) -> str:
    """Pick a yfinance period that yields at least `limit` bars."""
    i = interval.lower()
    if i in _INTRADAY_INTERVALS:
        # intraday history on yfinance is limited; 5d covers ~足够 for 15m
        if limit <= 60:
            return "1d"
        if limit <= 200:
            return "5d"
        return "60d"
    # daily/weekly
    if limit <= 30:
        return "1mo"
    if limit <= 100:
        return "3mo"
    if limit <= 250:
        return "1y"
    return "2y"


def _fetch_yfinance_ohlc_sync(symbol: str, interval: str, limit: int) -> List[OHLCVBar]:
    """Synchronous yfinance fetch. Returns [] on any failure."""
    import pandas as pd

    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - optional dep
        _last_error["ohlc"] = f"yfinance import failed: {exc}"
        logger.info("yfinance_unavailable", symbol=symbol, error=str(exc))
        return []

    ticker = _yf_ticker(symbol)
    yf_interval = _yf_interval(interval)
    if not ticker or not yf_interval:
        return []
    period = _period_for(interval, limit)

    try:
        df = yf.download(
            ticker,
            period=period,
            interval=yf_interval,
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        _last_error["ohlc"] = str(exc)
        logger.info("yfinance_ohlc_error", symbol=symbol, error=str(exc))
        return []

    if df is None or df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.tail(limit).sort_index()
    bars: List[OHLCVBar] = []
    for ts, row in df.iterrows():
        try:
            ts_dt = ts.to_pydatetime()
            if ts_dt.tzinfo is not None:
                ts_dt = ts_dt.astimezone(timezone.utc).replace(tzinfo=None)
            bars.append(
                OHLCVBar(
                    symbol=symbol,
                    timestamp=ts_dt,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row.get("Volume") or 0),
                )
            )
        except (TypeError, ValueError, KeyError):
            continue
    return bars


def _bars_to_candles(bars: List[OHLCVBar]) -> List[Candle]:
    return [
        Candle(
            date=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for b in bars
    ]


# --- public API: real candles ----------------------------------------------


def get_real_candles(
    symbol: str, interval: str = "1d", limit: int = 260
) -> Tuple[Optional[List[Candle]], str]:
    """Fetch real OHLCV candles for a symbol.

    Returns (candles, source). ``(None, "unavailable")`` when the live provider
    could not return data — callers must surface an unavailable state, never
    fabricate. Only the explicit mock provider returns synthetic candles here.
    """
    provider = get_market_data_provider()

    if provider == SOURCE_MOCK:
        from app.services.screener_engine import _generate_ohlc, _meta_for

        meta = _meta_for(symbol)
        base = meta["base"] if meta else 1000.0
        return _generate_ohlc(symbol, base, days=limit), SOURCE_MOCK

    # live providers
    cache_key = ("candles", symbol.upper(), interval, limit)
    cached = _CANDLE_CACHE.get(cache_key)
    if cached is not None:
        return cached, cached_source(cache_key)

    if provider == SOURCE_YFINANCE:
        bars = _fetch_yfinance_ohlc_sync(symbol, interval, limit)
    elif provider == SOURCE_ANGEL_ONE:
        bars = _fetch_via_broker("angel_one", symbol, interval, limit)
    elif provider == SOURCE_KITE:
        bars = _fetch_via_broker("kite", symbol, interval, limit)
    else:
        bars = []

    if not bars:
        return None, SOURCE_UNAVAILABLE

    candles = _bars_to_candles(bars)
    _CANDLE_CACHE.set(cache_key, candles)
    _set_cached_source(cache_key, provider)
    _last_success["ohlc"] = time.time()
    _last_error.pop("ohlc", None)
    return candles, provider


# source-tag side-cache (kept separate so the candle cache stays pure data)
_SOURCE_TAGS: Dict = {}


def _set_cached_source(key, source: str) -> None:
    _SOURCE_TAGS[key] = source


def cached_source(key) -> str:
    return _SOURCE_TAGS.get(key, "cached")


def get_real_quote(symbol: str) -> Tuple[Optional[MarketQuote], str]:
    """Fetch a real current quote. ``(None, "unavailable")`` on failure."""
    provider = get_market_data_provider()

    if provider == SOURCE_MOCK:
        from app.services.screener_engine import _generate_ohlc, _meta_for

        meta = _meta_for(symbol)
        base = meta["base"] if meta else 1000.0
        c = _generate_ohlc(symbol, base, days=2)[-1]
        prev = _generate_ohlc(symbol, base, days=2)[-2]
        chg = c.close - prev.close
        return (
            MarketQuote(
                symbol=symbol,
                name=meta.get("name", symbol) if meta else symbol,
                price=c.close,
                change=chg,
                change_percent=round(chg / prev.close * 100, 2) if prev.close else 0,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                previous_close=prev.close,
                volume=c.volume,
                timestamp=datetime.utcnow(),
                source=SOURCE_MOCK,
            ),
            SOURCE_MOCK,
        )

    cache_key = ("quote", symbol.upper())
    cached = _QUOTE_CACHE.get(cache_key)
    if cached is not None:
        return cached, cached_source(cache_key)

    quote = None
    if provider == SOURCE_YFINANCE:
        quote = _fetch_yfinance_quote_sync(symbol)
    elif provider == SOURCE_ANGEL_ONE:
        quote = _fetch_broker_quote("angel_one", symbol)
    elif provider == SOURCE_KITE:
        quote = _fetch_broker_quote("kite", symbol)

    if quote is None:
        return None, SOURCE_UNAVAILABLE
    quote.source = provider
    _QUOTE_CACHE.set(cache_key, quote)
    _set_cached_source(cache_key, provider)
    _last_success["quote"] = time.time()
    _last_error.pop("quote", None)
    return quote, provider


def _fetch_yfinance_quote_sync(symbol: str) -> Optional[MarketQuote]:
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover
        _last_error["quote"] = f"yfinance import failed: {exc}"
        return None
    ticker = _yf_ticker(symbol)
    if not ticker:
        return None
    try:
        info = yf.Ticker(ticker).fast_info
        last = float(info.last_price)
        prev = float(info.previous_close or last)
        chg = last - prev
        return MarketQuote(
            symbol=symbol,
            name=symbol,
            price=last,
            change=round(chg, 2),
            change_percent=round(chg / prev * 100, 2) if prev else 0.0,
            open=float(getattr(info, "open", last) or last),
            high=float(getattr(info, "day_high", last) or last),
            low=float(getattr(info, "day_low", last) or last),
            close=last,
            previous_close=prev,
            volume=int(getattr(info, "last_volume", 0) or 0),
            timestamp=datetime.utcnow(),
        )
    except Exception as exc:
        _last_error["quote"] = str(exc)
        logger.info("yfinance_quote_error", symbol=symbol, error=str(exc))
        return None


# --- broker adapters (return [] / None until credentials configured) --------


def _fetch_via_broker(provider: str, symbol: str, interval: str, limit: int) -> List[OHLCVBar]:
    """Delegate to the configured broker provider for OHLCV.

    Broker providers are async; this is a sync bridge used by the (sync)
    scanner engine. Credentials must be present or an empty list is returned
    (truthful unavailable) — never synthetic data.
    """
    try:
        provider_obj = _build_broker(provider)
    except Exception as exc:
        _last_error["ohlc"] = f"{provider} init failed: {exc}"
        return []
    if provider_obj is None or not _broker_configured(provider):
        _last_error["ohlc"] = f"{provider} not configured"
        return []
    try:
        loop = asyncio.new_event_loop()
        try:
            ohlc = loop.run_until_complete(
                provider_obj.get_ohlc(symbol, interval=interval, limit=limit)
            )
        finally:
            loop.close()
        return _broker_ohlc_to_bars(provider, symbol, ohlc)
    except Exception as exc:
        _last_error["ohlc"] = f"{provider} ohlc failed: {exc}"
        return []


def _fetch_broker_quote(provider: str, symbol: str) -> Optional[MarketQuote]:
    try:
        provider_obj = _build_broker(provider)
    except Exception as exc:
        _last_error["quote"] = f"{provider} init failed: {exc}"
        return None
    if provider_obj is None or not _broker_configured(provider):
        _last_error["quote"] = f"{provider} not configured"
        return None
    try:
        loop = asyncio.new_event_loop()
        try:
            q = loop.run_until_complete(provider_obj.get_quote(symbol))
        finally:
            loop.close()
        return _broker_quote_to_market(q) if q else None
    except Exception as exc:
        _last_error["quote"] = f"{provider} quote failed: {exc}"
        return None


def _broker_configured(provider: str) -> bool:
    if provider == SOURCE_ANGEL_ONE:
        return bool(
            settings.ANGEL_ONE_ENABLED
            and settings.ANGEL_ONE_API_KEY
            and settings.ANGEL_ONE_CLIENT_CODE
        )
    if provider == SOURCE_KITE:
        return bool(
            settings.KITE_CONNECT_ENABLED
            and settings.KITE_CONNECT_API_KEY
            and settings.KITE_CONNECT_ACCESS_TOKEN
        )
    return False


def _build_broker(provider: str):
    if provider == SOURCE_ANGEL_ONE:
        from app.integrations.data_providers.angel_one_provider import (
            create_angel_one_provider,
        )

        return create_angel_one_provider(
            api_key=settings.ANGEL_ONE_API_KEY,
            client_code=settings.ANGEL_ONE_CLIENT_CODE,
            password=settings.ANGEL_ONE_PASSWORD,
            totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
        )
    if provider == SOURCE_KITE:
        from app.integrations.data_providers.kite_connect_provider import (
            create_kite_connect_provider,
        )

        return create_kite_connect_provider(
            api_key=settings.KITE_CONNECT_API_KEY,
            access_token=settings.KITE_CONNECT_ACCESS_TOKEN,
        )
    return None


def _broker_ohlc_to_bars(provider: str, symbol: str, ohlc) -> List[OHLCVBar]:
    return [
        OHLCVBar(
            symbol=symbol,
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in (ohlc or [])
    ]


def _broker_quote_to_market(q) -> MarketQuote:
    return MarketQuote(
        symbol=q.symbol,
        name=getattr(q, "name", q.symbol),
        price=q.price,
        change=q.change,
        change_percent=q.change_percent,
        open=q.open,
        high=q.high,
        low=q.low,
        close=q.close,
        previous_close=q.previous_close,
        volume=q.volume,
        timestamp=q.timestamp,
    )


# --- universe ---------------------------------------------------------------

DEFAULT_UNIVERSE: List[str] = [
    "RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK", "SBIN",
    "BHARTIARTL", "ITC", "LT", "KOTAKBANK", "AXISBANK", "TATAMOTORS",
    "TATASTEEL", "MARUTI", "BAJFINANCE", "HINDUNILVR", "ASIANPAINT",
    "WIPRO", "ADANIENT", "SUNPHARMA",
]


def get_scanner_universe() -> List[str]:
    """Configurable scanner universe. Cached for the request lifetime."""
    raw = (settings.SCANNER_UNIVERSE or "").strip()
    if not raw:
        return list(DEFAULT_UNIVERSE)
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


# --- option chain (real OI only) -------------------------------------------


def get_real_option_chain(symbol: str, expiry: Optional[str] = None):
    """Fetch a real option chain with OI.

    Returns ``None`` when no derivatives provider is configured. yfinance
    does not expose NSE index option OI, so this is only non-None when a
    broker (Angel One / Kite) is configured and returns a chain. Synthetic OI
    is never produced here.
    """
    provider = get_market_data_provider()
    if provider not in (SOURCE_ANGEL_ONE, SOURCE_KITE):
        return None
    if not _broker_configured(provider):
        return None
    try:
        provider_obj = _build_broker(provider)
    except Exception as exc:
        _last_error["options"] = f"{provider} init failed: {exc}"
        return None
    try:
        loop = asyncio.new_event_loop()
        try:
            chain = loop.run_until_complete(
                provider_obj.get_option_chain(symbol, expiry=expiry)
            )
        finally:
            loop.close()
        return chain or None
    except Exception as exc:
        _last_error["options"] = f"{provider} option chain failed: {exc}"
        return None


# --- bounded-concurrency universe fetch (Phase 14) -------------------------


def fetch_universe_candles(
    symbols: List[str], interval: str = "1d", limit: int = 250,
    concurrency: Optional[int] = None,
) -> Dict[str, Tuple[List[Candle], str]]:
    """Fetch OHLCV for many symbols with bounded concurrency.

    Respects the configured ``SCANNER_CONCURRENCY`` limit so the scanner does
    not overwhelm the provider. Returns ``{symbol: (candles, source)}``;
    symbols that fail are omitted. Uses a thread pool because yfinance is
    synchronous.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    max_workers = concurrency or max(1, min(settings.SCANNER_CONCURRENCY, 10))
    out: Dict[str, Tuple[List[Candle], str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(get_real_candles, s, interval=interval, limit=limit): s
            for s in symbols
        }
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                candles, src = fut.result()
            except Exception as exc:
                _last_error[f"universe:{sym}"] = str(exc)
                continue
            if candles:
                out[sym] = (candles, src)
    return out
