"""Volume analysis calculations."""
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class VolumeProfile:
    """Volume profile data."""
    price_level: float
    volume: int
    percent_of_total: float
    cumulative_percent: float


@dataclass
class VolumeSpike:
    """Volume spike detection."""
    timestamp_index: int
    volume: int
    average_volume: float
    spike_ratio: float
    spike_type: str  # "normal", "spike_up", "spike_down", "collapse"


def calculate_volume_profile(
    closes: List[float],
    volumes: List[int],
    bins: int = 20,
) -> List[VolumeProfile]:
    """
    Calculate Volume Profile (TPO - Time Price Opportunity).
    
    Args:
        closes: List of closing prices
        volumes: List of volumes
        bins: Number of price bins (default: 20)
    
    Returns:
        List of VolumeProfile sorted by price level
    """
    if len(closes) != len(volumes) or len(closes) == 0:
        return []
    
    # Find price range
    min_price = min(closes)
    max_price = max(closes)
    price_range = max_price - min_price
    
    if price_range == 0:
        return []
    
    # Create bins
    bin_size = price_range / bins
    bin_volumes = [0] * bins
    bin_prices = [min_price + (i + 0.5) * bin_size for i in range(bins)]
    
    # Distribute volume into bins
    for close, volume in zip(closes, volumes):
        bin_index = min(int((close - min_price) / bin_size), bins - 1)
        bin_volumes[bin_index] += volume
    
    # Calculate total volume
    total_volume = sum(bin_volumes)
    
    # Build profile
    cumulative = 0
    profile = []
    
    for i in range(bins):
        cumulative += bin_volumes[i]
        profile.append(VolumeProfile(
            price_level=round(bin_prices[i], 2),
            volume=bin_volumes[i],
            percent_of_total=round((bin_volumes[i] / total_volume) * 100, 2) if total_volume > 0 else 0,
            cumulative_percent=round((cumulative / total_volume) * 100, 2) if total_volume > 0 else 0,
        ))
    
    return profile


def detect_volume_spike(
    volumes: List[int],
    period: int = 20,
    threshold: float = 2.0,
) -> List[Optional[VolumeSpike]]:
    """
    Detect volume spikes using standard deviation.
    
    Args:
        volumes: List of volumes
        period: Lookback period for average (default: 20)
        threshold: Number of standard deviations for spike (default: 2.0)
    
    Returns:
        List of VolumeSpike or None
    """
    if len(volumes) < period:
        return [None] * len(volumes)
    
    result = [None] * (period - 1)
    
    for i in range(period - 1, len(volumes)):
        # Calculate average and std
        window = volumes[i - period + 1:i]
        avg_volume = sum(window) / len(window)
        
        variance = sum((v - avg_volume) ** 2 for v in window) / len(window)
        std = variance ** 0.5
        
        current_vol = volumes[i]
        current_avg = avg_volume
        
        if std == 0:
            spike_ratio = 1.0
        else:
            spike_ratio = current_vol / avg_volume
        
        # Determine spike type
        if spike_ratio >= threshold:
            spike_type = "spike_up"
        elif spike_ratio <= 1 / threshold:
            spike_type = "spike_down"
        elif spike_ratio < 0.5:
            spike_type = "collapse"
        else:
            spike_type = "normal"
        
        result.append(VolumeSpike(
            timestamp_index=i,
            volume=current_vol,
            average_volume=round(avg_volume, 0),
            spike_ratio=round(spike_ratio, 2),
            spike_type=spike_type,
        ))
    
    return result


def calculate_on_balance_volume(
    closes: List[float],
    volumes: List[int],
) -> List[int]:
    """
    Calculate On-Balance Volume (OBV).
    """
    if len(closes) != len(volumes) or len(closes) == 0:
        return []
    
    obv = [volumes[0]]
    
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    
    return obv


def calculate_vwap_volume(
    volumes: List[int],
    typical_prices: List[float],
) -> List[float]:
    """
    Calculate volume-weighted average price for each bar.
    """
    if len(volumes) != len(typical_prices) or len(volumes) == 0:
        return []
    
    cumulative_tpv = 0
    cumulative_volume = 0
    vwap = []
    
    for volume, tp in zip(volumes, typical_prices):
        cumulative_tpv += volume * tp
        cumulative_volume += volume
        vwap.append(cumulative_tpv / cumulative_volume if cumulative_volume > 0 else 0)
    
    return vwap


def calculate_volume_weight(
    volumes: List[int],
    lookback: int = 20,
) -> List[Optional[float]]:
    """
    Calculate volume weight (% of average).
    """
    if len(volumes) < lookback:
        return [None] * len(volumes)
    
    result = [None] * (lookback - 1)
    
    for i in range(lookback - 1, len(volumes)):
        avg_volume = sum(volumes[i - lookback + 1:i]) / (lookback - 1)
        weight = (volumes[i] / avg_volume) * 100 if avg_volume > 0 else 100
        result.append(round(weight, 2))
    
    return result


def detect_volume_divergence(
    prices: List[float],
    volumes: List[int],
    lookback: int = 20,
) -> List[Optional[str]]:
    """
    Detect price-volume divergence.
    """
    if len(prices) < lookback or len(volumes) < lookback:
        return [None] * len(prices)
    
    result = [None] * (lookback - 1)
    
    for i in range(lookback - 1, len(prices)):
        price_trend = prices[i] - prices[i - lookback]
        vol_trend = sum(volumes[i - lookback + 1:i + 1]) / lookback - \
                    sum(volumes[i - 2 * lookback + 1:i - lookback + 1]) / lookback
        
        if price_trend > 0 and vol_trend < 0:
            result.append("bearish_divergence")
        elif price_trend < 0 and vol_trend > 0:
            result.append("bullish_divergence")
        elif price_trend > 0 and vol_trend > 0:
            result.append("confirmed_up")
        elif price_trend < 0 and vol_trend < 0:
            result.append("confirmed_down")
        else:
            result.append(None)
    
    return result
