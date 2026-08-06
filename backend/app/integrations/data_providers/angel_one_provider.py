"""Angel One SmartAPI integration for real-time market data.

Angel One provides free WebSocket streaming for live market data.
Documentation: https://smartapi.angelbroking.com/
"""

import asyncio
import json
import websockets
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog
import httpx

from .base import BaseDataProvider, TickerData, OHLCData, OptionChainData

logger = structlog.get_logger()


# Angel One SmartAPI endpoints
SMARTAPI_BASE_URL = "https://apiconnect.angelone.in"
SMARTAPI_WS_URL = "wss://websocket.angelone.in"
SMARTAPI_API_PATH = "/restful/apis"

# Token manager for WebSocket authentication
_ws_session_key: Optional[str] = None
_ws_refresh_token: Optional[str] = None
_websocket_client: Optional[Any] = None


@dataclass
class AngelOneConfig:
    """Configuration for Angel One SmartAPI."""
    api_key: str = ""
    client_code: str = ""
    password: str = ""
    totp_secret: str = ""
    feed_token: str = ""
    

@dataclass
class AngelOneQuote:
    """Angel One quote format."""
    symbol: str
    token: str
    exchange: str
    ltp: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    

class AngelOneProvider(BaseDataProvider):
    """Angel One SmartAPI data provider.
    
    Provides real-time market data via WebSocket and REST APIs.
    Free tier includes WebSocket streaming for live prices.
    
    Setup:
    1. Get API Key from Angel One SmartAPI portal
    2. Enable 2FA and get TOTP secret
    3. Set environment variables or pass config
    """
    
    def __init__(self, config: Optional[AngelOneConfig] = None):
        self.config = config or AngelOneConfig()
        self._tokens: Dict[str, str] = {}
        self._feed_token: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_client = None
        self._ws_subscriptions: set = field(default_factory=set)
        self._quote_cache: Dict[str, AngelOneQuote] = {}
        self._cache_lock = asyncio.Lock()
        
        # Symbol token mappings for NSE
        self._symbol_tokens = {
            # Indices
            "NIFTY 50": "26000",
            "NIFTY50": "26000",
            "NIFTY": "26000",
            "BANKNIFTY": "26001",
            "NIFTY BANK": "26001",
            "FINNIFTY": "26037",
            "NIFTY FIN SERVICE": "26037",
            "SENSEX": "13135",
            "BSE SENSEX": "13135",
            "INDIA VIX": "India VIX",
            
            # Popular stocks
            "RELIANCE": "2885",
            "HDFCBANK": "1333",
            "ICICIBANK": "4963",
            "INFY": "1594",
            "TCS": "11536",
            "HINDUNILVR": "1394",
            "ITC": "1660",
            "KOTAKBANK": "1922",
            "SBIN": "3045",
            "BHARTIARTL": "10604",
            "LT": "11483",
            "AXISBANK": "9198",
            
            # NFO F&O tokens
            "NIFTY24AUG": "58100",
            "NIFTY24AUGF": "58100",
            "BANKNIFTY24AUG": "58104",
        }
    
    @property
    def name(self) -> str:
        return "Angel One SmartAPI"
    
    @property
    def is_configured(self) -> bool:
        """Check if provider is configured with credentials."""
        return bool(self.config.api_key and self.config.client_code)
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=SMARTAPI_BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Api-Key": self.config.api_key,
                },
                timeout=30.0,
            )
        return self._http_client
    
    async def login(self) -> bool:
        """Authenticate with Angel One SmartAPI.
        
        Returns True if login successful, False otherwise.
        """
        if not self.is_configured:
            logger.warning("angel_one_not_configured")
            return False
            
        try:
            client = self._get_http_client()
            
            # Generate TOTP if secret is configured
            totp = ""
            if self.config.totp_secret:
                try:
                    import pyotp
                    totp = pyotp.TOTP(self.config.totp_secret).now()
                except ImportError:
                    logger.warning("pyotp_not_installed")
                    return False
            
            # Login request
            login_data = {
                "clientCode": self.config.client_code,
                "password": self.config.password,
                "totp": totp,
            }
            
            response = await client.post(
                f"{SMARTAPI_API_PATH}/login",
                json=login_data,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    self._tokens = {
                        "jwtToken": data.get("data", {}).get("jwtToken", ""),
                        "refreshToken": data.get("data", {}).get("refreshToken", ""),
                    }
                    self._feed_token = data.get("data", {}).get("feedToken", "")
                    logger.info("angel_one_login_success")
                    return True
                    
            logger.error("angel_one_login_failed", status=response.status_code)
            return False
            
        except Exception as e:
            logger.error("angel_one_login_error", error=str(e))
            return False
    
    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        """Get real-time quote for a symbol.
        
        Uses WebSocket data if connected, otherwise falls back to REST API.
        """
        # Check cache first
        async with self._cache_lock:
            if symbol.upper() in self._quote_cache:
                cached = self._quote_cache[symbol.upper()]
                # Check if data is fresh (within 5 seconds)
                if (datetime.utcnow() - cached.timestamp).total_seconds() < 5:
                    return self._angelone_to_ticker(cached)
        
        # Try REST API as fallback
        try:
            return await self._get_quote_rest(symbol)
        except Exception as e:
            logger.error("get_quote_failed", symbol=symbol, error=str(e))
            return None
    
    async def _get_quote_rest(self, symbol: str) -> Optional[TickerData]:
        """Get quote via REST API."""
        client = self._get_http_client()
        
        # Get token for symbol
        token = self._symbol_tokens.get(symbol.upper(), "")
        if not token:
            # Search for the symbol
            search_results = await self.search_symbols(symbol)
            if search_results:
                token = search_results[0].get("token", "")
        
        if not token:
            logger.warning("symbol_token_not_found", symbol=symbol)
            return None
        
        headers = {"Authorization": f"Bearer {self._tokens.get('jwtToken', '')}"}
        
        response = await client.get(
            f"{SMARTAPI_API_PATH}/marketData/latestCandle",
            params={"exchange": "NSE", "symboltoken": token},
            headers=headers,
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status"):
                candle = data.get("data", {})
                return TickerData(
                    symbol=symbol,
                    name=symbol,
                    price=float(candle.get("ltp", 0)),
                    change=float(candle.get("netPriceChange", 0)),
                    change_percent=float(candle.get("perNetPriceChange", 0)),
                    open=float(candle.get("open", 0)),
                    high=float(candle.get("high", 0)),
                    low=float(candle.get("low", 0)),
                    close=float(candle.get("close", 0)),
                    previous_close=float(candle.get("close", 0)),
                    volume=int(candle.get("volume", 0)),
                    timestamp=datetime.utcnow(),
                )
        
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
            token = self._symbol_tokens.get(symbol.upper(), "")
            
            if not token:
                return []
            
            headers = {"Authorization": f"Bearer {self._tokens.get('jwtToken', '')}"}
            
            # Map interval to Angel One format
            interval_map = {
                "1m": "ONE_MINUTE",
                "5m": "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h": "ONE_HOUR",
                "1d": "ONE_DAY",
            }
            angel_interval = interval_map.get(interval, "ONE_DAY")
            
            # Calculate dates
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                start_date = end_date - timedelta(days=limit)
            
            params = {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": angel_interval,
                "fromdate": start_date.strftime("%Y-%m-%d %H:%M"),
                "todate": end_date.strftime("%Y-%m-%d %H:%M"),
            }
            
            response = await client.get(
                f"{SMARTAPI_API_PATH}/marketData/historical",
                params=params,
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    candles = data.get("data", [])
                    return [
                        OHLCData(
                            timestamp=datetime.strptime(c["date"], "%Y-%m-%d %H:%M:%S"),
                            open=float(c["open"]),
                            high=float(c["high"]),
                            low=float(c["low"]),
                            close=float(c["close"]),
                            volume=int(c["volume"]),
                        )
                        for c in candles
                    ]
                    
        except Exception as e:
            logger.error("get_ohlc_failed", symbol=symbol, error=str(e))
        
        return []
    
    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Get option chain data for NIFTY/BANKNIFTY."""
        try:
            client = self._get_http_client()
            headers = {"Authorization": f"Bearer {self._tokens.get('jwtToken', '')}"}
            
            # Map symbol to exchange token
            symbol_map = {
                "NIFTY": "26000",
                "BANKNIFTY": "26001",
                "FINNIFTY": "26037",
            }
            exchange_token = symbol_map.get(symbol.upper(), "26000")
            
            params = {
                "exchange": "NFO",
                "symboltoken": exchange_token,
            }
            
            response = await client.get(
                f"{SMARTAPI_API_PATH}/marketData/optionChain",
                params=params,
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    records = data.get("data", {}).get("records", [])
                    
                    # Filter by expiry if specified
                    if expiry:
                        records = [r for r in records if expiry in str(r.get("expiryDate", ""))]
                    
                    return [
                        OptionChainData(
                            symbol=symbol,
                            expiry_date=datetime.strptime(str(r.get("expiryDate", "")), "%d%b%Y"),
                            strike=float(r.get("strikePrice", 0)),
                            call_oi=int(r.get("CE", {}).get("openInterest", 0)),
                            call_volume=int(r.get("CE", {}).get("totalTradedVolume", 0)),
                            call_iv=float(r.get("CE", {}).get("impliedVolatility", 0)),
                            call_ltp=float(r.get("CE", {}).get("lastPrice", 0)),
                            call_change_oi=int(r.get("CE", {}).get("changeinOpenInterest", 0)),
                            put_oi=int(r.get("PE", {}).get("openInterest", 0)),
                            put_volume=int(r.get("PE", {}).get("totalTradedVolume", 0)),
                            put_iv=float(r.get("PE", {}).get("impliedVolatility", 0)),
                            put_ltp=float(r.get("PE", {}).get("lastPrice", 0)),
                            put_change_oi=int(r.get("PE", {}).get("changeinOpenInterest", 0)),
                        )
                        for r in records
                        if r.get("strikePrice") and r.get("CE") and r.get("PE")
                    ]
                    
        except Exception as e:
            logger.error("get_option_chain_failed", symbol=symbol, error=str(e))
        
        return []
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols on NSE."""
        try:
            client = self._get_http_client()
            headers = {"Authorization": f"Bearer {self._tokens.get('jwtToken', '')}"}
            
            params = {"exchange": "NSE", "searchscrip": query}
            
            response = await client.get(
                f"{SMARTAPI_API_PATH}/marketData/searchScrip",
                params=params,
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    results = data.get("data", [])
                    return [
                        {
                            "symbol": r.get("symbol", ""),
                            "name": r.get("symbol", ""),
                            "token": r.get("token", ""),
                            "type": r.get("instrumenttype", ""),
                        }
                        for r in results[:10]
                    ]
                    
        except Exception as e:
            logger.error("search_symbols_failed", query=query, error=str(e))
        
        return []
    
    def _angelone_to_ticker(self, quote: AngelOneQuote) -> TickerData:
        """Convert Angel One quote format to standard TickerData."""
        return TickerData(
            symbol=quote.symbol,
            name=quote.symbol,
            price=quote.ltp,
            change=quote.change,
            change_percent=quote.change_percent,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            previous_close=quote.close,
            volume=quote.volume,
            timestamp=quote.timestamp,
        )
    
    async def connect_websocket(self) -> bool:
        """Connect to Angel One WebSocket for real-time data.
        
        This provides live tick-by-tick data for subscribed symbols.
        """
        if not self.is_configured:
            logger.warning("angel_one_not_configured")
            return False
        
        if self._ws_client is not None:
            return True
        
        try:
            # Generate request token via login first
            if not self._tokens.get("jwtToken"):
                await self.login()
            
            # Connect to WebSocket
            ws_url = f"{SMARTAPI_WS_URL}?api_key={self.config.api_key}"
            self._ws_client = await websockets.connect(ws_url)
            
            # Authenticate
            auth_params = {
                "action": "login",
                "params": {
                    "apiKey": self.config.api_key,
                    "clientCode": self.config.client_code,
                    "jwtToken": self._tokens.get("jwtToken", ""),
                    "refreshToken": self._tokens.get("refreshToken", ""),
                    "feedToken": self._feed_token,
                }
            }
            await self._ws_client.send(json.dumps(auth_params))
            
            # Wait for auth response
            response = await asyncio.wait_for(
                self._ws_client.recv(),
                timeout=10.0
            )
            
            auth_data = json.loads(response)
            if auth_data.get("status") or auth_data.get("action") == "login":
                logger.info("angel_one_ws_connected")
                # Start message handler
                asyncio.create_task(self._ws_message_handler())
                return True
                
        except Exception as e:
            logger.error("angel_one_ws_connect_failed", error=str(e))
            self._ws_client = None
        
        return False
    
    async def _ws_message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self._ws_client:
                try:
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data.get("action") == "subscribe":
                        await self._handle_subscription_data(data)
                    elif data.get("type") == "quote":
                        await self._handle_quote_update(data)
                        
                except json.JSONDecodeError:
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("angel_one_ws_disconnected")
            self._ws_client = None
    
    async def _handle_quote_update(self, data: Dict):
        """Handle quote update from WebSocket."""
        try:
            tokens = data.get("tokens", [])
            for token_data in tokens:
                symbol = token_data.get("symbol", "")
                quote = AngelOneQuote(
                    symbol=symbol,
                    token=token_data.get("token", ""),
                    exchange=token_data.get("exchange", ""),
                    ltp=float(token_data.get("ltp", 0)),
                    change=float(token_data.get("change", 0)),
                    change_percent=float(token_data.get("percentChange", 0)),
                    open=float(token_data.get("open", 0)),
                    high=float(token_data.get("high", 0)),
                    low=float(token_data.get("low", 0)),
                    close=float(token_data.get("close", 0)),
                    volume=int(token_data.get("volume", 0)),
                    timestamp=datetime.utcnow(),
                )
                
                async with self._cache_lock:
                    self._quote_cache[symbol.upper()] = quote
                    
        except Exception as e:
            logger.error("handle_quote_update_failed", error=str(e))
    
    async def _handle_subscription_data(self, data: Dict):
        """Handle subscription response."""
        if data.get("status"):
            logger.info("subscription_success", symbols=data.get("subscription", []))
    
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to real-time quotes for symbols."""
        if not self._ws_client:
            connected = await self.connect_websocket()
            if not connected:
                return False
        
        try:
            # Convert symbols to tokens
            tokens = []
            for symbol in symbols:
                token = self._symbol_tokens.get(symbol.upper(), "")
                if token:
                    tokens.append(f"NSE|{token}")
                    self._ws_subscriptions.add(symbol.upper())
            
            if tokens:
                subscribe_params = {
                    "action": "subscribe",
                    "params": {"mode": "FULL", "tokens": tokens}
                }
                await self._ws_client.send(json.dumps(subscribe_params))
                logger.info("subscribed", count=len(tokens))
                return True
                
        except Exception as e:
            logger.error("subscribe_failed", error=str(e))
        
        return False
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols."""
        if not self._ws_client:
            return False
        
        try:
            tokens = []
            for symbol in symbols:
                token = self._symbol_tokens.get(symbol.upper(), "")
                if token:
                    tokens.append(f"NSE|{token}")
                    self._ws_subscriptions.discard(symbol.upper())
            
            if tokens:
                unsubscribe_params = {
                    "action": "unsubscribe",
                    "params": {"mode": "FULL", "tokens": tokens}
                }
                await self._ws_client.send(json.dumps(unsubscribe_params))
                return True
                
        except Exception as e:
            logger.error("unsubscribe_failed", error=str(e))
        
        return False
    
    async def disconnect_websocket(self):
        """Disconnect from WebSocket."""
        if self._ws_client:
            try:
                await self._ws_client.close()
            except Exception:
                pass
            self._ws_client = None
            self._ws_subscriptions.clear()
    
    async def is_available(self) -> bool:
        """Check if provider is available."""
        if not self.is_configured:
            return False
        
        try:
            # Try a simple API call
            client = self._get_http_client()
            response = await client.get("/restful/apis/marketData/optionChain")
            # Will return auth error but confirms endpoint is reachable
            return response.status_code in [200, 401]
        except Exception:
            return False
    
    async def close(self):
        """Clean up resources."""
        await self.disconnect_websocket()
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Factory function
def create_angel_one_provider(
    api_key: str = "",
    client_code: str = "",
    password: str = "",
    totp_secret: str = "",
) -> AngelOneProvider:
    """Create Angel One provider with configuration."""
    config = AngelOneConfig(
        api_key=api_key,
        client_code=client_code,
        password=password,
        totp_secret=totp_secret,
    )
    return AngelOneProvider(config)
