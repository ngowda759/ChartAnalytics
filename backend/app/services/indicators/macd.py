"""MACD (Moving Average Convergence Divergence) calculations."""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from .ema import calculate_ema


@dataclass
class MACDData:
    """MACD indicator data."""

    macd: float
    signal: float
    histogram: float
    crossover: str  # "bullish", "bearish", "neutral"


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Calculate MACD line, signal line, and histogram.

    Args:
        prices: List of closing prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    # MACD Line = Fast EMA - Slow EMA
    macd_line = []
    for fast, slow in zip(fast_ema, slow_ema):
        if fast is None or slow is None:
            macd_line.append(None)
        else:
            macd_line.append(fast - slow)

    # Signal Line = 9-period EMA of MACD Line
    signal_line = calculate_ema([m if m is not None else 0 for m in macd_line], 9)

    # Histogram = MACD Line - Signal Line
    histogram = []
    for macd_val, signal_val in zip(macd_line, signal_line):
        if macd_val is None or signal_val is None:
            histogram.append(None)
        else:
            histogram.append(macd_val - signal_val)

    return macd_line, signal_line, histogram


def calculate_signal_line(
    macd_line: List[Optional[float]], period: int = 9
) -> List[Optional[float]]:
    """
    Calculate signal line (EMA of MACD).
    """
    return calculate_ema([m if m is not None else 0 for m in macd_line], period)


def detect_macd_crossover(
    macd_line: List[Optional[float]],
    signal_line: List[Optional[float]],
) -> List[MACDData]:
    """
    Detect MACD crossovers and generate signals.
    """
    signals = []

    for i in range(len(macd_line)):
        if macd_line[i] is None or signal_line[i] is None:
            signals.append(
                MACDData(
                    macd=0,
                    signal=0,
                    histogram=0,
                    crossover="neutral",
                )
            )
            continue

        histogram = macd_line[i] - signal_line[i]

        if i == 0:
            crossover = "neutral"
        else:
            prev_macd = macd_line[i - 1] or 0
            prev_signal = signal_line[i - 1] or 0
            prev_hist = prev_macd - prev_signal

            if histogram > 0 and prev_hist <= 0:
                crossover = "bullish"
            elif histogram < 0 and prev_hist >= 0:
                crossover = "bearish"
            else:
                crossover = "neutral"

        signals.append(
            MACDData(
                macd=round(macd_line[i], 4),
                signal=round(signal_line[i], 4),
                histogram=round(histogram, 4),
                crossover=crossover,
            )
        )

    return signals


def calculate_macd_histogram_rate(
    histogram: List[Optional[float]],
) -> List[Optional[float]]:
    """
    Calculate rate of change of MACD histogram.
    Useful for momentum analysis.
    """
    if len(histogram) < 2:
        return [None] * len(histogram)

    rates = [None]

    for i in range(1, len(histogram)):
        if histogram[i] is None or histogram[i - 1] is None:
            rates.append(None)
            continue

        if histogram[i - 1] == 0:
            rates.append(None)
        else:
            rate = ((histogram[i] - histogram[i - 1]) / abs(histogram[i - 1])) * 100
            rates.append(round(rate, 2))

    return rates
