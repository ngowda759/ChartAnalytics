from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
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
from app.services.market_service import get_market_service
from app.services.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_adx,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_vwap,
    calculate_supertrend,
    interpret_rsi,
    get_trend_direction,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{symbol}", response_model=TechnicalIndicators)
async def get_indicators(symbol: str):
    """Get all technical indicators for a symbol"""
    logger.info("calculating_indicators", symbol=symbol)

    service = get_market_service()
    ohlc = await service.get_ohlc(symbol, "1d", 200)

    if not ohlc or len(ohlc) < 200:
        raise HTTPException(status_code=404, detail="Insufficient data for analysis")

    closes = [c.close for c in ohlc]
    highs = [c.high for c in ohlc]
    lows = [c.low for c in ohlc]
    volumes = [c.volume for c in ohlc]

    current_price = closes[-1]

    # EMA
    ema9_list = calculate_ema(closes, 9)
    ema20_list = calculate_ema(closes, 20)
    ema50_list = calculate_ema(closes, 50)
    ema100_list = calculate_ema(closes, 100)
    ema200_list = calculate_ema(closes, 200)

    ema9 = ema9_list[-1] if ema9_list and ema9_list[-1] else current_price
    ema20 = ema20_list[-1] if ema20_list and ema20_list[-1] else current_price
    ema50 = ema50_list[-1] if ema50_list and ema50_list[-1] else current_price
    ema100 = ema100_list[-1] if ema100_list and ema100_list[-1] else current_price
    ema200 = ema200_list[-1] if ema200_list and ema200_list[-1] else current_price

    ema_trend_raw = get_trend_direction(ema20, ema50, ema200, current_price)
    # get_trend_direction returns fine-grained strings (strong_uptrend, uptrend,
    # strong_downtrend, downtrend, ranging, unknown); map to the enum's
    # bullish/bearish/neutral so EMAData.trend validates.
    _TREND_MAP = {
        "strong_uptrend": TrendDirection.BULLISH,
        "uptrend": TrendDirection.BULLISH,
        "strong_downtrend": TrendDirection.BEARISH,
        "downtrend": TrendDirection.BEARISH,
        "ranging": TrendDirection.NEUTRAL,
        "unknown": TrendDirection.NEUTRAL,
    }
    ema_trend = _TREND_MAP.get(ema_trend_raw, TrendDirection.NEUTRAL)

    # RSI
    rsi_list = calculate_rsi(closes, 14)
    rsi_value = rsi_list[-1] if rsi_list and rsi_list[-1] else 50
    rsi_signal = interpret_rsi(rsi_value)

    # MACD
    macd_line, signal_line, histogram = calculate_macd(closes)
    macd_value = macd_line[-1] if macd_line and macd_line[-1] else 0
    signal_value = signal_line[-1] if signal_line and signal_line[-1] else 0
    histogram_value = histogram[-1] if histogram and histogram[-1] else 0

    # Bollinger Bands
    bb_data = calculate_bollinger_bands(closes, 20, 2.0)
    bb = bb_data[-1] if bb_data and bb_data[-1] else None

    # VWAP
    vwap_values = calculate_vwap(highs, lows, closes, volumes)
    vwap = vwap_values[-1] if vwap_values and vwap_values[-1] else current_price

    # Supertrend
    st_data = calculate_supertrend(highs, lows, closes, 10, 3.0)
    st = st_data[-1] if st_data and st_data[-1] else None

    # ADX
    adx_data = calculate_adx(highs, lows, closes, 14)
    adx = adx_data[-1] if adx_data and adx_data[-1] else None

    # ATR
    atr_list = calculate_atr(highs, lows, closes, 14)
    atr_value = atr_list[-1] if atr_list and atr_list[-1] else 0

    # MACD crossover derived from last two histogram values.
    macd_crossover = "none"
    if len(histogram) >= 2 and histogram[-1] is not None and histogram[-2] is not None:
        if histogram[-1] > 0 and histogram[-2] <= 0:
            macd_crossover = "bullish"
        elif histogram[-1] < 0 and histogram[-2] >= 0:
            macd_crossover = "bearish"

    bb_obj = bb  # BollingerBands or None

    supertrend_obj = st
    st_direction = "up" if supertrend_obj and supertrend_obj.trend == "up" else "down"
    st_breakout = bool(
        supertrend_obj
        and (
            (st_direction == "up" and current_price > supertrend_obj.value)
            or (st_direction == "down" and current_price < supertrend_obj.value)
        )
    )

    adx_obj = adx
    adx_value = adx_obj.adx if adx_obj else 0.0
    adx_plus = adx_obj.plus_di if adx_obj else 0.0
    adx_minus = adx_obj.minus_di if adx_obj else 0.0
    adx_strength = adx_obj.trend_strength if adx_obj else "weak"

    atr_pct = round(atr_value / current_price * 100, 2) if current_price > 0 else 0.0
    atr_signal = "high" if atr_pct > 3 else ("medium" if atr_pct > 1.5 else "low")

    vwap_signal = "above" if current_price > vwap else "below"
    vwap_distance = (
        round((current_price - vwap) / vwap * 100, 2) if vwap > 0 else 0.0
    )

    # Overall signal from EMA trend + RSI + MACD histogram.
    signals = []
    if ema_trend == TrendDirection.BULLISH:
        signals.append(1)
    elif ema_trend == TrendDirection.BEARISH:
        signals.append(-1)
    if rsi_value > 70:
        signals.append(-1)
    elif rsi_value < 30:
        signals.append(1)
    if histogram_value > 0:
        signals.append(1)
    elif histogram_value < 0:
        signals.append(-1)
    overall = (
        "bullish" if sum(signals) > 0
        else "bearish" if sum(signals) < 0 else "neutral"
    )
    confidence = round(min(abs(sum(signals)) / max(len(signals), 1) * 100, 100), 2)

    return TechnicalIndicators(
        symbol=symbol,
        timestamp=datetime.utcnow(),
        price=round(current_price, 2),
        ema=EMAData(
            ema_9=round(ema9, 2),
            ema_20=round(ema20, 2),
            ema_50=round(ema50, 2),
            ema_100=round(ema100, 2),
            ema_200=round(ema200, 2),
            trend=ema_trend,
        ),
        rsi=RSIData(
            value=round(rsi_value, 2),
            signal=rsi_signal.signal,
        ),
        macd=MACDData(
            macd=round(macd_value, 4),
            signal=round(signal_value, 4),
            histogram=round(histogram_value, 4),
            crossover=macd_crossover,
        ),
        vwap=VWAPData(
            value=round(vwap, 2),
            distance_from_vwap=vwap_distance,
            signal=vwap_signal,
        ),
        supertrend=SupertrendData(
            value=round(supertrend_obj.value, 2) if supertrend_obj else round(current_price, 2),
            direction=st_direction,
            is_breakout=st_breakout,
        ),
        bollinger_bands=BollingerBandsData(
            upper=round(bb_obj.upper, 2) if bb_obj else round(current_price * 1.02, 2),
            middle=round(bb_obj.middle, 2) if bb_obj else round(current_price, 2),
            lower=round(bb_obj.lower, 2) if bb_obj else round(current_price * 0.98, 2),
            bandwidth=round(bb_obj.bandwidth, 2) if bb_obj else 4.0,
            position=round(bb_obj.percent_b * 100, 2) if bb_obj else 50.0,
        ),
        atr=ATRData(
            value=round(atr_value, 2),
            percent=atr_pct,
            signal=atr_signal,
        ),
        adx=ADXData(
            value=round(adx_value, 2),
            trend_strength=adx_strength,
            plus_di=round(adx_plus, 2),
            minus_di=round(adx_minus, 2),
        ),
        overall_signal=overall,
        confidence=confidence,
    )


@router.get("/history/{symbol}")
async def get_indicator_history(
    symbol: str,
    indicator: str = Query(
        ..., description="Indicator name (ema, rsi, macd, adx, bollinger, atr, vwap)"
    ),
    period: int = Query(20, ge=5, le=200),
):
    """Get historical values of a specific indicator"""
    logger.info("fetching_indicator_history", symbol=symbol, indicator=indicator)

    service = get_market_service()
    ohlc = await service.get_ohlc(symbol, "1d", 300)

    if not ohlc or len(ohlc) < period:
        raise HTTPException(status_code=404, detail="Insufficient data")

    closes = [c.close for c in ohlc]
    highs = [c.high for c in ohlc]
    lows = [c.low for c in ohlc]
    volumes = [c.volume for c in ohlc]

    values = []
    timestamps = [c.timestamp for c in ohlc]

    if indicator == "ema":
        ema_values = calculate_ema(closes, period)
        values = [{"value": round(v, 2) if v else None} for v in ema_values]
    elif indicator == "rsi":
        rsi_values = calculate_rsi(closes, period)
        values = [{"value": round(v, 2) if v else None} for v in rsi_values]
    elif indicator == "macd":
        macd_line, signal_line, histogram = calculate_macd(closes)
        for i in range(len(macd_line)):
            values.append(
                {
                    "macd": round(macd_line[i], 4) if macd_line[i] else None,
                    "signal": round(signal_line[i], 4) if signal_line[i] else None,
                    "histogram": round(histogram[i], 4) if histogram[i] else None,
                }
            )
    elif indicator == "bollinger":
        bb_data = calculate_bollinger_bands(closes, period, 2.0)
        values = [
            {
                "upper": round(bb.upper, 2) if bb else None,
                "middle": round(bb.middle, 2) if bb else None,
                "lower": round(bb.lower, 2) if bb else None,
            }
            for bb in bb_data
        ]
    elif indicator == "atr":
        atr_values = calculate_atr(highs, lows, closes, period)
        values = [{"value": round(v, 2) if v else None} for v in atr_values]
    elif indicator == "vwap":
        vwap_values = calculate_vwap(highs, lows, closes, volumes)
        values = [{"value": round(v, 2) if v else None} for v in vwap_values]
    elif indicator == "adx":
        adx_data = calculate_adx(highs, lows, closes, period)
        values = [
            {
                "adx": round(adx.adx, 2) if adx else None,
                "plus_di": round(adx.plus_di, 2) if adx else None,
                "minus_di": round(adx.minus_di, 2) if adx else None,
            }
            for adx in adx_data
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown indicator: {indicator}")

    return IndicatorHistoryResponse(
        symbol=symbol,
        indicator=indicator,
        period=period,
        values=values[: len(timestamps)],
        timestamps=timestamps,
    )


@router.get("/analysis/{symbol}")
async def get_ai_analysis(symbol: str):
    """Get AI-powered complete technical analysis"""
    logger.info("generating_ai_analysis", symbol=symbol)

    service = get_market_service()
    insight = await service.get_market_insight(symbol)

    if not insight:
        raise HTTPException(status_code=404, detail="Unable to generate analysis")

    return {
        "symbol": insight.symbol,
        "timestamp": insight.timestamp.isoformat(),
        "trend": insight.trend,
        "momentum": insight.momentum,
        "sentiment": insight.sentiment,
        "confidence": insight.confidence,
        "breakout_probability": insight.breakout_probability,
        "summary": insight.summary,
        "recommendation": insight.recommendation,
        "signals": [
            {
                "indicator": s.indicator,
                "value": s.value,
                "signal": s.signal,
                "strength": s.strength,
                "message": s.message,
            }
            for s in insight.signals
        ],
        "support_levels": [
            {"price": s.price, "strength": s.strength} for s in insight.support_levels
        ],
        "resistance_levels": [
            {"price": s.price, "strength": s.strength}
            for s in insight.resistance_levels
        ],
        "risk_factors": insight.risk_factors,
        "key_observations": insight.key_observations,
    }
