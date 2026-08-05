"""Exponential Moving Average (EMA) calculations."""
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EMACrossover:
    """EMA crossover signal."""
    fast_ema: float
    slow_ema: float
    crossover_type: str  # "bullish", "bearish", "neutral"
    strength: float  # 0-100


def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: List of closing prices
        period: EMA period (e.g., 20, 50, 200)
    
    Returns:
        List of EMA values (first `period-1` values will be None)
    """
    if len(prices) < period:
        return [None] * len(prices)
    
    ema = [None] * (period - 1)
    
    # First EMA is SMA
    sma = sum(prices[:period]) / period
    ema.append(sma)
    
    # Multiplier
    multiplier = 2 / (period + 1)
    
    # Calculate remaining EMAs
    for i in range(period, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    
    return ema


def calculate_double_ema(prices: List[float], fast: int = 12, slow: int = 26) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """
    Calculate dual EMAs for crossover analysis.
    
    Args:
        prices: List of closing prices
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
    
    Returns:
        Tuple of (fast_ema, slow_ema)
    """
    return calculate_ema(prices, fast), calculate_ema(prices, slow)


def calculate_triple_ema(prices: List[float]) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Calculate triple EMAs (20, 50, 200) for trend analysis.
    
    Returns:
        Tuple of (ema_20, ema_50, ema_200)
    """
    return calculate_ema(prices, 20), calculate_ema(prices, 50), calculate_ema(prices, 200)


def detect_ema_crossover(
    fast_ema: List[Optional[float]],
    slow_ema: List[Optional[float]],
    threshold: float = 0.001,
) -> List[EMACrossover]:
    """
    Detect EMA crossovers from EMA lists.
    """
    signals = []
    
    for i in range(1, len(fast_ema)):
        if fast_ema[i] is None or slow_ema[i] is None:
            signals.append(EMACrossover(
                fast_ema=0,
                slow_ema=0,
                crossover_type="neutral",
                strength=0,
            ))
            continue
        
        prev_fast = fast_ema[i - 1] or 0
        prev_slow = slow_ema[i - 1] or 0
        
        current_diff = fast_ema[i] - slow_ema[i]
        prev_diff = prev_fast - prev_slow
        
        if prev_diff <= 0 and current_diff > threshold * slow_ema[i]:
            strength = min(100, abs(current_diff / slow_ema[i]) * 1000)
            signals.append(EMACrossover(
                fast_ema=fast_ema[i],
                slow_ema=slow_ema[i],
                crossover_type="bullish",
                strength=strength,
            ))
        elif prev_diff >= 0 and current_diff < -threshold * slow_ema[i]:
            strength = min(100, abs(current_diff / slow_ema[i]) * 1000)
            signals.append(EMACrossover(
                fast_ema=fast_ema[i],
                slow_ema=slow_ema[i],
                crossover_type="bearish",
                strength=strength,
            ))
        else:
            signals.append(EMACrossover(
                fast_ema=fast_ema[i],
                slow_ema=slow_ema[i],
                crossover_type="neutral",
                strength=0,
            ))
    
    return signals


def get_trend_direction(ema_20: Optional[float], ema_50: Optional[float], ema_200: Optional[float], price: float) -> str:
    """
    Determine trend direction based on EMA structure.
    """
    if None in [ema_20, ema_50, ema_200]:
        return "unknown"
    
    if price > ema_20 > ema_50 > ema_200:
        return "strong_uptrend"
    elif price > ema_20 and price > ema_50 and ema_50 > ema_200:
        return "uptrend"
    elif price < ema_20 < ema_50 < ema_200:
        return "strong_downtrend"
    elif price < ema_20 and price < ema_50 and ema_50 < ema_200:
        return "downtrend"
    else:
        return "ranging"
