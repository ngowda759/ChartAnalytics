"""Market data service with caching and real-time updates."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog

from app.integrations.data_providers.mock_provider import MockDataProvider
from app.integrations.data_providers.angel_one_provider import AngelOneProvider, create_angel_one_provider
from app.integrations.data_providers.base import TickerData, OHLCData, OptionChainData, BaseDataProvider
from app.services.ai_market_engine import AIMarketEngine, MarketInsight
from app.services.option_chain import OptionChainAnalyzer, OptionChainAnalysis
from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class CachedQuote:
    """Cached market quote with timestamp."""

    data: TickerData
    cached_at: datetime
    ttl_seconds: int = 60


@dataclass
class MarketDataService:
    """Service for fetching and caching market data."""

    provider: BaseDataProvider = field(default_factory=lambda: MockDataProvider())
    _quote_cache: Dict[str, CachedQuote] = field(default_factory=dict)
    _cache_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_indices(self) -> List[TickerData]:
        """Get all major market indices."""
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
                # Return cached data if available
                return self._quote_cache.get(
                    cache_key,
                    TickerData(
                        symbol=symbol,
                        name=symbol,
                        price=0,
                        change=0,
                        change_percent=0,
                        open=0,
                        high=0,
                        low=0,
                        close=0,
                        previous_close=0,
                        volume=0,
                        timestamp=datetime.utcnow(),
                    ),
                )

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
        """Get OHLC data for a symbol."""
        try:
            return await self.provider.get_ohlc(symbol, interval, limit)
        except Exception as e:
            logger.error("fetch_ohlc_failed", symbol=symbol, error=str(e))
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
    """Get or create market service instance."""
    global _market_service
    if _market_service is None:
        # Check if Angel One is enabled
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
            logger.info("using_mock_provider", reason="angel_one_disabled")
            _market_service = MarketDataService(provider=MockDataProvider())
    return _market_service
