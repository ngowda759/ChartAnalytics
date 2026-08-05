"""Volume Weighted Average Price (VWAP) calculations."""

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class VWAPLevel:
    """VWAP with standard deviation levels."""

    value: float
    upper_band_1: float
    upper_band_2: float
    lower_band_1: float
    lower_band_2: float


def calculate_vwap(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[int],
) -> List[Optional[float]]:
    """
    Calculate Volume Weighted Average Price.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        volumes: List of volumes

    Returns:
        List of VWAP values
    """
    if len(highs) != len(lows) != len(closes) != len(volumes):
        raise ValueError("All input lists must have the same length")

    if len(highs) == 0:
        return []

    vwap = [None] * len(highs)
    cumulative_tpv = 0.0
    cumulative_volume = 0

    for i in range(len(highs)):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3
        tpv = typical_price * volumes[i]

        cumulative_tpv += tpv
        cumulative_volume += volumes[i]

        if cumulative_volume > 0:
            vwap[i] = cumulative_tpv / cumulative_volume

    return vwap


def calculate_vwap_with_bands(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[int],
    std_period: int = 20,
) -> List[Optional[VWAPLevel]]:
    """
    Calculate VWAP with standard deviation bands.
    """
    vwap = calculate_vwap(highs, lows, closes, volumes)

    if len(vwap) < std_period:
        return [None] * len(vwap)

    result = [None] * (std_period - 1)

    for i in range(std_period - 1, len(vwap)):
        if vwap[i] is None:
            result.append(None)
            continue

        # Calculate rolling standard deviation of VWAP
        vwap_slice = [v for v in vwap[i - std_period + 1 : i + 1] if v is not None]
        if len(vwap_slice) < std_period:
            result.append(None)
            continue

        mean = sum(vwap_slice) / len(vwap_slice)
        variance = sum((v - mean) ** 2 for v in vwap_slice) / len(vwap_slice)
        std = variance**0.5

        result.append(
            VWAPLevel(
                value=vwap[i],
                upper_band_1=vwap[i] + std,
                upper_band_2=vwap[i] + 2 * std,
                lower_band_1=vwap[i] - std,
                lower_band_2=vwap[i] - 2 * std,
            )
        )

    return result


def detect_vwap_cross(
    prices: List[float],
    vwap_values: List[Optional[float]],
) -> List[str]:
    """
    Detect when price crosses VWAP.

    Returns:
        List of signals: "above", "below", "cross_up", "cross_down"
    """
    signals = []

    for i in range(len(prices)):
        if vwap_values[i] is None:
            signals.append("neutral")
            continue

        if i == 0:
            signals.append("above" if prices[i] > vwap_values[i] else "below")
            continue

        prev_price = prices[i - 1]
        prev_vwap = vwap_values[i - 1] or vwap_values[i]

        if prices[i] > vwap_values[i] and prev_price <= prev_vwap:
            signals.append("cross_up")
        elif prices[i] < vwap_values[i] and prev_price >= prev_vwap:
            signals.append("cross_down")
        elif prices[i] > vwap_values[i]:
            signals.append("above")
        else:
            signals.append("below")

    return signals
