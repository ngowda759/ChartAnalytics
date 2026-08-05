"""Mock data provider for development and testing."""
import random
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

from .base import BaseDataProvider, TickerData, OHLCData, OptionChainData


@dataclass
class MarketIndex:
    """Market index configuration."""
    symbol: str
    name: str
    base_price: float
    volatility: float
    avg_volume: int


class MockDataProvider(BaseDataProvider):
    """Mock data provider that generates realistic market data."""
    
    def __init__(self):
        self._indices = [
            MarketIndex("NIFTY 50", "NIFTY 50", 24567.85, 0.015, 25000000),
            MarketIndex("NIFTY BANK", "BANKNIFTY", 52456.70, 0.018, 15000000),
            MarketIndex("NIFTY FIN SERVICE", "FINNIFTY", 23456.30, 0.016, 8000000),
            MarketIndex("SENSEX", "BSE SENSEX", 80789.45, 0.014, 5000000),
            MarketIndex("INDIA VIX", "India VIX", 14.56, 0.08, 1000000),
        ]
        
        self._stocks = {
            "RELIANCE": MarketIndex("RELIANCE", "Reliance Industries", 2967.50, 0.02, 10000000),
            "HDFCBANK": MarketIndex("HDFCBANK", "HDFC Bank", 1689.30, 0.018, 8000000),
            "ICICIBANK": MarketIndex("ICICIBANK", "ICICI Bank", 1124.75, 0.02, 7000000),
            "INFOSYS": MarketIndex("INFY", "Infosys", 1834.20, 0.022, 6000000),
            "TCS": MarketIndex("TCS", "Tata Consultancy", 4123.45, 0.015, 4000000),
            "HINDUNILVR": MarketIndex("HINDUNILVR", "Hindustan Unilever", 2645.80, 0.016, 3000000),
            "ITC": MarketIndex("ITC", "ITC Limited", 458.25, 0.017, 5000000),
            "KOTAKBANK": MarketIndex("KOTAKBANK", "Kotak Mahindra Bank", 1789.60, 0.02, 4000000),
            "SBIN": MarketIndex("SBIN", "State Bank of India", 785.40, 0.022, 10000000),
            "BHARTIARTL": MarketIndex("BHARTIARTL", "Bharti Airtel", 1234.50, 0.025, 6000000),
            "LT": MarketIndex("LT", "Larsen & Toubro", 3456.80, 0.018, 3000000),
            "AXISBANK": MarketIndex("AXISBANK", "Axis Bank", 1098.75, 0.022, 5000000),
        }
        
        self._last_prices: Dict[str, float] = {}
        for idx in self._indices:
            self._last_prices[idx.symbol] = idx.base_price
        for symbol, stock in self._stocks.items():
            self._last_prices[symbol] = stock.base_price
    
    @property
    def name(self) -> str:
        return "Mock Provider"
    
    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        """Generate realistic mock quote."""
        await asyncio.sleep(0.01)  # Simulate network delay
        
        symbol_upper = symbol.upper().replace(" ", "").replace("-", "")
        
        # Check if it's an index
        for idx in self._indices:
            if symbol_upper in idx.symbol.upper().replace(" ", ""):
                return self._generate_index_quote(idx)
        
        # Check stocks
        for stock_symbol, stock in self._stocks.items():
            if symbol_upper in stock_symbol or stock_symbol in symbol_upper:
                return self._generate_stock_quote(stock_symbol, stock)
        
        # Default: generate random stock
        return self._generate_random_quote(symbol)
    
    def _generate_index_quote(self, idx: MarketIndex) -> TickerData:
        """Generate quote for an index."""
        last_price = self._last_prices.get(idx.symbol, idx.base_price)
        
        # Add some momentum/trending
        change_percent = random.gauss(0, idx.volatility * 100)
        change_percent = max(-5, min(5, change_percent))  # Cap at ±5%
        
        price = last_price * (1 + change_percent / 100)
        
        # OHLC
        open_price = last_price * (1 + random.uniform(-0.5, 0.5) / 100)
        high_price = max(price, open_price) * (1 + random.uniform(0, 0.5) / 100)
        low_price = min(price, open_price) * (1 - random.uniform(0, 0.5) / 100)
        
        # Previous close (slightly different from open)
        prev_close = open_price * (1 - random.uniform(-0.2, 0.2) / 100)
        
        self._last_prices[idx.symbol] = price
        
        return TickerData(
            symbol=idx.symbol,
            name=idx.name,
            price=round(price, 2),
            change=round(price - prev_close, 2),
            change_percent=round(change_percent, 2),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(price, 2),
            previous_close=round(prev_close, 2),
            volume=random.randint(idx.avg_volume // 2, idx.avg_volume * 2),
            timestamp=datetime.utcnow(),
            metadata={"index": True},
        )
    
    def _generate_stock_quote(self, symbol: str, stock: MarketIndex) -> TickerData:
        """Generate quote for a stock."""
        last_price = self._last_prices.get(symbol, stock.base_price)
        
        change_percent = random.gauss(0, stock.volatility * 100)
        change_percent = max(-8, min(8, change_percent))
        
        price = last_price * (1 + change_percent / 100)
        
        open_price = last_price * (1 + random.uniform(-1, 1) / 100)
        high_price = max(price, open_price) * (1 + random.uniform(0, 1) / 100)
        low_price = min(price, open_price) * (1 - random.uniform(0, 1) / 100)
        prev_close = open_price * (1 - random.uniform(-0.3, 0.3) / 100)
        
        self._last_prices[symbol] = price
        
        return TickerData(
            symbol=symbol,
            name=stock.name,
            price=round(price, 2),
            change=round(price - prev_close, 2),
            change_percent=round(change_percent, 2),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(price, 2),
            previous_close=round(prev_close, 2),
            volume=random.randint(stock.avg_volume // 2, stock.avg_volume * 2),
            timestamp=datetime.utcnow(),
            metadata={"stock": True, "segment": "EQ"},
        )
    
    def _generate_random_quote(self, symbol: str) -> TickerData:
        """Generate random quote for unknown symbol."""
        base_price = random.uniform(100, 5000)
        change_percent = random.gauss(0, 2)
        
        price = base_price * (1 + change_percent / 100)
        prev_close = base_price
        
        return TickerData(
            symbol=symbol,
            name=symbol,
            price=round(price, 2),
            change=round(price - prev_close, 2),
            change_percent=round(change_percent, 2),
            open=round(base_price * (1 + random.uniform(-0.5, 0.5) / 100), 2),
            high=round(price * (1 + random.uniform(0, 1) / 100), 2),
            low=round(price * (1 - random.uniform(0, 1) / 100), 2),
            close=round(price, 2),
            previous_close=round(prev_close, 2),
            volume=random.randint(100000, 10000000),
            timestamp=datetime.utcnow(),
        )
    
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
        """Generate realistic OHLC data."""
        await asyncio.sleep(0.01)
        
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=limit)
        
        # Get base price
        quote = await self.get_quote(symbol)
        base_price = quote.price if quote else 25000
        
        # Interval to minutes
        interval_minutes = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
        }.get(interval, 1440)
        
        candles = []
        current_price = base_price * random.uniform(0.85, 0.95)  # Start lower
        volatility = base_price * 0.005
        
        current_time = start_date
        candle_count = 0
        
        while current_time <= end_date and candle_count < limit:
            # Skip weekends for daily+ intervals
            if interval in ["1d", "1w"] and current_time.weekday() >= 5:
                current_time += timedelta(days=1)
                continue
            
            # Add trend component
            trend = 0.0002 if candle_count % 10 < 7 else -0.0003
            change = random.gauss(trend * interval_minutes, volatility)
            
            open_price = current_price
            close_price = current_price + change
            high_price = max(open_price, close_price) + random.uniform(0, volatility / 2)
            low_price = min(open_price, close_price) - random.uniform(0, volatility / 2)
            
            # Volume with occasional spikes
            base_volume = 500000 if interval == "1d" else 50000
            volume_mult = random.uniform(0.5, 2.0)
            if random.random() < 0.1:  # 10% chance of volume spike
                volume_mult *= random.uniform(2, 4)
            
            candles.append(OHLCData(
                timestamp=current_time,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=int(base_volume * volume_mult),
            ))
            
            current_price = close_price
            current_time += timedelta(minutes=interval_minutes)
            candle_count += 1
        
        return candles
    
    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Generate realistic option chain data."""
        await asyncio.sleep(0.02)
        
        # Get underlying price
        quote = await self.get_quote(symbol)
        spot_price = quote.price if quote else 25000
        
        if expiry is None:
            # Next Friday
            today = datetime.utcnow()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            expiry_date = today + timedelta(days=days_until_friday)
        else:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
        
        # Calculate ATM strike
        atm_strike = round(spot_price / 50) * 50  # Round to nearest 50
        
        # Generate strikes around ATM
        strikes = [atm_strike + i * 50 for i in range(-20, 21)]
        
        # IV smile - higher at wings
        def get_iv(strike: float) -> float:
            moneyness = abs(strike - spot_price) / spot_price
            base_iv = 15 + moneyness * 100
            return min(60, max(8, base_iv + random.gauss(0, 2)))
        
        option_chain = []
        for strike in strikes:
            # Calls
            intrinsic_call = max(0, spot_price - strike)
            call_iv = get_iv(strike)
            call_ltp = intrinsic_call * random.uniform(0.85, 1.15) + 5 if intrinsic_call > 0 else random.uniform(1, 10)
            
            # Puts
            intrinsic_put = max(0, strike - spot_price)
            put_iv = get_iv(strike)
            put_ltp = intrinsic_put * random.uniform(0.85, 1.15) + 5 if intrinsic_put > 0 else random.uniform(1, 10)
            
            # OI increases away from ATM
            moneyness_factor = 1 - moneyness = abs(strike - spot_price) / spot_price
            oi_base = int(50000 * (1 - moneyness_factor * 2))
            
            option_chain.append(OptionChainData(
                symbol=symbol,
                expiry_date=expiry_date,
                strike=strike,
                call_oi=random.randint(max(10000, oi_base), max(50000, oi_base * 2)),
                call_volume=random.randint(10000, 100000),
                call_iv=round(call_iv, 2),
                call_ltp=round(call_ltp, 2),
                call_change_oi=random.randint(-50000, 100000),
                put_oi=random.randint(max(10000, oi_base), max(50000, oi_base * 2)),
                put_volume=random.randint(10000, 100000),
                put_iv=round(put_iv, 2),
                put_ltp=round(put_ltp, 2),
                put_change_oi=random.randint(-50000, 100000),
            ))
        
        return option_chain
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols."""
        await asyncio.sleep(0.01)
        
        query_upper = query.upper()
        results = []
        
        # Search indices
        for idx in self._indices:
            if query_upper in idx.symbol.upper() or query_upper in idx.name.upper():
                results.append({
                    "symbol": idx.symbol,
                    "name": idx.name,
                    "type": "INDEX",
                })
        
        # Search stocks
        for symbol, stock in self._stocks.items():
            if query_upper in symbol or query_upper in stock.name.upper():
                results.append({
                    "symbol": symbol,
                    "name": stock.name,
                    "type": "STOCK",
                })
        
        return results[:10]
    
    async def is_available(self) -> bool:
        """Mock provider is always available."""
        return True
