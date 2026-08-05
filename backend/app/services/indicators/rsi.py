"""Relative Strength Index (RSI) calculations."""
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RSISignal:
    """RSI value with signal interpretation."""
    value: float
    signal: str  # "oversold", "overbought", "neutral"
    strength: float  # How extreme the reading is (0-100)


def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Calculate Relative Strength Index using Wilder's smoothing method.
    
    Args:
        prices: List of closing prices
        period: RSI period (default: 14)
    
    Returns:
        List of RSI values
    """
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    # Calculate price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    # Separate gains and losses
    gains = [max(0, c) for c in changes]
    losses = [max(0, -c) for c in changes]
    
    # First average (simple)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi = [None] * (period + 1)
    
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100 - (100 / (1 + rs)))
    
    # Subsequent values using Wilder's smoothing
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    
    # Prepend None values for alignment
    return [None] + rsi


def interpret_rsi(rsi_value: float, oversold: float = 30, overbought: float = 70) -> RSISignal:
    """
    Interpret RSI value and generate signal.
    """
    if rsi_value <= oversold:
        # How far into oversold territory
        strength = ((oversold - rsi_value) / oversold) * 100
        return RSISignal(value=rsi_value, signal="oversold", strength=min(100, strength))
    elif rsi_value >= overbought:
        # How far into overbought territory
        strength = ((rsi_value - overbought) / (100 - overbought)) * 100
        return RSISignal(value=rsi_value, signal="overbought", strength=min(100, strength))
    else:
        # Neutral zone
        if rsi_value < 50:
            strength = ((50 - rsi_value) / 50) * 50
        else:
            strength = ((rsi_value - 50) / 50) * 50
        return RSISignal(value=rsi_value, signal="neutral", strength=strength)


def calculate_rsi_divergence(
    prices: List[float],
    rsi_values: List[Optional[float]],
    lookback: int = 20,
) -> List[Optional[str]]:
    """
    Detect RSI divergence from price.
    
    Returns:
        "bullish_divergence", "bearish_divergence", or None
    """
    if len(prices) < lookback or len(rsi_values) < lookback:
        return [None] * len(prices)
    
    signals = [None] * (len(prices) - lookback)
    
    for i in range(lookback, len(prices)):
        # Get recent window
        price_window = prices[i - lookback:i + 1]
        rsi_window = [r for r in rsi_values[i - lookback:i + 1] if r is not None]
        
        if len(rsi_window) < 5:
            signals.append(None)
            continue
        
        # Find local extremes
        price_trend = price_window[-1] - price_window[0]
        rsi_trend = rsi_window[-1] - rsi_window[0]
        
        if price_trend < 0 and rsi_trend > 5:
            signals.append("bullish_divergence")
        elif price_trend > 0 and rsi_trend < -5:
            signals.append("bearish_divergence")
        else:
            signals.append(None)
    
    return signals


def calculate_stochastic_rsi(
    rsi_values: List[Optional[float]],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Calculate Stochastic RSI (%K of RSI).
    """
    if len(rsi_values) < period:
        return [None] * len(rsi_values)
    
    stoch_rsi = [None] * (period - 1)
    
    for i in range(period - 1, len(rsi_values)):
        window = [v for v in rsi_values[i - period + 1:i + 1] if v is not None]
        
        if len(window) < period:
            stoch_rsi.append(None)
            continue
        
        lowest = min(window)
        highest = max(window)
        
        if highest == lowest:
            stoch_rsi.append(50)  # Neutral
        else:
            current_rsi = rsi_values[i]
            if current_rsi is not None:
                stoch_rsi.append(((current_rsi - lowest) / (highest - lowest)) * 100)
            else:
                stoch_rsi.append(None)
    
    return stoch_rsi
