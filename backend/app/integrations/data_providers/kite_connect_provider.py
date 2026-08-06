"""Zerodha Kite Connect integration for real-time market data.

Kite Connect provides WebSocket streaming for live market data.
Free for personal/non-commercial use.
Documentation: https://kite.trade/docs/connect/v3/
"""

import asyncio
import json
import structlog
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .base import BaseDataProvider, TickerData, OHLCData, OptionChainData

logger = structlog.get_logger()


# Kite Connect endpoints
KITE_BASE_URL = "https://api.kite.trade"
KITE_WS_URL = "wss://ws.kite.trade"


@dataclass
class KiteConnectConfig:
    """Configuration for Kite Connect."""
    api_key: str = ""
    access_token: str = ""


@dataclass
class KiteQuote:
    """Kite quote format."""
    symbol: str
    token: str
    ltp: float
    change: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime


# NSE instrument tokens
SYMBOL_TOKENS = {
    "NIFTY 50": "256265",
    "NIFTY50": "256265",
    "NIFTY": "256265",
    "BANKNIFTY": "260105",
    "NIFTY BANK": "260105",
    "FINNIFTY": "260289",
    "NIFTY FIN SERVICE": "260289",
    "SENSEX": "265",
    "BSE SENSEX": "265",
    "INDIA VIX": "264969",
    # Popular stocks
    "RELIANCE": "738561",
    "HDFCBANK": "341249",
    "ICICIBANK": "49633",
    "INFY": "408065",
    "TCS": "11536",
    "HINDUNILVR": "134657",
    "ITC": "415771",
    "KOTAKBANK": "492033",
    "SBIN": "779521",
    "BHARTIARTL": "1060370",
    "LT": "293761",
    "AXISBANK": "60417",
}


class KiteConnectProvider(BaseDataProvider):
    """Kite Connect data provider.
    
    Provides real-time market data via WebSocket and REST APIs.
    Free for personal/non-commercial use.
    
    Setup:
    1. Get API Key from https://developers.kite.trade
    2. Generate access token via OAuth flow
    3. Set environment variables
    """
    
    def __init__(self, config: Optional[KiteConnectConfig] = None):
        self.config = config or KiteConnectConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_client = None
        self._quote_cache: Dict[str, KiteQuote] = {}
        self._cache_lock = asyncio.Lock()
        self._subscriptions: set = set()
    
    @property
    def name(self) -> str:
        return "Kite Connect"
    
    @property
    def is_configured(self) -> bool:
        """Check if provider has valid credentials."""
        return bool(self.config.api_key and self.config.access_token)
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=KITE_BASE_URL,
                headers={
                    "X-Kite-Version": "3",
                    "Authorization": f"token {self.config.api_key}:{self.config.access_token}",
                },
                timeout=30.0,
            )
        return self._http_client
    
    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        """Get real-time quote for a symbol."""
        # Check cache
        async with self._cache_lock:
            if symbol.upper() in self._quote_cache:
                cached = self._quote_cache[symbol.upper()]
                if (datetime.utcnow() - cached.timestamp).total_seconds() < 5:
                    return self._kite_to_ticker(cached)
        
        # Try REST API
        try:
            return await self._get_quote_rest(symbol)
        except Exception as e:
            logger.error("kite_get_quote_failed", symbol=symbol, error=str(e))
            return None
    
    async def _get_quote_rest(self, symbol: str) -> Optional[TickerData]:
        """Get quote via REST API."""
        client = self._get_http_client()
        token = SYMBOL_TOKENS.get(symbol.upper(), "")
        
        if not token:
            logger.warning("symbol_token_not_found", symbol=symbol)
            return None
        
        try:
            response = await client.get(f"/quote/{'NSE' if not symbol.endswith(('F', 'OPT')) else 'NFO'}/{token}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    quote_data = data["data"].get(token, {})
                    last_trade = quote_data.get("last_price", 0)
                    ohlc = quote_data.get("ohlc", {})
                    
                    return TickerData(
                        symbol=symbol,
                        name=symbol,
                        price=last_trade,
                        change=quote_data.get("net_change", 0),
                        change_percent=quote_data.get("net_change_percent", 0),
                        open=ohlc.get("open", 0),
                        high=ohlc.get("high", 0),
                        low=ohlc.get("low", 0),
                        close=ohlc.get("close", 0),
                        previous_close=ohlc.get("close", 0),
                        volume=quote_data.get("volume", 0),
                        timestamp=datetime.utcnow(),
                    )
        except Exception as e:
            logger.error("kite_rest_quote_failed", error=str(e))
        
        return None
    
    async def get_quotes(self, symbols: List[str]) -> List[TickerData]:
        """Get quotes for multiple symbols."""
        results = []
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote:
                results.append(quote)
        return results
    
    async def get_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[OHLCData]:
        """Get OHLC historical data."""
        try:
            client = self._get_http_client()
            token = SYMBOL_TOKENS.get(symbol.upper(), "")
            
            if not token:
                return []
            
            # Map interval
            interval_map = {
                "1m": "minute",
                "5m": "5minute",
                "15m": "15minute",
                "30m": "30minute",
                "1h": "60minute",
                "1d": "day",
            }
            kite_interval = interval_map.get(interval, "day")
            
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                start_date = end_date - timedelta(days=limit)
            
            params = {
                "oi": "1",  # Include OI for futures
                "interval": kite_interval,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
            }
            
            response = await client.get(
                f"/historical/{'NSE' if symbol.upper() in ['NIFTY', 'BANKNIFTY'] else 'NSE'}/{token}",
                params=params,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    candles = data["data"].get("candles", [])
                    return [
                        OHLCData(
                            timestamp=datetime.strptime(c[0], "%Y-%m-%d %H:%M:%S"),
                            open=float(c[1]),
                            high=float(c[2]),
                            low=float(c[3]),
                            close=float(c[4]),
                            volume=int(c[5]) if len(c) > 5 else 0,
                        )
                        for c in candles
                    ]
                    
        except Exception as e:
            logger.error("kite_get_ohlc_failed", symbol=symbol, error=str(e))
        
        return []
    
    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Get option chain data (requires subscription)."""
        # Kite doesn't provide direct option chain API
        # Use instruments list and filter for options
        try:
            client = self._get_http_client()
            
            # Get NFO instruments
            response = await client.get("/instruments/NFO")
            if response.status_code != 200:
                return []
            
            # Parse CSV response
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                return []
            
            headers = lines[0].split(",")
            
            # Filter for options
            expiry_map = {
                "NIFTY": "NIFTY",
                "BANKNIFTY": "BANKNIFTY",
                "FINNIFTY": "FINNIFTY",
            }
            prefix = expiry_map.get(symbol.upper(), symbol.upper())
            
            options = []
            for line in lines[1:]:
                cols = line.split(",")
                if len(cols) < 10:
                    continue
                
                instrument_type = cols[5] if len(cols) > 5 else ""
                if instrument_type == "OPT":
                    name = cols[1] if len(cols) > 1 else ""
                    if prefix in name:
                        expiry_str = cols[2] if len(cols) > 2 else ""
                        strike = cols[6] if len(cols) > 6 else "0"
                        
                        try:
                            expiry_date = datetime.strptime(expiry_str, "%d-%b-%Y")
                        except:
                            continue
                        
                        if expiry and expiry not in expiry_str:
                            continue
                        
                        options.append(
                            OptionChainData(
                                symbol=symbol,
                                expiry_date=expiry_date,
                                strike=float(strike),
                                call_oi=0,
                                call_volume=0,
                                call_iv=0,
                                call_ltp=0,
                                call_change_oi=0,
                                put_oi=0,
                                put_volume=0,
                                put_iv=0,
                                put_ltp=0,
                                put_change_oi=0,
                            )
                        )
            
            return options
            
        except Exception as e:
            logger.error("kite_get_option_chain_failed", symbol=symbol, error=str(e))
        
        return []
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols."""
        try:
            client = self._get_http_client()
            response = await client.get("/instruments/NSE")
            
            if response.status_code == 200:
                lines = response.text.strip().split("\n")
                if len(lines) < 2:
                    return []
                
                results = []
                query_upper = query.upper()
                
                for line in lines[1:100]:  # Limit search
                    cols = line.split(",")
                    if len(cols) > 2:
                        token = cols[0]
                        name = cols[2]
                        if query_upper in name.upper():
                            results.append({
                                "symbol": name,
                                "name": name,
                                "token": token,
                                "type": cols[5] if len(cols) > 5 else "",
                            })
                            if len(results) >= 10:
                                break
                
                return results
                
        except Exception as e:
            logger.error("kite_search_symbols_failed", query=query, error=str(e))
        
        return []
    
    def _kite_to_ticker(self, quote: KiteQuote) -> TickerData:
        """Convert Kite quote to standard TickerData."""
        return TickerData(
            symbol=quote.symbol,
            name=quote.symbol,
            price=quote.ltp,
            change=quote.change,
            change_percent=(quote.change / quote.close * 100) if quote.close else 0,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            previous_close=quote.close,
            volume=quote.volume,
            timestamp=quote.timestamp,
        )
    
    async def connect_websocket(self) -> bool:
        """Connect to Kite WebSocket for real-time data."""
        if not self.is_configured:
            logger.warning("kite_not_configured")
            return False
        
        if self._ws_client is not None:
            return True
        
        try:
            import websockets
            
            ws_url = f"{KITE_WS_URL}?api_key={self.config.api_key}"
            self._ws_client = await websockets.connect(ws_url)
            
            # Authenticate
            await self._ws_client.send(json.dumps({
                "action": "login",
                "params": {
                    "api_key": self.config.api_key,
                    "access_token": self.config.access_token,
                }
            }))
            
            # Wait for auth response
            response = await asyncio.wait_for(self._ws_client.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("status") == "success" or data.get("type") == "login":
                logger.info("kite_ws_connected")
                asyncio.create_task(self._ws_message_handler())
                return True
                
        except Exception as e:
            logger.error("kite_ws_connect_failed", error=str(e))
            self._ws_client = None
        
        return False
    
    async def _ws_message_handler(self):
        """Handle WebSocket messages."""
        try:
            async for message in self._ws_client:
                try:
                    data = json.loads(message)
                    
                    if data.get("type") == "quote":
                        self._handle_quote_update(data)
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception:
            logger.warning("kite_ws_disconnected")
            self._ws_client = None
    
    def _handle_quote_update(self, data: Dict):
        """Handle quote update from WebSocket."""
        try:
            quotes = data.get("data", {})
            for token, tick in quotes.items():
                quote = KiteQuote(
                    symbol=tick.get("instrument_token", ""),
                    token=token,
                    ltp=tick.get("last_price", 0),
                    change=tick.get("net_change", 0),
                    open=tick.get("ohlc", {}).get("open", 0),
                    high=tick.get("ohlc", {}).get("high", 0),
                    low=tick.get("ohlc", {}).get("low", 0),
                    close=tick.get("ohlc", {}).get("close", 0),
                    volume=tick.get("volume", 0),
                    timestamp=datetime.utcnow(),
                )
                self._quote_cache[token] = quote
                
        except Exception as e:
            logger.error("handle_quote_update_failed", error=str(e))
    
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to real-time quotes."""
        if not self._ws_client:
            connected = await self.connect_websocket()
            if not connected:
                return False
        
        try:
            tokens = []
            for symbol in symbols:
                token = SYMBOL_TOKENS.get(symbol.upper(), "")
                if token:
                    tokens.append(token)
                    self._subscriptions.add(token)
            
            if tokens:
                await self._ws_client.send(json.dumps({
                    "action": "subscribe",
                    "params": {"mode": "full", "exchange": "NSE", "tokens": tokens}
                }))
                logger.info("subscribed", count=len(tokens))
                return True
                
        except Exception as e:
            logger.error("subscribe_failed", error=str(e))
        
        return False
    
    async def disconnect_websocket(self):
        """Disconnect from WebSocket."""
        if self._ws_client:
            try:
                await self._ws_client.close()
            except Exception:
                pass
            self._ws_client = None
            self._subscriptions.clear()
    
    async def is_available(self) -> bool:
        """Check if provider is available."""
        if not self.is_configured:
            return False
        
        try:
            client = self._get_http_client()
            response = await client.get("/portfolio/holdings")
            return response.status_code in [200, 401]
        except Exception:
            return False
    
    async def close(self):
        """Clean up resources."""
        await self.disconnect_websocket()
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def create_kite_connect_provider(
    api_key: str = "",
    access_token: str = "",
) -> KiteConnectProvider:
    """Create Kite Connect provider with configuration."""
    config = KiteConnectConfig(
        api_key=api_key,
        access_token=access_token,
    )
    return KiteConnectProvider(config)
