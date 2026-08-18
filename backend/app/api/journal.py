from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import structlog

from app.schemas.journal import (
    Trade,
    TradeCreate,
    TradeUpdate,
    TradeFilters,
    PerformanceMetrics,
)

logger = structlog.get_logger()
router = APIRouter()

# NOTE: There is no journal persistence layer wired in this environment, so the
# production-safe behaviour is to return a truthful empty state rather than
# fabricate random trades/P&L. When a real store is added, these endpoints
# should read from it; until then they return [] / zeroed metrics so the UI can
# show "No trading history available" instead of fake numbers.


@router.get("/", response_model=List[Trade])
async def get_trades(
    user_id: str = "user_1",
    filters: Optional[TradeFilters] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get user's trade history.

    No persistence layer is configured, so this returns an empty list (a
    truthful "no trading history" state) rather than fabricated trades.
    """
    logger.info("fetching_trades", user_id=user_id, limit=limit, offset=offset)
    return []


@router.get("/{trade_id}", response_model=Trade)
async def get_trade(trade_id: str):
    """Get a specific trade.

    No persistence layer is configured; a non-existent trade is a 404, not a
    fabricated record.
    """
    logger.info("fetching_trade", trade_id=trade_id)
    raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")


@router.post("/", response_model=Trade, status_code=201)
async def create_trade(trade_data: TradeCreate, user_id: str = "user_1"):
    """Create a new trade.

    Constructs the response from the request payload (not fabricated market
    data). The generated ID is a request-scoped identifier; wire a real store to
    persist it.
    """
    import uuid

    logger.info("creating_trade", user_id=user_id, symbol=trade_data.symbol)
    now = datetime.utcnow()
    return Trade(
        id=f"trade_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        symbol=trade_data.symbol,
        instrument=trade_data.instrument,
        type=trade_data.type,
        entry={
            "price": trade_data.entry_price,
            "quantity": trade_data.quantity,
            "timestamp": now,
        },
        status="open",
        strategy=trade_data.strategy or "Manual",
        tags=trade_data.tags or [],
        created_at=now,
        updated_at=now,
    )


@router.put("/{trade_id}", response_model=Trade)
async def update_trade(trade_id: str, updates: TradeUpdate):
    """Update a trade (add exit, notes, etc.).

    Without persistence there is nothing to update; return 404 truthfully.
    """
    logger.info("updating_trade", trade_id=trade_id)
    raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")


@router.get("/metrics/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(user_id: str = "user_1"):
    """Get trading performance metrics"""
    logger.info("fetching_performance_metrics", user_id=user_id)

    trades = await get_trades(user_id, limit=100)
    closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]

    winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in closed_trades if t.pnl and t.pnl <= 0]

    total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
    avg_win = (
        sum(t.pnl for t in winning_trades if t.pnl) / len(winning_trades)
        if winning_trades
        else 0
    )
    avg_loss = (
        sum(t.pnl for t in losing_trades if t.pnl) / len(losing_trades)
        if losing_trades
        else 0
    )

    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
    profit_factor = (
        abs(
            sum(t.pnl for t in winning_trades if t.pnl)
            / sum(t.pnl for t in losing_trades if t.pnl)
        )
        if losing_trades and sum(t.pnl for t in losing_trades if t.pnl) != 0
        else 0
    )

    return PerformanceMetrics(
        total_trades=len(closed_trades),
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=round(win_rate, 2),
        average_win=round(avg_win, 2),
        average_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2),
        total_pnl=round(total_pnl, 2),
        expectancy=round(
            (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * abs(avg_loss)), 2
        ),
        source="journal",
    )
