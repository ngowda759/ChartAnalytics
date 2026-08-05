from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import structlog

from app.schemas.journal import (
    Trade,
    TradeCreate,
    TradeUpdate,
    TradeFilters,
    PerformanceMetrics,
    MonthlyReturn,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[Trade])
async def get_trades(
    user_id: str = "user_1",
    filters: Optional[TradeFilters] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get user's trade history"""
    logger.info("fetching_trades", user_id=user_id)

    # Mock trades
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK"]
    trades = []

    for i in range(min(limit, 20)):
        entry_price = 24567.85 * random.uniform(0.98, 1.02)
        exit_price = entry_price * random.uniform(0.97, 1.03)
        quantity = random.choice([50, 75, 100, 150, 200])

        trade = Trade(
            id=f"trade_{i + 1}",
            user_id=user_id,
            symbol=random.choice(symbols),
            instrument=random.choice(["futures", "options", "equity"]),
            type=random.choice(["long", "short"]),
            entry={
                "price": round(entry_price, 2),
                "quantity": quantity,
                "timestamp": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            },
            exit=(
                {
                    "price": round(exit_price, 2),
                    "quantity": quantity,
                    "timestamp": datetime.utcnow()
                    - timedelta(days=random.randint(0, 29)),
                }
                if random.random() > 0.3
                else None
            ),
            status=(
                random.choice(["open", "closed", "cancelled"])
                if random.random() > 0.2
                else "closed"
            ),
            strategy=random.choice(["ORB", "VWAP", "EMA", "Momentum", "Scalping"]),
            tags=random.sample(
                ["intraday", "swing", "options", "futures", "bullish", "bearish"], k=2
            ),
            pnl=round(
                (exit_price - entry_price)
                * quantity
                * (1 if random.random() > 0.5 else -1),
                2,
            ),
            fees=round(random.uniform(50, 500), 2),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            updated_at=datetime.utcnow(),
        )
        trades.append(trade)

    return trades


@router.get("/{trade_id}", response_model=Trade)
async def get_trade(trade_id: str):
    """Get a specific trade"""
    logger.info("fetching_trade", trade_id=trade_id)

    entry_price = 24567.85
    quantity = 100

    return Trade(
        id=trade_id,
        user_id="user_1",
        symbol="NIFTY",
        instrument="futures",
        type="long",
        entry={
            "price": entry_price,
            "quantity": quantity,
            "timestamp": datetime.utcnow() - timedelta(hours=2),
        },
        exit={
            "price": entry_price * 1.01,
            "quantity": quantity,
            "timestamp": datetime.utcnow(),
        },
        status="closed",
        strategy="VWAP",
        tags=["intraday", "bullish"],
        pnl=round((entry_price * 1.01 - entry_price) * quantity, 2),
        fees=200,
        created_at=datetime.utcnow() - timedelta(hours=2),
        updated_at=datetime.utcnow(),
    )


@router.post("/", response_model=Trade, status_code=201)
async def create_trade(trade_data: TradeCreate, user_id: str = "user_1"):
    """Create a new trade"""
    logger.info("creating_trade", user_id=user_id)

    return Trade(
        id=f"trade_{random.randint(1000, 9999)}",
        user_id=user_id,
        symbol=trade_data.symbol,
        instrument=trade_data.instrument,
        type=trade_data.type,
        entry={
            "price": trade_data.entry_price,
            "quantity": trade_data.quantity,
            "timestamp": datetime.utcnow(),
        },
        status="open",
        strategy=trade_data.strategy or "Manual",
        tags=trade_data.tags or [],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.put("/{trade_id}", response_model=Trade)
async def update_trade(trade_id: str, updates: TradeUpdate):
    """Update a trade (add exit, notes, etc.)"""
    logger.info("updating_trade", trade_id=trade_id)

    trade = await get_trade(trade_id)

    if updates.exit_price:
        trade.exit = {
            "price": updates.exit_price,
            "quantity": updates.exit_quantity or trade.entry["quantity"],
            "timestamp": datetime.utcnow(),
        }
        trade.status = "closed"

        # Calculate P&L
        multiplier = 1 if trade.type == "long" else -1
        trade.pnl = round(
            (trade.exit["price"] - trade.entry["price"])
            * trade.exit["quantity"]
            * multiplier,
            2,
        )

    if updates.notes:
        trade.notes = updates.notes

    if updates.tags:
        trade.tags = updates.tags

    trade.updated_at = datetime.utcnow()

    return trade


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
        sharpe_ratio=round(random.uniform(0.5, 2.5), 2),
        max_drawdown=round(random.uniform(5, 15), 2),
        max_drawdown_percent=round(random.uniform(8, 20), 2),
        total_pnl=round(total_pnl, 2),
        expectancy=round(
            (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * abs(avg_loss)), 2
        ),
        avg_rr=round(random.uniform(1.2, 2.5), 2),
        monthly_returns=[
            MonthlyReturn(
                month="Jan",
                return_value=round(random.uniform(-5, 10), 2),
                trades=random.randint(5, 20),
            ),
            MonthlyReturn(
                month="Feb",
                return_value=round(random.uniform(-3, 8), 2),
                trades=random.randint(5, 20),
            ),
            MonthlyReturn(
                month="Mar",
                return_value=round(random.uniform(-8, 12), 2),
                trades=random.randint(5, 20),
            ),
            MonthlyReturn(
                month="Apr",
                return_value=round(random.uniform(-2, 15), 2),
                trades=random.randint(5, 20),
            ),
            MonthlyReturn(
                month="May",
                return_value=round(random.uniform(-10, 5), 2),
                trades=random.randint(5, 20),
            ),
            MonthlyReturn(
                month="Jun",
                return_value=round(random.uniform(-5, 8), 2),
                trades=random.randint(5, 20),
            ),
        ],
    )
