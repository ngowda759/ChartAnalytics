"""Backtesting Service - Historical strategy testing and performance analysis."""
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import structlog

logger = structlog.get_logger()


class BacktestPeriod(str, Enum):
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1Y"
    YTD = "YTD"


@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class BacktestTrade:
    entry_date: datetime
    exit_date: datetime
    symbol: str
    direction: str  # "long" or "short"
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    holding_period: int  # in bars
    exit_reason: str


@dataclass
class BacktestMetrics:
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
    max_drawdown_duration: int  # in days
    total_return: float
    annualized_return: float
    avg_trade_duration: float
    recovery_factor: float
    calmar_ratio: float


@dataclass
class BacktestResult:
    strategy_name: str
    period: BacktestPeriod
    start_date: datetime
    end_date: datetime
    metrics: BacktestMetrics
    trades: List[BacktestTrade]
    equity_curve: List[Dict[str, Any]]
    monthly_returns: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)


class BacktestingEngine:
    """Service for backtesting trading strategies."""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.logger = structlog.get_logger()

    def run_backtest(
        self,
        strategy_name: str,
        strategy_params: Dict[str, Any],
        price_data: List[OHLCV],
        period: BacktestPeriod,
    ) -> BacktestResult:
        """Run a backtest on historical data."""
        self.logger.info("starting_backtest", strategy=strategy_name)

        if len(price_data) < 50:
            return BacktestResult(
                strategy_name=strategy_name,
                period=period,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow(),
                metrics=self._empty_metrics(),
                trades=[],
                equity_curve=[],
                monthly_returns=[],
                errors=["Insufficient data for backtest"],
            )

        # Generate signals
        signals = self._generate_signals(price_data, strategy_params)
        
        # Execute trades
        trades = self._execute_trades(price_data, signals)
        
        # Calculate metrics
        metrics = self._calculate_metrics(trades, price_data)
        
        # Generate equity curve
        equity_curve = self._generate_equity_curve(trades, price_data)
        
        # Calculate monthly returns
        monthly_returns = self._calculate_monthly_returns(equity_curve)

        return BacktestResult(
            strategy_name=strategy_name,
            period=period,
            start_date=price_data[0].timestamp,
            end_date=price_data[-1].timestamp,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns,
        )

    def _generate_signals(
        self, data: List[OHLCV], params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate trading signals based on strategy parameters."""
        signals = []
        strategy_type = params.get("type", "EMA_CROSSOVER")

        if strategy_type == "EMA_CROSSOVER":
            fast_period = params.get("fast_ema", 20)
            slow_period = params.get("slow_ema", 50)
            
            fast_ema = self._calculate_ema(data, fast_period)
            slow_ema = self._calculate_ema(data, slow_period)

            for i in range(slow_period, len(data)):
                if fast_ema[i] > slow_ema[i] and fast_ema[i - 1] <= slow_ema[i - 1]:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "BUY",
                        "price": data[i].close,
                    })
                elif fast_ema[i] < slow_ema[i] and fast_ema[i - 1] >= slow_ema[i - 1]:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "SELL",
                        "price": data[i].close,
                    })

        elif strategy_type == "RSI":
            rsi_period = params.get("rsi_period", 14)
            oversold = params.get("oversold", 30)
            overbought = params.get("overbought", 70)
            
            rsi = self._calculate_rsi(data, rsi_period)

            for i in range(rsi_period, len(data)):
                if rsi[i] < oversold and rsi[i - 1] >= oversold:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "BUY",
                        "price": data[i].close,
                    })
                elif rsi[i] > overbought and rsi[i - 1] <= overbought:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "SELL",
                        "price": data[i].close,
                    })

        elif strategy_type == "VWAP":
            for i in range(20, len(data)):
                vwap = self._calculate_vwap(data[max(0, i - 20):i + 1])
                if data[i].close > vwap and data[i - 1].close <= vwap:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "BUY",
                        "price": data[i].close,
                    })
                elif data[i].close < vwap and data[i - 1].close >= vwap:
                    signals.append({
                        "index": i,
                        "timestamp": data[i].timestamp,
                        "action": "SELL",
                        "price": data[i].close,
                    })

        return signals

    def _calculate_ema(self, data: List[OHLCV], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        ema = [data[0].close]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(data)):
            ema.append((data[i].close - ema[-1]) * multiplier + ema[-1])
        
        return ema

    def _calculate_rsi(self, data: List[OHLCV], period: int) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(data) < period + 1:
            return [50.0] * len(data)
        
        rsi = [50.0] * period
        gains = []
        losses = []
        
        for i in range(1, len(data)):
            change = data[i].close - data[i - 1].close
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(data)):
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
            
            if i < len(data) - 1:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return rsi

    def _calculate_vwap(self, data: List[OHLCV]) -> float:
        """Calculate VWAP."""
        if not data:
            return 0
        cumulative_tpv = sum(d.close * d.volume for d in data)
        cumulative_volume = sum(d.volume for d in data)
        return cumulative_tpv / cumulative_volume if cumulative_volume > 0 else 0

    def _execute_trades(
        self, data: List[OHLCV], signals: List[Dict[str, Any]]
    ) -> List[BacktestTrade]:
        """Execute trades based on signals."""
        trades = []
        position = None

        for signal in signals:
            idx = signal["index"]
            action = signal["action"]
            price = signal["price"]
            timestamp = signal["timestamp"]

            if action == "BUY" and position is None:
                position = {
                    "entry_date": timestamp,
                    "entry_price": price,
                    "index": idx,
                    "direction": "long",
                }
            elif action == "SELL" and position is None:
                position = {
                    "entry_date": timestamp,
                    "entry_price": price,
                    "index": idx,
                    "direction": "short",
                }
            elif action == "SELL" and position["direction"] == "long":
                exit_price = price
                pnl = (exit_price - position["entry_price"]) * 100  # Assuming 100 qty
                pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                
                trades.append(BacktestTrade(
                    entry_date=position["entry_date"],
                    exit_date=timestamp,
                    symbol=data[0].timestamp.strftime("%Y%m%d"),
                    direction="long",
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    quantity=100,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    holding_period=idx - position["index"],
                    exit_reason="signal",
                ))
                position = None
            elif action == "BUY" and position["direction"] == "short":
                exit_price = price
                pnl = (position["entry_price"] - exit_price) * 100
                pnl_pct = (position["entry_price"] - exit_price) / position["entry_price"] * 100
                
                trades.append(BacktestTrade(
                    entry_date=position["entry_date"],
                    exit_date=timestamp,
                    symbol=data[0].timestamp.strftime("%Y%m%d"),
                    direction="short",
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    quantity=100,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    holding_period=idx - position["index"],
                    exit_reason="signal",
                ))
                position = None

        return trades

    def _calculate_metrics(self, trades: List[BacktestTrade], data: List[OHLCV]) -> BacktestMetrics:
        """Calculate backtest performance metrics."""
        if not trades:
            return self._empty_metrics()

        total = len(trades)
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_count = len(wins)
        loss_count = len(losses)

        total_pnl = sum(t.pnl for t in trades)
        total_win = sum(t.pnl for t in wins) if wins else 0
        total_loss = abs(sum(t.pnl for t in losses)) if losses else 0

        avg_win = total_win / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0

        win_rate = (win_count / total * 100) if total > 0 else 0
        profit_factor = total_win / total_loss if total_loss > 0 else 0

        # Calculate returns
        returns = [t.pnl_percent / 100 for t in trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        
        # Sharpe ratio (simplified)
        if returns:
            std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            sharpe = (avg_return / std_dev * math.sqrt(252)) if std_dev > 0 else 0
        else:
            sharpe = 0

        # Drawdown
        cumulative = 0
        peak = self.initial_capital
        max_dd = 0
        max_dd_pct = 0

        for trade in trades:
            cumulative += trade.pnl
            equity = self.initial_capital + cumulative
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        # Annualized return
        if len(data) > 1:
            days = (data[-1].timestamp - data[0].timestamp).days
            years = max(days / 365, 0.01)
            annualized = ((1 + total_pnl / self.initial_capital) ** (1 / years) - 1) * 100
        else:
            annualized = 0

        avg_duration = sum(t.holding_period for t in trades) / total if total > 0 else 0
        recovery = total_pnl / max_dd if max_dd > 0 else 0
        calmar = annualized / max_dd_pct if max_dd_pct > 0 else 0

        return BacktestMetrics(
            total_trades=total,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=round(win_rate, 2),
            average_win=round(avg_win, 2),
            average_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sharpe * 1.2, 2),  # Simplified
            max_drawdown=round(max_dd, 2),
            max_drawdown_percent=round(max_dd_pct, 2),
            max_drawdown_duration=0,
            total_return=round(total_pnl, 2),
            annualized_return=round(annualized, 2),
            avg_trade_duration=round(avg_duration, 1),
            recovery_factor=round(recovery, 2),
            calmar_ratio=round(calmar, 2),
        )

    def _empty_metrics(self) -> BacktestMetrics:
        """Return empty metrics structure."""
        return BacktestMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, average_win=0, average_loss=0,
            profit_factor=0, sharpe_ratio=0, sortino_ratio=0,
            max_drawdown=0, max_drawdown_percent=0, max_drawdown_duration=0,
            total_return=0, annualized_return=0, avg_trade_duration=0,
            recovery_factor=0, calmar_ratio=0,
        )

    def _generate_equity_curve(self, trades: List[BacktestTrade], data: List[OHLCV]) -> List[Dict[str, Any]]:
        """Generate equity curve data."""
        curve = []
        equity = self.initial_capital
        
        for trade in trades:
            equity += trade.pnl
            curve.append({
                "date": trade.exit_date,
                "equity": round(equity, 2),
                "drawdown": round((equity - self.initial_capital) / self.initial_capital * 100, 2),
            })
        
        return curve

    def _calculate_monthly_returns(self, equity_curve: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate monthly returns."""
        if not equity_curve:
            return []
        
        monthly = {}
        for point in equity_curve:
            month_key = point["date"].strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = {"equity_start": point["equity"], "equity_end": point["equity"]}
            else:
                monthly[month_key]["equity_end"] = point["equity"]
        
        returns = []
        for month, values in sorted(monthly.items()):
            ret = (values["equity_end"] - values["equity_start"]) / values["equity_start"] * 100 if values["equity_start"] > 0 else 0
            returns.append({
                "month": month,
                "return": round(ret, 2),
            })
        
        return returns


# Singleton instance
backtesting_engine = BacktestingEngine()
