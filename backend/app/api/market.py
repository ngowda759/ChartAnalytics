from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import structlog

from app.schemas.market import (
    IndexQuote,
    MarketQuote,
    OHLC,
    HistoricalData,
    WatchlistItem,
    WatchlistCreate,
)

logger = structlog.get_logger()
router = APIRouter()


def generate_mock_quote(symbol: str, base_price: float) -> MarketQuote:
    """Generate mock market quote"""
    change = random.uniform(-2, 2)
    return MarketQuote(
        symbol=symbol,
        name=symbol,
        price=base_price,
        change=base_price * change / 100,
        change_percent=change,
        open=base_price * (1 + random.uniform(-0.5, 0.5) / 100),
        high=base_price * (1 + random.uniform(0.1, 1) / 100),
        low=base_price * (1 - random.uniform(0.1, 1) / 100),
        previous_close=base_price * (1 - change / 100),
        volume=random.randint(1000000, 50000000),
        timestamp=datetime.utcnow(),
    )


@router.get("/indices", response_model=List[IndexQuote])
async def get_indices():
    """Get all major market indices"""
    logger.info("fetching_indices")
    
    indices_data = [
        {"symbol": "NIFTY 50", "name": "NIFTY 50", "base_price": 24567.85},
        {"symbol": "BANKNIFTY", "name": "NIFTY Bank", "base_price": 52456.70},
        {"symbol": "FINNIFTY", "name": "NIFTY Fin Services", "base_price": 23456.30},
        {"symbol": "SENSEX", "name": "BSE Sensex", "base_price": 80789.45},
        {"symbol": "INDIA VIX", "name": "India VIX", "base_price": 14.56},
    ]
    
    return [
        IndexQuote(**generate_mock_quote(d["symbol"], d["base_price"]).dict(), is_index=True)
        for d in indices_data
    ]


@router.get("/quote/{symbol}", response_model=MarketQuote)
async def get_quote(symbol: str):
    """Get quote for a specific symbol"""
    logger.info("fetching_quote", symbol=symbol)
    
    base_prices = {
        "NIFTY": 24567.85,
        "BANKNIFTY": 52456.70,
        "FINNIFTY": 23456.30,
        "RELIANCE": 2967.50,
        "HDFCBANK": 1689.30,
        "ICICIBANK": 1124.75,
        "INFOSYS": 1834.20,
        "TCS": 4123.45,
    }
    
    base_price = base_prices.get(symbol.upper(), 10000)
    return generate_mock_quote(symbol.upper(), base_price)


@router.get("/ohlc/{symbol}", response_model=List[OHLC])
async def get_ohlc(
    symbol: str,
    interval: str = Query("5m", description="Time interval (1m, 5m, 15m, 1h, 1d)"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get OHLC data for charting"""
    logger.info("fetching_ohlc", symbol=symbol, interval=interval, limit=limit)
    
    # Generate mock OHLC data
    base_price = 24567.85
    if symbol.upper() == "BANKNIFTY":
        base_price = 52456.70
    elif symbol.upper() == "FINNIFTY":
        base_price = 23456.30
    
    interval_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "1d": 1440,
    }.get(interval, 5)
    
    candles = []
    current_price = base_price
    now = datetime.utcnow()
    
    for i in range(limit, 0, -1):
        timestamp = now - timedelta(minutes=i * interval_minutes)
        
        volatility = base_price * 0.002  # 0.2% volatility
        change = random.uniform(-volatility, volatility)
        
        open_price = current_price
        close_price = current_price + change
        high_price = max(open_price, close_price) + random.uniform(0, volatility / 2)
        low_price = min(open_price, close_price) - random.uniform(0, volatility / 2)
        
        candles.append(
            OHLC(
                timestamp=timestamp,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=random.randint(50000, 500000),
            )
        )
        
        current_price = close_price
    
    return candles


@router.get("/historical/{symbol}", response_model=HistoricalData)
async def get_historical_data(
    symbol: str,
    interval: str = Query("1d", description="Time interval"),
    range_from: Optional[datetime] = None,
    range_to: Optional[datetime] = None,
):
    """Get historical data for a symbol"""
    logger.info("fetching_historical", symbol=symbol, interval=interval)
    
    if range_from is None:
        range_from = datetime.utcnow() - timedelta(days=365)
    if range_to is None:
        range_to = datetime.utcnow()
    
    # Generate mock historical data
    base_price = 24567.85
    candles = []
    current_price = base_price
    current_date = range_from
    
    while current_date <= range_to:
        if interval == "1d":
            # Skip weekends
            if current_date.weekday() < 5:
                volatility = base_price * 0.015
                change = random.uniform(-volatility, volatility)
                
                candles.append(
                    OHLC(
                        timestamp=current_date,
                        open=round(current_price, 2),
                        high=round(current_price + abs(change) + random.uniform(0, volatility / 2), 2),
                        low=round(current_price - abs(change) - random.uniform(0, volatility / 2), 2),
                        close=round(current_price + change, 2),
                        volume=random.randint(1000000, 50000000),
                    )
                )
                current_price = current_price + change
        
        current_date += timedelta(days=1)
    
    return HistoricalData(
        symbol=symbol,
        interval=interval,
        data=candles,
        from_date=range_from,
        to_date=range_to,
    )


@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist(user_id: str = "user_1"):
    """Get user's watchlist"""
    logger.info("fetching_watchlist", user_id=user_id)
    
    # Mock watchlist
    symbols = [
        {"symbol": "NIFTY", "base_price": 24567.85},
        {"symbol": "BANKNIFTY", "base_price": 52456.70},
        {"symbol": "RELIANCE", "base_price": 2967.50},
        {"symbol": "HDFCBANK", "base_price": 1689.30},
        {"symbol": "ICICIBANK", "base_price": 1124.75},
    ]
    
    return [
        WatchlistItem(
            symbol=s["symbol"],
            name=s["symbol"],
            price=round(s["base_price"] * (1 + random.uniform(-0.5, 0.5) / 100), 2),
            change_percent=round(random.uniform(-2, 2), 2),
        )
        for s in symbols
    ]


@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(item: WatchlistCreate, user_id: str = "user_1"):
    """Add symbol to watchlist"""
    logger.info("adding_to_watchlist", user_id=user_id, symbol=item.symbol)
    
    return WatchlistItem(
        symbol=item.symbol,
        name=item.symbol,
        price=10000.00,
        change_percent=0.0,
    )


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, user_id: str = "user_1"):
    """Remove symbol from watchlist"""
    logger.info("removing_from_watchlist", user_id=user_id, symbol=symbol)
    
    return {"message": f"{symbol} removed from watchlist"}
