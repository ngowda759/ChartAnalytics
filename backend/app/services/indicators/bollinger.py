"""Bollinger Bands calculations."""

from typing import List, Optional
from dataclasses import dataclass
import math


@dataclass
class BollingerBands:
    """Bollinger Bands data."""

    upper: float
    middle: float
    lower: float
    bandwidth: float
    percent_b: float


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> List[Optional[BollingerBands]]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: List of closing prices
        period: Moving average period (default: 20)
        std_dev: Standard deviations for bands (default: 2.0)

    Returns:
        List of BollingerBands
    """
    if len(prices) < period:
        return [None] * len(prices)

    result = [None] * (period - 1)

    for i in range(period - 1, len(prices)):
        # Get window
        window = prices[i - period + 1 : i + 1]

        # Calculate SMA (middle band)
        middle = sum(window) / period

        # Calculate standard deviation
        variance = sum((p - middle) ** 2 for p in window) / period
        std = math.sqrt(variance)

        # Calculate bands
        upper = middle + std_dev * std
        lower = middle - std_dev * std

        # Bandwidth: (Upper - Lower) / Middle * 100
        bandwidth = ((upper - lower) / middle) * 100 if middle != 0 else 0

        # %B: (Price - Lower) / (Upper - Lower)
        if upper != lower:
            percent_b = (prices[i] - lower) / (upper - lower)
        else:
            percent_b = 0.5

        result.append(
            BollingerBands(
                upper=round(upper, 2),
                middle=round(middle, 2),
                lower=round(lower, 2),
                bandwidth=round(bandwidth, 2),
                percent_b=round(percent_b, 4),
            )
        )

    return result


def detect_bollinger_squeeze(
    bands: List[Optional[BollingerBands]],
    lookback: int = 20,
) -> List[Optional[str]]:
    """
    Detect Bollinger Band squeezes (low volatility).
    """
    if len(bands) < lookback:
        return [None] * len(bands)

    result = [None] * (lookback - 1)

    for i in range(lookback - 1, len(bands)):
        # Get recent bandwidth values
        recent_bands = [
            b.bandwidth for b in bands[i - lookback + 1 : i + 1] if b is not None
        ]

        if len(recent_bands) < lookback // 2:
            result.append(None)
            continue

        # Calculate average bandwidth
        avg_bandwidth = sum(recent_bands) / len(recent_bands)
        current_bandwidth = bands[i].bandwidth if bands[i] else avg_bandwidth

        # Squeeze: current bandwidth < 50% of average
        if current_bandwidth < avg_bandwidth * 0.5:
            result.append("squeeze")
        elif current_bandwidth > avg_bandwidth * 1.5:
            result.append("expansion")
        else:
            result.append("normal")

    return result


def calculate_bollinger_width(
    bands: List[Optional[BollingerBands]],
) -> List[Optional[float]]:
    """
    Calculate Bollinger Width (bandwidth) as a time series.
    """
    return [b.bandwidth if b else None for b in bands]


def calculate_bollinger_percent_b(
    bands: List[Optional[BollingerBands]],
) -> List[Optional[float]]:
    """
    Calculate %B as a time series.
    """
    return [b.percent_b if b else None for b in bands]
