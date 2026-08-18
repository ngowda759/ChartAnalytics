from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import uuid
import structlog

from app.schemas.strategies import (
    Strategy,
    StrategyCreate,
    StrategyUpdate,
    BacktestResult,
    BacktestParams,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=List[Strategy])
async def get_strategies(user_id: str = "user_1"):
    """Get user's strategies"""
    logger.info("fetching_strategies", user_id=user_id)

    return [
        Strategy(
            id="strat_1",
            user_id=user_id,
            name="VWAP Breakout",
            type="VWAP",
            description="Buy on VWAP cross above with confirmation",
            parameters={"vwap_period": 1, "confirmation_candles": 2},
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Strategy(
            id="strat_2",
            user_id=user_id,
            name="EMA Crossover",
            type="EMA_CROSSOVER",
            description="Golden cross entry, death cross exit",
            parameters={"fast_ema": 20, "slow_ema": 50},
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: str):
    """Get a specific strategy"""
    logger.info("fetching_strategy", strategy_id=strategy_id)

    return Strategy(
        id=strategy_id,
        user_id="user_1",
        name="ORB Strategy",
        type="ORB",
        description="Opening Range Breakout",
        parameters={"orb_period": 15, "breakout_threshold": 0.5},
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.post("", response_model=Strategy, status_code=201)
async def create_strategy(data: StrategyCreate, user_id: str = "user_1"):
    """Create a new strategy"""
    logger.info("creating_strategy", user_id=user_id)
    now = datetime.utcnow()
    return Strategy(
        id=f"strat_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        name=data.name,
        type=data.type,
        description=data.description,
        parameters=data.parameters or {},
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@router.post("/{strategy_id}/backtest", response_model=BacktestResult)
async def backtest_strategy(strategy_id: str, params: BacktestParams):
    """Run backtest on a strategy.

    No backtest engine / historical data source is wired, so fabricating
    performance metrics (returns, win rate, sharpe, etc.) would mislead. Return
    a truthful empty/unavailable result instead of random numbers.
    """
    logger.info("running_backtest", strategy_id=strategy_id)
    return BacktestResult(
        strategy_id=strategy_id,
        period={"start_date": params.start_date, "end_date": params.end_date},
        metrics={
            "total_return": 0.0,
            "annualized_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "total_trades": 0,
            "avg_trade_duration": 0,
            "recovery_factor": 0.0,
        },
        equity_curve=[],
        trades=[],
    )
