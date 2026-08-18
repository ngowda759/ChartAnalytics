"""Base data provider interface for market data.

Defines the unified, provider-agnostic contract every market-data provider
must implement. All normalized models carry a ``source`` tag (which provider
produced the data), a ``status`` lifecycle tag (live/cached/stale/unavailable/
error) and a ``timestamp`` so downstream consumers (scanner, decision signals,
agent analysis, dashboard) never depend on provider-specific response shapes.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

# --- provider source labels (mirrors app.services.market_data) -------------
SOURCE_ANGEL_ONE = "angel_one"
SOURCE_KITE = "kite"
SOURCE_YFINANCE = "yfinance"
SOURCE_NSE = "nse"
SOURCE_MOCK = "mock"
SOURCE_UNAVAILABLE = "unavailable"

# Lifecycle status of any data point produced by a provider.
STATUS_LIVE = "live"
STATUS_CACHED = "cached"
STATUS_STALE = "stale"
STATUS_UNAVAILABLE = "unavailable"
STATUS_ERROR = "error"


@dataclass
class TickerData:
    """Standardized ticker data from any provider."""

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
    metadata: Optional[Dict[str, Any]] = None
    source: str = SOURCE_UNAVAILABLE
    status: str = STATUS_UNAVAILABLE


@dataclass
class OHLCData:
    """OHLC candle data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class InstrumentMeta:
    """Normalized instrument master record.

    Resolved from the provider's instrument master (e.g. Angel One
    OpenAPI ``/scrip_master`` CSVs / search-scrip). Never fabricated —
    every field is populated from the master or the record is absent.
    """

    symbol: str
    exchange: str  # NSE / NFO / BSE / CDS / MCX
    token: str  # provider instrument token
    tradingsymbol: str  # provider trading symbol (e.g. NIFTY24AUG24500CE)
    instrument_type: str = ""  # OPTSTK / OPTIDX / FUTSTK / FUTIDX / EQ
    expiry: Optional[datetime] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CE / PE
    lot_size: Optional[int] = None
    name: Optional[str] = None  # human-friendly name


@dataclass
class OptionChainData:
    """Option chain data for a single strike (paired CE+PE).

    Every field is populated from the real provider response or left at its
    ``None`` default when the provider genuinely does not report it (e.g. IV
    when not available). The ``source``/``status``/``timestamp`` tags let the
    UI distinguish live OI from cached/stale snapshots and never render
    fabricated OI. Identity fields (symbol/expiry/strike) remain required.
    """

    symbol: str
    expiry_date: datetime
    strike: float
    call_oi: Optional[int] = None
    call_volume: Optional[int] = None
    call_iv: Optional[float] = None
    call_ltp: Optional[float] = None
    call_change_oi: Optional[int] = None
    put_oi: Optional[int] = None
    put_volume: Optional[int] = None
    put_iv: Optional[float] = None
    put_ltp: Optional[float] = None
    put_change_oi: Optional[int] = None
    source: str = SOURCE_UNAVAILABLE
    status: str = STATUS_UNAVAILABLE
    timestamp: Optional[datetime] = None


class BaseDataProvider(ABC):
    """Abstract base class for market data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        """Get real-time quote for a symbol."""
        pass

    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> List[TickerData]:
        """Get quotes for multiple symbols."""
        pass

    @abstractmethod
    async def get_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[OHLCData]:
        """Get OHLC data for charting."""
        pass

    @abstractmethod
    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Get option chain data."""
        pass

    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols."""
        pass

    async def lookup_instrument(self, symbol: str) -> Optional[InstrumentMeta]:
        """Resolve a symbol to normalized instrument metadata.

        Default implementation returns None (provider has no instrument
        master). Brokers with a scrip master override this.
        """
        return None

    async def is_available(self) -> bool:
        """Check if provider is available."""
        try:
            await self.get_quote("NIFTY")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Release provider resources (HTTP clients, sockets)."""
        return None
