"""Base data provider interface for market data."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass


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
class OptionChainData:
    """Option chain data for a symbol."""
    symbol: str
    expiry_date: datetime
    strike: float
    call_oi: int
    call_volume: int
    call_iv: float
    call_ltp: float
    call_change_oi: int
    put_oi: int
    put_volume: int
    put_iv: float
    put_ltp: float
    put_change_oi: int


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
    
    async def is_available(self) -> bool:
        """Check if provider is available."""
        try:
            await self.get_quote("NIFTY")
            return True
        except Exception:
            return False
