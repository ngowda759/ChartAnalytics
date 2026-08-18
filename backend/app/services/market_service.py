"""Market data service with caching and real-time updates."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
import structlog
import pandas as pd

from app.integrations.data_providers.mock_provider import MockDataProvider
from app.integrations.data_providers.angel_one_provider import AngelOneProvider, create_angel_one_provider
from app.integrations.data_providers.kite_connect_provider import KiteConnectProvider, create_kite_connect_provider
from app.integrations.data_providers.base import TickerData, OHLCData, OptionChainData, BaseDataProvider
from app.services.ai_market_engine import AIMarketEngine, MarketInsight
from app.services.option_chain import OptionChainAnalyzer, OptionChainAnalysis
from app.services.nse_service import get_index_quotes, _safe_float
from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class CachedQuote:
    """Cached market quote with timestamp."""

    data: TickerData
    cached_at: datetime
    ttl_seconds: int = 60


# Friendly display name per index symbol reported by nsetools.
_INDEX_DISPLAY_NAMES = {
    "NIFTY 50": "NIFTY 50",
    "NIFTY BANK": "NIFTY Bank",
    "NIFTY FIN SERVICE": "NIFTY Fin Services",
    "NIFTY MIDCAP 100": "NIFTY Midcap 100",
    "NIFTY SMLCAP 100": "NIFTY Smallcap 100",
    "INDIA VIX": "India VIX",
}


@dataclass
class MarketDataService:
    """Service for fetching and caching market data."""

    provider: BaseDataProvider = field(default_factory=lambda: MockDataProvider())
    _quote_cache: Dict[str, CachedQuote] = field(default_factory=dict)
    _cache_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_indices(self) -> List[TickerData]:
        """Get all major market indices.

        Prefers live NSE data via nsetools so the dashboard shows real prices.
        Falls back to the configured provider (mock/Angel One/Kite) when NSE is
        unreachable (e.g. outside market hours).
        """
        live = get_index_quotes()
        if live:
            now = datetime.utcnow()
            return [
                TickerData(
                    symbol=item.get("indexSymbol") or item.get("index", ""),
                    name=_INDEX_DISPLAY_NAMES.get(
                        item.get("indexSymbol") or item.get("index"),
                        item.get("index", ""),
                    ),
                    price=_safe_float(item.get("last"), 0) or 0,
                    change=_safe_float(item.get("variation"), 0) or 0,
                    change_percent=_safe_float(item.get("percentChange"), 0) or 0,
                    open=_safe_float(item.get("open"), 0) or 0,
                    high=_safe_float(item.get("high"), 0) or 0,
                    low=_safe_float(item.get("low"), 0) or 0,
                    close=_safe_float(item.get("last"), 0) or 0,
                    previous_close=_safe_float(item.get("previousClose"), 0) or 0,
                    volume=0,
                    timestamp=now,
                    metadata={"index": True, "source": "nsetools"},
                )
                for item in live
            ]
        logger.info("indices_fallback_to_provider", reason="nse_unreachable")
        symbols = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "SENSEX", "INDIA VIX"]
        return await self.get_quotes(symbols)

    async def get_quote(
        self, symbol: str, force_refresh: bool = False
    ) -> Optional[TickerData]:
        """Get quote for a symbol with caching."""
        cache_key = symbol.upper()

        # Check cache
        if not force_refresh and cache_key in self._quote_cache:
            cached = self._quote_cache[cache_key]
            if (
                datetime.utcnow() - cached.cached_at
            ).total_seconds() < cached.ttl_seconds:
                return cached.data

        # Fetch fresh data
        async with self._cache_lock:
            try:
                data = await self.provider.get_quote(symbol)
                if data:
                    self._quote_cache[cache_key] = CachedQuote(
                        data=data,
                        cached_at=datetime.utcnow(),
                    )
                return data
            except Exception as e:
                logger.error("fetch_quote_failed", symbol=symbol, error=str(e))
                # Return cached data if available; otherwise None so the caller
                # can show "N/A" instead of a fabricated zero-price quote.
                return self._quote_cache.get(cache_key, None)

    async def get_quotes(self, symbols: List[str]) -> List[TickerData]:
        """Get quotes for multiple symbols."""
        tasks = [self.get_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, TickerData)]

    async def get_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
    ) -> List[OHLCData]:
        """Get OHLC data for a symbol.

        Prefers live yfinance intraday candles so charts reflect the current
        session; falls back to the configured provider (mock/Angel One/Kite)
        when yfinance is unavailable (offline tests, blocked network) so the
        endpoint is never empty.
        """
        live = await self._fetch_yfinance_ohlc(symbol, interval, limit)
        if live:
            return live
        try:
            return await self.provider.get_ohlc(symbol, interval, limit)
        except Exception as e:
            logger.error("fetch_ohlc_failed", symbol=symbol, error=str(e))
            return []

    # yfinance intraday support -------------------------------------------------

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
    }
    _YF_INTRADAY_INTERVALS = {"1m", "5m", "15m", "30m", "1h"}

    def _yf_ticker(self, symbol: str) -> Optional[str]:
        key = symbol.strip().upper()
        if key in self._YF_INDEX_MAP:
            return self._YF_INDEX_MAP[key]
        # NSE equities: append .NS (yfinance convention). Skip obvious
        # non-equity placeholders so we don't spam yfinance with junk.
        if key and not key.startswith("^"):
            return f"{key}.NS"
        return None

    def _yf_interval(self, interval: str) -> Optional[str]:
        i = interval.lower()
        return {"1h": "60m"}.get(i, i) if i in self._YF_INTRADAY_INTERVALS else None

    async def _fetch_yfinance_ohlc(
        self, symbol: str, interval: str, limit: int
    ) -> List[OHLCData]:
        """Fetch live intraday OHLC via yfinance. Returns [] on any failure."""
        yf_interval = self._yf_interval(interval)
        ticker = self._yf_ticker(symbol)
        if not yf_interval or not ticker:
            return []

        def _download() -> List[OHLCData]:
            import yfinance as yf  # local import: heavy, and optional at runtime

            df = yf.download(
                ticker,
                period="1d",
                interval=yf_interval,
                progress=False,
                auto_adjust=False,
            )
            if df is None or df.empty:
                return []
            # Normalise column names: yfinance may return MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.tail(limit).sort_index()
            out: List[OHLCData] = []
            for ts, row in df.iterrows():
                try:
                    ts_dt = ts.to_pydatetime()
                    if ts_dt.tzinfo is not None:
                        ts_dt = ts_dt.astimezone(timezone.utc).replace(tzinfo=None)
                    out.append(
                        OHLCData(
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
            return out

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.info("yfinance_ohlc_unavailable", symbol=symbol, error=str(e))
            return []

    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Get option chain data."""
        try:
            return await self.provider.get_option_chain(symbol, expiry)
        except Exception as e:
            logger.error("fetch_option_chain_failed", symbol=symbol, error=str(e))
            return []

    async def analyze_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> Optional[OptionChainAnalysis]:
        """Analyze option chain data."""
        try:
            chain_data = await self.get_option_chain(symbol, expiry)
            if not chain_data:
                return None

            # Get spot price
            quote = await self.get_quote(symbol)
            spot_price = quote.price if quote else 25000

            # Get expiry date
            expiry_date = datetime.utcnow()
            if expiry:
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            else:
                # Next Friday
                days_until_friday = (4 - datetime.utcnow().weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                expiry_date = datetime.utcnow() + timedelta(days=days_until_friday)

            analyzer = OptionChainAnalyzer(spot_price, expiry_date)
            return analyzer.analyze(chain_data)
        except Exception as e:
            logger.error("analyze_option_chain_failed", symbol=symbol, error=str(e))
            return None

    async def get_market_insight(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 200,
    ) -> Optional[MarketInsight]:
        """Get AI-powered market insight."""
        try:
            # Get OHLC data
            ohlc_data = await self.get_ohlc(symbol, interval, limit)
            if not ohlc_data or len(ohlc_data) < 50:
                return None

            # Extract price arrays
            closes = [c.close for c in ohlc_data]
            highs = [c.high for c in ohlc_data]
            lows = [c.low for c in ohlc_data]
            volumes = [c.volume for c in ohlc_data]

            # Get option chain analysis
            option_chain = await self.analyze_option_chain(symbol)

            # Generate insight
            engine = AIMarketEngine(symbol)
            return engine.analyze(closes, highs, lows, closes, volumes, option_chain)
        except Exception as e:
            logger.error("get_market_insight_failed", symbol=symbol, error=str(e))
            return None

    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols."""
        try:
            return await self.provider.search_symbols(query)
        except Exception as e:
            logger.error("search_symbols_failed", query=query, error=str(e))
            return []

    def clear_cache(self):
        """Clear the quote cache."""
        self._quote_cache.clear()


# Global service instance
_market_service: Optional[MarketDataService] = None


def get_market_service() -> MarketDataService:
    """Get or create market service instance.

    Provider selection is EXPLICIT and never silently falls back to mock:
      - MARKET_DATA_PROVIDER=kite       -> Kite Connect (needs credentials)
      - MARKET_DATA_PROVIDER=angel_one  -> Angel One (needs credentials)
      - MARKET_DATA_PROVIDER=yfinance    -> Yahoo Finance (no credentials)
      - MARKET_DATA_PROVIDER=auto        -> kite > angel_one > yfinance
      - MARKET_DATA_PROVIDER=mock        -> synthetic dev/test data (explicit)
    In production, "mock" is rejected unless ALLOW_MOCK_IN_PRODUCTION=true.
    """
    global _market_service
    if _market_service is None:
        from app.services import market_data

        provider_name = market_data.get_market_data_provider()

        if provider_name == market_data.SOURCE_MOCK:
            if not market_data.mock_allowed_in_production():
                # Production must fail clearly instead of silently running mock.
                raise RuntimeError(
                    "LIVE MARKET DATA NOT CONFIGURED: MARKET_DATA_PROVIDER=mock "
                    "is not allowed in production (set a live provider or "
                    "ALLOW_MOCK_IN_PRODUCTION=true to override)."
                )
            logger.warning("using_mock_provider", reason="explicit_development_mode")
            _market_service = MarketDataService(provider=MockDataProvider())
        elif provider_name == market_data.SOURCE_KITE:
            if settings.KITE_CONNECT_ENABLED and settings.KITE_CONNECT_API_KEY:
                logger.info("using_kite_connect_provider")
                provider = create_kite_connect_provider(
                    api_key=settings.KITE_CONNECT_API_KEY,
                    access_token=settings.KITE_CONNECT_ACCESS_TOKEN,
                )
                _market_service = MarketDataService(provider=provider)
            else:
                logger.warning(
                    "kite_provider_not_configured",
                    reason="missing KITE_CONNECT_API_KEY/ACCESS_TOKEN",
                )
                _market_service = MarketDataService(provider=_UnavailableProvider("kite"))
        elif provider_name == market_data.SOURCE_ANGEL_ONE:
            if settings.ANGEL_ONE_ENABLED and settings.ANGEL_ONE_API_KEY:
                logger.info("using_angel_one_provider")
                provider = create_angel_one_provider(
                    api_key=settings.ANGEL_ONE_API_KEY,
                    client_code=settings.ANGEL_ONE_CLIENT_CODE,
                    password=settings.ANGEL_ONE_PASSWORD,
                    totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
                )
                _market_service = MarketDataService(provider=provider)
            else:
                logger.warning(
                    "angel_one_provider_not_configured",
                    reason="missing ANGEL_ONE_API_KEY/CLIENT_CODE",
                )
                _market_service = MarketDataService(
                    provider=_UnavailableProvider("angel_one")
                )
        else:
            # yfinance (default, credential-free) — real data via the unified
            # service; the MarketDataService OHLC path already prefers yfinance.
            logger.info("using_yfinance_provider", reason="credential_free_default")
            _market_service = MarketDataService(provider=_YFinanceProvider())
    return _market_service


class _YFinanceProvider(BaseDataProvider):
    """Thin provider that delegates OHLC/quotes to the unified market_data
    service (yfinance). Option chain is unavailable (yfinance has no NSE OI)."""

    _PROVIDER_NAME = "yfinance"

    @property
    def name(self) -> str:
        return "yfinance"

    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        from app.services import market_data

        q, src = market_data.get_real_quote(symbol)
        if q is None:
            return None
        return TickerData(
            symbol=q.symbol,
            name=q.name,
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
            metadata={"source": src},
        )

    async def get_quotes(self, symbols: List[str]) -> List[TickerData]:
        out = []
        for s in symbols:
            q = await self.get_quote(s)
            if q:
                out.append(q)
        return out

    async def get_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        start_date=None,
        end_date=None,
    ) -> List[OHLCData]:
        from app.services import market_data

        candles, _src = market_data.get_real_candles(symbol, interval=interval, limit=limit)
        if not candles:
            return []
        return [
            OHLCData(timestamp=c.date, open=c.open, high=c.high, low=c.low, close=c.close, volume=c.volume)
            for c in candles
        ]

    async def get_option_chain(self, symbol: str, expiry=None):
        return []  # yfinance has no NSE option OI — truthful unavailable

    async def search_symbols(self, query: str):
        return []

    async def is_available(self) -> bool:
        from app.services import market_data

        return market_data.get_market_data_provider() != market_data.SOURCE_UNAVAILABLE


class _UnavailableProvider(BaseDataProvider):
    """Provider that returns nothing (truthful unavailable) — used when a live
    provider is selected but its credentials are missing, instead of mock."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return f"{self._name} (not configured)"

    async def get_quote(self, symbol: str):
        return None

    async def get_quotes(self, symbols: List[str]):
        return []

    async def get_ohlc(self, symbol, interval="1d", limit=100, start_date=None, end_date=None):
        return []

    async def get_option_chain(self, symbol, expiry=None):
        return []

    async def search_symbols(self, query):
        return []

    async def is_available(self) -> bool:
        return False
