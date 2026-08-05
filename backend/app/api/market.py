from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.schemas.market import (
    IndexQuote,
    MarketQuote,
    OHLC,
    HistoricalData,
    WatchlistItem,
    WatchlistCreate,
)
from app.services.market_service import get_market_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/indices", response_model=List[IndexQuote])
async def get_indices():
    """Get all major market indices with real-time data"""
    logger.info("fetching_indices")

    service = get_market_service()
    quotes = await service.get_indices()

    return [
        IndexQuote(
            symbol=q.symbol,
            name=q.name,
            price=q.price,
            change=q.change,
            change_percent=q.change_percent,
            open=q.open,
            high=q.high,
            low=q.low,
            previous_close=q.previous_close,
            volume=q.volume,
            timestamp=q.timestamp,
            is_index=True,
        )
        for q in quotes
    ]


@router.get("/quote/{symbol}", response_model=MarketQuote)
async def get_quote(symbol: str, force_refresh: bool = False):
    """Get real-time quote for a symbol"""
    logger.info("fetching_quote", symbol=symbol, force_refresh=force_refresh)

    service = get_market_service()
    quote = await service.get_quote(symbol, force_refresh)

    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    return MarketQuote(
        symbol=quote.symbol,
        name=quote.name,
        price=quote.price,
        change=quote.change,
        change_percent=quote.change_percent,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        previous_close=quote.previous_close,
        volume=quote.volume,
        timestamp=quote.timestamp,
    )


@router.get("/ohlc/{symbol}", response_model=List[OHLC])
async def get_ohlc(
    symbol: str,
    interval: str = Query("5m", description="Time interval (1m, 5m, 15m, 30m, 1h, 1d)"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get OHLC data for charting"""
    logger.info("fetching_ohlc", symbol=symbol, interval=interval, limit=limit)

    service = get_market_service()
    ohlc_data = await service.get_ohlc(symbol, interval, limit)

    return [
        OHLC(
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in ohlc_data
    ]


@router.get("/historical/{symbol}", response_model=HistoricalData)
async def get_historical_data(
    symbol: str,
    interval: str = Query("1d", description="Time interval (1m, 5m, 15m, 1h, 1d, 1w)"),
    range_from: Optional[datetime] = None,
    range_to: Optional[datetime] = None,
):
    """Get historical OHLC data for a symbol"""
    logger.info("fetching_historical", symbol=symbol, interval=interval)

    if range_from is None:
        range_from = datetime.utcnow() - timedelta(days=365)
    if range_to is None:
        range_to = datetime.utcnow()

    service = get_market_service()
    ohlc_data = await service.get_ohlc(symbol, interval, 500)

    # Filter by date range
    filtered_data = [c for c in ohlc_data if range_from <= c.timestamp <= range_to]

    return HistoricalData(
        symbol=symbol,
        interval=interval,
        data=[
            OHLC(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in filtered_data
        ],
        from_date=range_from,
        to_date=range_to,
    )


@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist(user_id: str = "user_1"):
    """Get user's watchlist"""
    logger.info("fetching_watchlist", user_id=user_id)

    # Default watchlist
    symbols = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "RELIANCE", "HDFCBANK"]

    service = get_market_service()
    quotes = await service.get_quotes(symbols)

    return [
        WatchlistItem(
            symbol=q.symbol,
            name=q.name,
            price=q.price,
            change_percent=q.change_percent,
        )
        for q in quotes
    ]


@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(item: WatchlistCreate, user_id: str = "user_1"):
    """Add symbol to watchlist"""
    logger.info("adding_to_watchlist", user_id=user_id, symbol=item.symbol)

    service = get_market_service()
    quote = await service.get_quote(item.symbol)

    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol {item.symbol} not found")

    return WatchlistItem(
        symbol=quote.symbol,
        name=quote.name,
        price=quote.price,
        change_percent=quote.change_percent,
    )


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, user_id: str = "user_1"):
    """Remove symbol from watchlist"""
    logger.info("removing_from_watchlist", user_id=user_id, symbol=symbol)

    return {"message": f"{symbol} removed from watchlist"}


@router.get("/search")
async def search_symbols(q: str = Query(..., min_length=1)):
    """Search for symbols"""
    logger.info("searching_symbols", query=q)

    service = get_market_service()
    results = await service.search_symbols(q)

    return {"results": results}
