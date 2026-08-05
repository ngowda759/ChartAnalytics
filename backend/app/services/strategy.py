"""Strategy Builder Service - Create and manage trading strategies."""
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


class StrategyType(str, Enum):
    ORB = "ORB"  # Opening Range Breakout
    VWAP = "VWAP"
    EMA_CROSSOVER = "EMA_CROSSOVER"
    MOMENTUM = "MOMENTUM"
    SCALPING = "SCALPING"
    OPTION_BUYING = "OPTION_BUYING"
    OPTION_SELLING = "OPTION_SELLING"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"
    CUSTOM = "CUSTOM"


class ConditionType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    EMA_CROSS_ABOVE = "ema_cross_above"
    EMA_CROSS_BELOW = "ema_cross_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    VOLUME_ABOVE = "volume_above"
    VWAP_ABOVE = "vwap_above"
    VWAP_BELOW = "vwap_below"
    ATR_PERCENT = "atr_percent"
    PRICE_RANGE = "price_range"


@dataclass
class StrategyCondition:
    type: ConditionType
    indicator: Optional[str] = None
    value: float = 0
    value2: Optional[float] = None  # For range conditions
    operator: str = "AND"


@dataclass
class StrategyRule:
    id: str
    name: str
    conditions: List[StrategyCondition]
    action: str  # "entry_long", "entry_short", "exit", "alert"


@dataclass
class Strategy:
    id: str
    name: str
    type: StrategyType
    description: str
    rules: List[StrategyRule]
    parameters: Dict[str, Any]
    risk_per_trade: float = 2.0  # Percentage
    max_positions: int = 3
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StrategySignal:
    strategy_id: str
    strategy_name: str
    action: str
    symbol: str
    price: float
    confidence: float
    reason: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyBuilder:
    """Service for building and managing trading strategies."""

    def __init__(self):
        self.logger = structlog.get_logger()
        self._strategies: Dict[str, Strategy] = {}

    def create_strategy(
        self,
        name: str,
        strategy_type: StrategyType,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Strategy:
        """Create a new trading strategy."""
        strategy_id = f"strat_{name.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}"
        
        rules = self._get_default_rules(strategy_type, parameters or {})
        
        strategy = Strategy(
            id=strategy_id,
            name=name,
            type=strategy_type,
            description=description,
            rules=rules,
            parameters=parameters or self._get_default_parameters(strategy_type),
        )
        
        self._strategies[strategy_id] = strategy
        self.logger.info("strategy_created", strategy_id=strategy_id, name=name)
        return strategy

    def _get_default_parameters(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """Get default parameters for a strategy type."""
        defaults = {
            StrategyType.ORB: {
                "range_minutes": 15,
                "breakout_percentage": 0.5,
                "stop_loss_percentage": 0.5,
            },
            StrategyType.VWAP: {
                "vwap_deviation": 1.0,
                "confirmation_bars": 2,
            },
            StrategyType.EMA_CROSSOVER: {
                "fast_ema": 20,
                "slow_ema": 50,
                "signal_ema": 9,
            },
            StrategyType.MOMENTUM: {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
            },
            StrategyType.SCALPING: {
                "target_points": 10,
                "stop_loss_points": 5,
                "timeframe": "1min",
            },
            StrategyType.OPTION_BUYING: {
                "strike_offset": 1,
                "expiry_days_max": 7,
                "iv_minimum": 20,
            },
            StrategyType.OPTION_SELLING: {
                "strike_offset": 2,
                "expiry_days_min": 7,
                "iv_minimum": 25,
            },
        }
        return defaults.get(strategy_type, {})

    def _get_default_rules(self, strategy_type: StrategyType, parameters: Dict[str, Any]) -> List[StrategyRule]:
        """Get default rules for a strategy type."""
        rules = []
        
        if strategy_type == StrategyType.ORB:
            rules.append(StrategyRule(
                id="orb_entry",
                name="ORB Entry",
                conditions=[
                    StrategyCondition(
                        type=ConditionType.PRICE_RANGE,
                        value=parameters.get("breakout_percentage", 0.5),
                        value2=parameters.get("range_minutes", 15),
                    )
                ],
                action="entry_long",
            ))
        
        elif strategy_type == StrategyType.VWAP:
            rules.append(StrategyRule(
                id="vwap_long",
                name="VWAP Long",
                conditions=[
                    StrategyCondition(type=ConditionType.VWAP_ABOVE, value=0),
                ],
                action="entry_long",
            ))
            rules.append(StrategyRule(
                id="vwap_short",
                name="VWAP Short",
                conditions=[
                    StrategyCondition(type=ConditionType.VWAP_BELOW, value=0),
                ],
                action="entry_short",
            ))
        
        elif strategy_type == StrategyType.EMA_CROSSOVER:
            fast_ema = parameters.get("fast_ema", 20)
            slow_ema = parameters.get("slow_ema", 50)
            rules.append(StrategyRule(
                id="ema_bullish_cross",
                name="Bullish EMA Cross",
                conditions=[
                    StrategyCondition(
                        type=ConditionType.EMA_CROSS_ABOVE,
                        indicator=f"EMA_{fast_ema}",
                        value=float(fast_ema),
                    ),
                ],
                action="entry_long",
            ))
            rules.append(StrategyRule(
                id="ema_bearish_cross",
                name="Bearish EMA Cross",
                conditions=[
                    StrategyCondition(
                        type=ConditionType.EMA_CROSS_BELOW,
                        indicator=f"EMA_{fast_ema}",
                        value=float(fast_ema),
                    ),
                ],
                action="entry_short",
            ))
        
        elif strategy_type == StrategyType.MOMENTUM:
            rules.append(StrategyRule(
                id="momentum_long",
                name="Momentum Long",
                conditions=[
                    StrategyCondition(
                        type=ConditionType.RSI_BELOW,
                        indicator="RSI",
                        value=parameters.get("rsi_oversold", 30),
                    ),
                ],
                action="entry_long",
            ))
            rules.append(StrategyRule(
                id="momentum_short",
                name="Momentum Short",
                conditions=[
                    StrategyCondition(
                        type=ConditionType.RSI_ABOVE,
                        indicator="RSI",
                        value=parameters.get("rsi_overbought", 70),
                    ),
                ],
                action="entry_short",
            ))
        
        return rules

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Strategy]:
        """List all strategies."""
        return list(self._strategies.values())

    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> Optional[Strategy]:
        """Update a strategy."""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None
        
        if "name" in updates:
            strategy.name = updates["name"]
        if "description" in updates:
            strategy.description = updates["description"]
        if "parameters" in updates:
            strategy.parameters.update(updates["parameters"])
        if "is_active" in updates:
            strategy.is_active = updates["is_active"]
        if "risk_per_trade" in updates:
            strategy.risk_per_trade = updates["risk_per_trade"]
        if "max_positions" in updates:
            strategy.max_positions = updates["max_positions"]
        
        strategy.updated_at = datetime.utcnow()
        self.logger.info("strategy_updated", strategy_id=strategy_id)
        return strategy

    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy."""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            self.logger.info("strategy_deleted", strategy_id=strategy_id)
            return True
        return False

    def evaluate_strategy(
        self,
        strategy: Strategy,
        market_data: Dict[str, Any],
    ) -> List[StrategySignal]:
        """Evaluate a strategy against current market data."""
        signals = []
        
        for rule in strategy.rules:
            if self._evaluate_rule(rule, market_data):
                signal = StrategySignal(
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    action=rule.action,
                    symbol=market_data.get("symbol", "UNKNOWN"),
                    price=market_data.get("price", 0),
                    confidence=0.8,
                    reason=f"Strategy rule '{rule.name}' triggered",
                    timestamp=datetime.utcnow(),
                    metadata={"rule_id": rule.id},
                )
                signals.append(signal)
        
        return signals

    def _evaluate_rule(self, rule: StrategyRule, market_data: Dict[str, Any]) -> bool:
        """Evaluate if a rule's conditions are met."""
        if not rule.conditions:
            return False
        
        results = []
        for condition in rule.conditions:
            result = self._evaluate_condition(condition, market_data)
            results.append(result)
        
        if rule.conditions[0].operator == "AND":
            return all(results)
        else:
            return any(results)

    def _evaluate_condition(self, condition: StrategyCondition, market_data: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        price = market_data.get("price", 0)
        
        if condition.type == ConditionType.PRICE_ABOVE:
            return price > condition.value
        elif condition.type == ConditionType.PRICE_BELOW:
            return price < condition.value
        elif condition.type == ConditionType.VWAP_ABOVE:
            vwap = market_data.get("vwap", 0)
            return vwap > 0 and price > vwap
        elif condition.type == ConditionType.VWAP_BELOW:
            vwap = market_data.get("vwap", 0)
            return vwap > 0 and price < vwap
        elif condition.type == ConditionType.RSI_ABOVE:
            rsi = market_data.get("rsi", 50)
            return rsi > condition.value
        elif condition.type == ConditionType.RSI_BELOW:
            rsi = market_data.get("rsi", 50)
            return rsi < condition.value
        
        return False


# Singleton instance
strategy_builder = StrategyBuilder()
