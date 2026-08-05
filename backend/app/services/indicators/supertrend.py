"""Supertrend indicator calculations."""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from .atr import calculate_atr


@dataclass
class SupertrendData:
    """Supertrend indicator data."""

    value: float
    trend: str  # "up", "down"
    reversal: bool
    atr: float


def calculate_supertrend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> List[Optional[SupertrendData]]:
    """
    Calculate Supertrend indicator.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default: 10)
        multiplier: ATR multiplier (default: 3.0)

    Returns:
        List of SupertrendData
    """
    atr_values = calculate_atr(highs, lows, closes, period)

    if len(atr_values) < period:
        return [None] * len(highs)

    # Calculate basic upper/lower bands
    hl2 = [(highs[i] + lows[i]) / 2 for i in range(len(highs))]

    upper_band = [None] * len(hl2)
    lower_band = [None] * len(hl2)
    supertrend = [None] * len(hl2)
    trend = ["unknown"] * len(hl2)

    for i in range(period, len(hl2)):
        if atr_values[i] is None:
            continue

        atr = atr_values[i]
        upper_band[i] = hl2[i] + multiplier * atr
        lower_band[i] = hl2[i] - multiplier * atr

    # Calculate Supertrend
    prev_close = closes[0]
    prev_trend = "down"
    prev_st = hl2[0]

    for i in range(1, len(closes)):
        if upper_band[i] is None:
            supertrend[i] = prev_st
            trend[i] = prev_trend
            continue

        curr_close = closes[i]

        if curr_close > upper_band[i - 1] if upper_band[i - 1] else False:
            curr_trend = "up"
        elif curr_close < lower_band[i - 1] if lower_band[i - 1] else False:
            curr_trend = "down"
        else:
            curr_trend = prev_trend

        if curr_trend == "up":
            curr_st = max(
                lower_band[i], supertrend[i - 1] if supertrend[i - 1] else lower_band[i]
            )
        else:
            curr_st = min(
                upper_band[i], supertrend[i - 1] if supertrend[i - 1] else upper_band[i]
            )

        reversal = (prev_trend == "down" and curr_trend == "up") or (
            prev_trend == "up" and curr_trend == "down"
        )

        supertrend[i] = curr_st
        trend[i] = curr_trend
        prev_trend = curr_trend
        prev_st = curr_st

    # Build result
    result = []
    for i in range(len(highs)):
        if supertrend[i] is None or atr_values[i] is None:
            result.append(None)
        else:
            reversal = False
            if i > 0 and trend[i] != trend[i - 1]:
                reversal = True

            result.append(
                SupertrendData(
                    value=round(supertrend[i], 2),
                    trend=trend[i],
                    reversal=reversal,
                    atr=round(atr_values[i], 2),
                )
            )

    return result


def get_supertrend_signal(supertrend: List[Optional[SupertrendData]]) -> str:
    """
    Get current Supertrend signal.
    """
    if not supertrend or supertrend[-1] is None:
        return "neutral"

    current = supertrend[-1]

    if current.reversal:
        return "reversal_" + current.trend
    else:
        return current.trend
