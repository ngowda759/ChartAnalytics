from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import structlog

from app.schemas.indicators import (
    TechnicalIndicators,
    EMAData,
    MACDData,
    RSIData,
    SupertrendData,
    BollingerBandsData,
    ATRData,
    ADXData,
    VWAPData,
    TrendDirection,
    IndicatorHistoryResponse,
    IndicatorHistory,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{symbol}", response_model=TechnicalIndicators)
async def get_indicators(symbol: str):
    """Get all technical indicators for a symbol"""
    logger.info("calculating_indicators", symbol=symbol)
    
    spot_price = 24567.85 if symbol.upper() == "NIFTY" else 52456.70
    
    # Generate mock indicator values
    price = spot_price * (1 + random.uniform(-0.01, 0.01))
    
    # EMA
    ema20 = price * (1 + random.uniform(-0.005, 0.005))
    ema50 = price * (1 + random.uniform(-0.015, 0.015))
    ema200 = price * (1 + random.uniform(-0.03, 0.03))
    
    ema_trend = "bullish" if price > ema20 > ema50 else "bearish" if price < ema20 < ema50 else "neutral"
    
    # RSI
    rsi_value = random.uniform(30, 70)
    rsi_signal = "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral"
    
    # MACD
    macd_value = random.uniform(-50, 50)
    signal_value = random.uniform(-30, 30)
    histogram = macd_value - signal_value
    macd_crossover = "bullish" if histogram > 0 and random.random() > 0.7 else "bearish" if histogram < 0 and random.random() > 0.7 else "none"
    
    # VWAP
    vwap_value = price * (1 + random.uniform(-0.002, 0.002))
    vwap_distance = ((price - vwap_value) / vwap_value) * 100
    
    # Supertrend
    supertrend_value = price * (1 + random.uniform(-0.01, 0.01))
    supertrend_direction = "up" if price > supertrend_value else "down"
    is_breakout = abs(price - supertrend_value) / price > 0.005
    
    # Bollinger Bands
    middle_band = price
    std_dev = price * 0.02
    upper_band = middle_band + (2 * std_dev)
    lower_band = middle_band - (2 * std_dev)
    bandwidth = ((upper_band - lower_band) / middle_band) * 100
    bb_position = ((price - lower_band) / (upper_band - lower_band)) * 100 if upper_band != lower_band else 50
    
    # ATR
    atr_value = price * 0.015
    atr_percent = (atr_value / price) * 100
    
    # ADX
    adx_value = random.uniform(15, 50)
    plus_di = random.uniform(10, 40)
    minus_di = random.uniform(10, 40)
    
    # Overall signal
    signals = [ema_trend, rsi_signal]
    bullish_count = sum(1 for s in signals if s == "bullish")
    bearish_count = sum(1 for s in signals if s == "bearish")
    overall_signal = "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral"
    confidence = random.uniform(55, 85)
    
    return TechnicalIndicators(
        symbol=symbol.upper(),
        timestamp=datetime.utcnow(),
        price=round(price, 2),
        ema=EMAData(
            ema_9=round(price * (1 + random.uniform(-0.002, 0.002)), 2),
            ema_20=round(ema20, 2),
            ema_50=round(ema50, 2),
            ema_100=round(price * (1 + random.uniform(-0.02, 0.02)), 2),
            ema_200=round(ema200, 2),
            trend=TrendDirection(ema_trend),
            crossover="golden_cross" if ema20 > ema50 else "death_cross" if ema20 < ema50 else None,
        ),
        rsi=RSIData(
            value=round(rsi_value, 2),
            signal=rsi_signal,
        ),
        macd=MACDData(
            macd=round(macd_value, 2),
            signal=round(signal_value, 2),
            histogram=round(histogram, 2),
            crossover=macd_crossover,
        ),
        vwap=VWAPData(
            value=round(vwap_value, 2),
            distance_from_vwap=round(vwap_distance, 3),
            signal="above" if price > vwap_value else "below",
        ),
        supertrend=SupertrendData(
            value=round(supertrend_value, 2),
            direction=supertrend_direction,
            is_breakout=is_breakout,
        ),
        bollinger_bands=BollingerBandsData(
            upper=round(upper_band, 2),
            middle=round(middle_band, 2),
            lower=round(lower_band, 2),
            bandwidth=round(bandwidth, 2),
            position=round(bb_position, 2),
        ),
        atr=ATRData(
            value=round(atr_value, 2),
            percent=round(atr_percent, 2),
            signal="high" if atr_percent > 2 else "medium" if atr_percent > 1 else "low",
        ),
        adx=ADXData(
            value=round(adx_value, 2),
            trend_strength="strong" if adx_value > 25 else "moderate" if adx_value > 15 else "weak",
            plus_di=round(plus_di, 2),
            minus_di=round(minus_di, 2),
        ),
        overall_signal=overall_signal,
        confidence=round(confidence, 1),
    )


@router.get("/{symbol}/ema")
async def get_ema(
    symbol: str,
    periods: str = Query("20,50,200", description="Comma-separated periods"),
):
    """Get EMA values for specific periods"""
    logger.info("calculating_ema", symbol=symbol, periods=periods)
    
    period_list = [int(p.strip()) for p in periods.split(",")]
    spot_price = 24567.85 if symbol.upper() == "NIFTY" else 52456.70
    
    return {
        "symbol": symbol.upper(),
        "timestamp": datetime.utcnow(),
        "price": spot_price,
        "ema": {
            f"ema_{p}": round(spot_price * (1 + random.uniform(-0.03 * p / 50, 0.03 * p / 50)), 2)
            for p in period_list
        },
    }


@router.get("/{symbol}/rsi")
async def get_rsi(symbol: str, period: int = Query(14, ge=1, le=100)):
    """Get RSI value"""
    logger.info("calculating_rsi", symbol=symbol, period=period)
    
    spot_price = 24567.85 if symbol.upper() == "NIFTY" else 52456.70
    rsi_value = random.uniform(25, 75)
    
    return {
        "symbol": symbol.upper(),
        "timestamp": datetime.utcnow(),
        "price": spot_price,
        "rsi": round(rsi_value, 2),
        "signal": "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral",
        "period": period,
    }


@router.get("/{symbol}/macd")
async def get_macd(
    symbol: str,
    fast: int = Query(12, ge=1),
    slow: int = Query(26, ge=1),
    signal: int = Query(9, ge=1),
):
    """Get MACD values"""
    logger.info("calculating_macd", symbol=symbol, fast=fast, slow=slow, signal=signal)
    
    spot_price = 24567.85 if symbol.upper() == "NIFTY" else 52456.70
    
    macd_value = random.uniform(-100, 100)
    signal_value = random.uniform(-50, 50)
    
    return {
        "symbol": symbol.upper(),
        "timestamp": datetime.utcnow(),
        "price": spot_price,
        "macd": round(macd_value, 2),
        "signal": round(signal_value, 2),
        "histogram": round(macd_value - signal_value, 2),
        "crossover": "bullish" if macd_value > signal_value else "bearish",
        "parameters": {"fast": fast, "slow": slow, "signal": signal},
    }


@router.get("/{symbol}/history/{indicator}", response_model=IndicatorHistoryResponse)
async def get_indicator_history(
    symbol: str,
    indicator: str,
    period: str = Query("1d", description="Time period (1d, 1w, 1m, 3m)"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get historical indicator values"""
    logger.info("fetching_indicator_history", symbol=symbol, indicator=indicator, period=period)
    
    now = datetime.utcnow()
    interval_hours = {
        "1d": 24,
        "1w": 168,
        "1m": 720,
        "3m": 2160,
    }.get(period, 24)
    
    data = []
    base_value = 50 if indicator == "rsi" else 0 if indicator == "macd" else 24567.85
    
    for i in range(limit, 0, -1):
        timestamp = now - timedelta(hours=i * interval_hours / limit)
        
        if indicator == "rsi":
            value = random.uniform(20, 80)
        elif indicator == "macd":
            value = random.uniform(-50, 50)
        else:
            value = base_value * (1 + random.uniform(-0.05, 0.05))
        
        data.append(IndicatorHistory(timestamp=timestamp, value=round(value, 2)))
    
    return IndicatorHistoryResponse(
        indicator=indicator,
        symbol=symbol.upper(),
        period=period,
        data=data,
    )
