"""Average Directional Index (ADX) calculations."""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from .atr import calculate_atr


@dataclass
class ADXData:
    """ADX indicator data."""

    adx: float
    plus_di: float
    minus_di: float
    trend_strength: str  # "very_weak", "weak", "moderate", "strong", "very_strong"
    trend_direction: str  # "up", "down", "neutral"


def calculate_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[ADXData]]:
    """
    Calculate Average Directional Index (ADX) with +DI and -DI.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ADX period (default: 14)

    Returns:
        List of ADXData
    """
    if len(highs) < period + 1:
        return [None] * len(highs)

    # Calculate True Range
    tr = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(highs)):
        # True Range
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))

        # Directional Movement
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
            minus_dm.append(0)
        elif down_move > up_move and down_move > 0:
            plus_dm.append(0)
            minus_dm.append(down_move)
        else:
            plus_dm.append(0)
            minus_dm.append(0)

    # Calculate smoothed values using Wilder's method
    atr = calculate_atr(highs, lows, closes, period)
    smoothed_tr = []
    smoothed_plus_dm = []
    smoothed_minus_dm = []

    for i in range(period, len(tr)):
        if i == period:
            smoothed_tr.append(sum(tr[:period]))
            smoothed_plus_dm.append(sum(plus_dm[:period]))
            smoothed_minus_dm.append(sum(minus_dm[:period]))
        else:
            smoothed_tr.append(smoothed_tr[-1] - smoothed_tr[-1] / period + tr[i])
            smoothed_plus_dm.append(
                smoothed_plus_dm[-1] - smoothed_plus_dm[-1] / period + plus_dm[i]
            )
            smoothed_minus_dm.append(
                smoothed_minus_dm[-1] - smoothed_minus_dm[-1] / period + minus_dm[i]
            )

    # Calculate DI
    plus_di = []
    minus_di = []
    dx = []
    adx = []

    start_idx = period

    for i in range(len(smoothed_tr)):
        if smoothed_tr[i] == 0:
            plus_di.append(0)
            minus_di.append(0)
        else:
            plus_di.append((smoothed_plus_dm[i] / smoothed_tr[i]) * 100)
            minus_di.append((smoothed_minus_dm[i] / smoothed_tr[i]) * 100)

        di_sum = plus_di[-1] + minus_di[-1]
        if di_sum == 0:
            dx.append(0)
        else:
            dx.append(abs(plus_di[-1] - minus_di[-1]) / di_sum * 100)

    # Smooth DX to get ADX
    adx_value = sum(dx[:period]) / period
    adx.append(adx_value)

    for i in range(period, len(dx)):
        adx_value = (adx[-1] * (period - 1) + dx[i]) / period
        adx.append(adx_value)

    # Build result (prepend None values)
    result = [None] * start_idx

    for i in range(len(adx)):
        idx = start_idx + i
        if idx >= len(highs):
            break

        adx_val = adx[i]
        plus_val = plus_di[i] if i < len(plus_di) else 0
        minus_val = minus_di[i] if i < len(minus_di) else 0

        # Trend strength
        if adx_val < 20:
            strength = "very_weak"
        elif adx_val < 40:
            strength = "weak"
        elif adx_val < 60:
            strength = "moderate"
        elif adx_val < 80:
            strength = "strong"
        else:
            strength = "very_strong"

        # Trend direction
        if plus_val > minus_val:
            direction = "up"
        elif minus_val > plus_val:
            direction = "down"
        else:
            direction = "neutral"

        result.append(
            ADXData(
                adx=round(adx_val, 2),
                plus_di=round(plus_val, 2),
                minus_di=round(minus_val, 2),
                trend_strength=strength,
                trend_direction=direction,
            )
        )

    return result


def get_adx_signal(adx_data: List[Optional[ADXData]]) -> str:
    """
    Get current ADX signal.
    """
    if not adx_data or adx_data[-1] is None:
        return "no_trend"

    current = adx_data[-1]

    if current.adx < 20:
        return "no_trend"
    elif current.adx >= 20 and current.trend_direction == "up":
        return "trending_up"
    elif current.adx >= 20 and current.trend_direction == "down":
        return "trending_down"
    else:
        return "weak_trend"
