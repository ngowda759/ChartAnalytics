"""Backtesting API - Historical strategy testing endpoints."""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.services.backtesting import (
    backtesting_engine,
    BacktestPeriod,
    OHLCV,
)

logger = structlog.get_logger()
router = APIRouter()


from pydantic import BaseModel


class BacktestRequest(BaseModel):
    strategy_name: str
    strategy_type: str
    parameters: dict = {}
    period: str = "1M"
    initial_capital: float = 100000


class BacktestTradeResponse(BaseModel):
    entry_date: datetime
    exit_date: datetime
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    holding_period: int
    exit_reason: str


class BacktestMetricsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    max_drawdown_duration: int
    total_return: float
    annualized_return: float
    avg_trade_duration: float
    recovery_factor: float
    calmar_ratio: float


class BacktestResponse(BaseModel):
    strategy_name: str
    period: str
    start_date: datetime
    end_date: datetime
    metrics: BacktestMetricsResponse
    trades: List[BacktestTradeResponse]
    equity_curve: List[dict]
    monthly_returns: List[dict]
    errors: List[str]


def _period_bars(period: BacktestPeriod) -> int:
    """Approximate number of daily bars for a backtest period."""
    return {
        BacktestPeriod.ONE_WEEK: 5,
        BacktestPeriod.ONE_MONTH: 22,
        BacktestPeriod.THREE_MONTHS: 66,
        BacktestPeriod.SIX_MONTHS: 132,
        BacktestPeriod.ONE_YEAR: 252,
    }.get(period, 66)


def fetch_backtest_data(symbol: str, num_bars: int) -> List[OHLCV]:
    """Fetch REAL OHLCV history for backtesting from the unified market layer.

    No fabricated candles: when the live provider is unavailable the backtest
    returns an empty dataset (and the endpoint surfaces 503) rather than
    running on random noise.
    """
    from app.services import market_data

    candles, src = market_data.get_real_candles(symbol, interval="1d", limit=num_bars)
    if not candles:
        return []
    return [
        OHLCV(
            timestamp=c.date,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles
    ]


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run a backtest on real historical data."""
    logger.info("running_backtest", strategy=request.strategy_name, period=request.period)

    try:
        period = BacktestPeriod(request.period)
    except ValueError:
        period = BacktestPeriod.ONE_MONTH

    # Fetch real OHLCV; default to NIFTY when no symbol is supplied.
    symbol = request.parameters.get("symbol", "NIFTY")
    data = fetch_backtest_data(symbol, _period_bars(period))
    if not data:
        raise HTTPException(
            status_code=503,
            detail=(
                "Backtest unavailable: no real historical OHLCV could be loaded "
                f"for {symbol}. Configure a live market-data provider."
            ),
        )

    result = backtesting_engine.run_backtest(
        strategy_name=request.strategy_name,
        strategy_params={
            "type": request.strategy_type,
            **request.parameters,
        },
        price_data=data,
        period=period,
    )

    return BacktestResponse(
        strategy_name=result.strategy_name,
        period=result.period.value,
        start_date=result.start_date,
        end_date=result.end_date,
        metrics=BacktestMetricsResponse(
            total_trades=result.metrics.total_trades,
            winning_trades=result.metrics.winning_trades,
            losing_trades=result.metrics.losing_trades,
            win_rate=result.metrics.win_rate,
            average_win=result.metrics.average_win,
            average_loss=result.metrics.average_loss,
            profit_factor=result.metrics.profit_factor,
            sharpe_ratio=result.metrics.sharpe_ratio,
            sortino_ratio=result.metrics.sortino_ratio,
            max_drawdown=result.metrics.max_drawdown,
            max_drawdown_percent=result.metrics.max_drawdown_percent,
            max_drawdown_duration=result.metrics.max_drawdown_duration,
            total_return=result.metrics.total_return,
            annualized_return=result.metrics.annualized_return,
            avg_trade_duration=result.metrics.avg_trade_duration,
            recovery_factor=result.metrics.recovery_factor,
            calmar_ratio=result.metrics.calmar_ratio,
        ),
        trades=[
            BacktestTradeResponse(
                entry_date=t.entry_date,
                exit_date=t.exit_date,
                symbol=t.symbol,
                direction=t.direction,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                quantity=t.quantity,
                pnl=t.pnl,
                pnl_percent=t.pnl_percent,
                holding_period=t.holding_period,
                exit_reason=t.exit_reason,
            )
            for t in result.trades
        ],
        equity_curve=result.equity_curve,
        monthly_returns=result.monthly_returns,
        errors=result.errors,
    )


@router.get("/strategies")
async def list_strategy_types():
    """List available strategy types for backtesting."""
    return {
        "types": [
            {"value": "EMA_CROSSOVER", "name": "EMA Crossover", "description": "Trade when fast EMA crosses slow EMA"},
            {"value": "RSI", "name": "RSI Reversal", "description": "Trade RSI overbought/oversold reversals"},
            {"value": "VWAP", "name": "VWAP", "description": "Trade VWAP breakouts and bounces"},
            {"value": "MOMENTUM", "name": "Momentum", "description": "Trade with momentum indicators"},
            {"value": "BREAKOUT", "name": "Breakout", "description": "Trade price breakouts from ranges"},
        ],
        "periods": [
            {"value": "1W", "name": "1 Week"},
            {"value": "1M", "name": "1 Month"},
            {"value": "3M", "name": "3 Months"},
            {"value": "6M", "name": "6 Months"},
            {"value": "1Y", "name": "1 Year"},
        ],
    }


@router.get("/sample-data")
async def get_sample_data(symbol: str = "NIFTY", bars: int = 100):
    """Get real OHLCV history for a symbol (no fabricated data)."""
    logger.info("getting_sample_data", symbol=symbol, bars=bars)

    data = fetch_backtest_data(symbol, bars)
    if not data:
        raise HTTPException(
            status_code=503,
            detail=f"Real OHLCV unavailable for {symbol}.",
        )

    return [
        {
            "timestamp": d.timestamp.isoformat(),
            "open": d.open,
            "high": d.high,
            "low": d.low,
            "close": d.close,
            "volume": d.volume,
        }
        for d in data
    ]
