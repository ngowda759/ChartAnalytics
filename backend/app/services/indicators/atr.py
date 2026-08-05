"""Average True Range (ATR) calculations."""
from typing import List, Optional


def calculate_true_range(
    highs: List[float],
    lows: List[float],
    closes: List[float],
) -> List[Optional[float]]:
    """
    Calculate True Range.
    """
    if len(highs) < 2:
        return [0.0] * len(highs)
    
    tr = [abs(highs[0] - lows[0])]
    
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))
    
    return tr


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Calculate Average True Range using Wilder's smoothing.
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default: 14)
    
    Returns:
        List of ATR values
    """
    if len(highs) < period:
        return [None] * len(highs)
    
    tr = calculate_true_range(highs, lows, closes)
    
    # First ATR is simple average
    atr = [None] * (period - 1)
    first_atr = sum(tr[:period]) / period
    atr.append(first_atr)
    
    # Subsequent values using Wilder's smoothing
    for i in range(period, len(tr)):
        current_atr = (atr[-1] * (period - 1) + tr[i]) / period
        atr.append(current_atr)
    
    return atr


def calculate_normalized_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Calculate Normalized ATR (ATR as percentage of price).
    """
    atr = calculate_atr(highs, lows, closes, period)
    natr = []
    
    for i in range(len(atr)):
        if atr[i] is None or closes[i] == 0:
            natr.append(None)
        else:
            natr.append((atr[i] / closes[i]) * 100)
    
    return natr


def calculate_wilders_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Calculate ATR using Wilders smoothing (same as standard ATR).
    """
    return calculate_atr(highs, lows, closes, period)
